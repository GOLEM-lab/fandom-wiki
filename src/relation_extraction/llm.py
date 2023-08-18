import langchain
import torch

import pandas as pd

from argparse import ArgumentParser
from importlib import import_module

import sys


def _build_parser():
    parser = ArgumentParser()
    
    # Input files
    input_group = parser.add_argument_group("Input options")
    input_group.add_argument("--keyfile", help="Filepath of the \".csv\" file containing provider API keys.")
    input_group.add_argument("--provider", default="OpenAI", help="Name of the LLM provider to use.")

    system_group = parser.add_argument_group("System options")
    system_group.add_argument("--temperature", type=float, default=0.0, help="Temperature at which to sample LLM.")
    system_group.add_argument("--model_id", default="bigscience/bloom-3b", help="LLM to use (When using HuggingFacePipeline)")
    system_group.add_argument("--model_path", default="./models/nous-hermes-13b.bin", help="Path of the LLM to use (When using GPT4All)")
    system_group.add_argument("--max_length", type=int, default=2048, help="Maximum token length of the LLM.")
    system_group.add_argument("--no-gpu", dest="gpu", action="store_false", help="Do not use GPU. Only has effect when running locally.")

    system_group.set_defaults(gpu=True)

    return parser

if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    if args.provider == "HuggingFacePipeline":

        device = 0 if (args.gpu and (torch.cuda.device_count() > 0)) else -1
        model = langchain.HuggingFacePipeline.from_model_id(
            model_id=args.model_id,
            task="text-generation",
            model_kwargs={"temperature": args.temperature, "max_length": args.max_length},
            device=device
        )
    elif args.provider == "GPT4All":
        model = langchain.llms.GPT4All(model=args.model_path)
    else:
        # Get Provider Key
        keyfile_df = pd.read_csv(args.keyfile)
        
        provider_mask = keyfile_df.provider == args.provider
        key = provider_mask.idmax()
        if provider_mask[key]:
            key = keyfile_df.iloc[key]
        else:
            raise RuntimeError(f"Provider \"{args.provider}\" key not found in keyfile \"{args.keyfile}\"")
        
        # Get provider
        provider = getattr(langchain,args.provider)
        
        model_param = {
            f"{args.provider.lower()}_api_key" : key,
            "temperature" : args.temperature}
        model = provider(**model_param)

    ## Test
    while True:
        print("Prompt:")

        in_ = sys.stdin.read()
        out_ = model.predict(in_)
        
        print(out_)
        print()

