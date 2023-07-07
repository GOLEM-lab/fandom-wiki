import langchain

import pandas as pd

from argparse import ArgumentParser
from importlib import import_module


def _build_parser():
    parser = ArgumentParser()
    
    # Input files
    input_group = parser.add_argument_group("Input options")
    input_group.add_argument("--keyfile", required=True, help="Filepath of the \".csv\" file containing provider API keys.")
    input_group.add_argument("--provider", default="OpenAI", help="Name of the LLM provider to use.")

    system_group = parser.add_argument_group("System options")
    system_group.add_argument("--temperature", type=float, default=0.0, help="Temperature at which to sample LLM.")

    return parser

if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

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
        in_ = input("Prompt: ")
        out_ = model.predict(in_)

