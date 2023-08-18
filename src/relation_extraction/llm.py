from .llm_prompt import build_prompt, filter_examples, reformat_examples

import langchain
import torch

import pandas as pd

from argparse import ArgumentParser
from importlib import import_module
import warnings

import sys


def build_llm(
        provider : str,
        model_locator : str = None,
        *,
        service_key : str = None,
        sampling_temperature : float = 0.0,
        decoding_max_length : int = 3072,
        use_gpu : bool = True,
    ):
    if provider == "HuggingFacePipeline":
        if model_locator is None:
            raise ValueError(f""""model_locator" argument is None. A model locator must be provided for this provider ({provider}).""")

        device = 0 if (use_gpu and (torch.cuda.device_count() > 0)) else -1
        model = langchain.HuggingFacePipeline.from_model_id(
            model_id=model_locator,
            task="text-generation",
            model_kwargs={
                "temperature": sampling_temperature, "max_length": decoding_max_length,
            },
            device=device
        )

    elif provider == "GPT4All":
        if model_locator is None:
            raise ValueError(f""""model_locator" argument is None. A model locator must be provided for this provider ({provider}).""")

        model = langchain.llms.GPT4All(model=model_locator)

    else:
        if service_key is None:
            raise ValueError(f""""service_key" argument is None. A service key must be provided for this provider ({provider}).""")

        # Get provider
        provider = getattr(langchain,provider)
        
        model_param = {
            f"{provider.lower()}_api_key" : service_key,
            "temperature" : sampling_temperature}
        model = provider(**model_param)

    return model

def _build_parser():
    parser = ArgumentParser()
    
    # Input files
    input_group = parser.add_argument_group("Input options")
    input_group.add_argument("--relations", required=True, help="Filepath of the \".csv\" file containing the relations to predict and their descriptions.")
    input_group.add_argument("--target", required=True, help="Filepath of the \".csv\" file containing the target examples")
    input_group.add_argument("--examples", help="Filepath of the \".csv\" file containing examples to use for few-shot.")
    input_group.add_argument("--keyfile", help="Filepath of the \".csv\" file containing provider API keys.")

    behaviour_group = parser.add_argument_group("Behaviour options")
    behaviour_group.add_argument("--num_examples", type=int, default=3, help="Maximum number of examples to use.")
    behaviour_group.add_argument("--example_selection", choices=["sequential","random"], default="sequential", help="How to choose the examples to use.")

    system_group = parser.add_argument_group("System options")
    system_group.add_argument("--provider", default="HuggingFacePipeline", help="Name of the LLM provider to use.")
    system_group.add_argument("--model_id", default="bigscience/bloom-3b", help="LLM to use (When using HuggingFacePipeline)")
    system_group.add_argument("--model_path", default="./models/nous-hermes-13b.bin", help="Path of the LLM to use (When using GPT4All)")

    system_group.add_argument("--temperature", type=float, default=0.0, help="Temperature at which to sample LLM.")
    system_group.add_argument("--max_length", type=int, default=3072, help="Maximum token length of the LLM.")
    system_group.add_argument("--no-gpu", dest="gpu", action="store_false", help="Do not use GPU. Only has effect when running locally.")

    system_group.set_defaults(gpu=True)

    return parser

if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    # Build Prompt Engine
    rel_df = pd.read_csv(args.relations)
    ex_df = None
    if args.examples:
        ex_df = pd.read_csv(args.examples)

    prompt = build_prompt(
        rel_df=rel_df,
        ex_df=ex_df,
        random_example_selection=(args.example_selection == "random"),
        num_examples=args.num_examples)

    # Build Model
    model_locator = (
        args.model_id if (args.provider == "HuggingFacePipeline") else
        args.model_path if args.provider == "GPT4All" else None
    )

    if args.provider not in {"GPT4All","HuggingFacePipeline"}:
        # Get Provider Key
        keyfile_df = pd.read_csv(args.keyfile)
        
        provider_mask = keyfile_df.provider == args.provider
        key = provider_mask.idmax()
        if provider_mask[key]:
            key = keyfile_df.iloc[key]
        else:
            raise RuntimeError(f"Provider \"{args.provider}\" key not found in keyfile \"{args.keyfile}\"")
    else:
        key = None

    model = build_llm(
        provider=args.provider,
        model_locator=model_locator,
        service_key=key,
        sampling_temperature=args.temperature,
        decoding_max_length=args.max_length,
        use_gpu=args.gpu
    )

    # Get Target examples
    tgt_df = pd.read_csv(args.target)
    tgt_df = filter_examples(tgt_df,rel_df)
    tgt = reformat_examples(tgt_df)


    ## Test
    for e in tgt:
        p = prompt.format(text=e["text"])
        print(p,end="")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out_ = model.predict(p)
        print(out_)

