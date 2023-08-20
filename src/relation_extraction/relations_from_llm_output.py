import pandas as pd

import operator as op
import re

from argparse import ArgumentParser
import itertools as itools

import json

import sys


_shallow_dict_regex = re.compile("{.*?}",re.DOTALL)
_double_quotes_regex = re.compile("(?:(?<=\": )'|(?<=\":)'|'(?=}|,))",re.DOTALL)
_internal_double_quotes_regex = re.compile("(?!(?<=\\\\)\"|(?<=\": )\"|(?<=\":)\"|\"(?=}|,)|\"(?=:)|\"(?=relation)|\"(?=subject)|\"(?=object))\"",re.DOTALL)
_newline_regex = re.compile("('|\")\n\s*('|\")")
def predictions_text_to_dict(llm_output : dict):

    llm_predictions = map(op.itemgetter("model_prediction"),llm_output)
    dict_candidates = map(_shallow_dict_regex.findall,llm_predictions)
    dict_candidates = itools.chain(*dict_candidates)
    dict_candidates = set(dict_candidates)
    
    res = []
    for d in dict_candidates:
        try:
            d = d.replace("'object'",'"object"').replace("'subject'",'"subject"').replace("'relation'",'"relation"')
            d = d.replace('\\"object"\\','"object"').replace('\\"subject"\\','"subject"').replace('\\"relation"\\','"relation"')
            d = _double_quotes_regex.sub('"',d)
            d = _newline_regex.sub(" ",d)
            d = _internal_double_quotes_regex.sub("\\\"",d)

            r = json.loads(d)    
            res.append(r)
        except json.JSONDecodeError as e:
            sys.stderr.write("{}\n{}\n".format(d,e))

    return res



def _build_parser():
    parser = ArgumentParser()
    
    # Input files
    input_group = parser.add_argument_group("Input options")
    input_group.add_argument("--llm_output", required=True, help="Filepath of the \".json\" file with the LLM output.")
    input_group.add_argument("--relations", help="Filepath of the \".csv\" file with the relation spec.")


    return parser


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    with open(args.llm_output,"r") as llm_output:
        llm_output = json.load(llm_output)
        
    rels = None
    if args.relations:
        with open(args.relations,"r") as relations_file:
            rel_df = pd.read_csv(relations_file)
        rels = dict(zip(rel_df["propLabel"],rel_df["prop"]))
    
    predictions = predictions_text_to_dict(llm_output)
    pred_df = pd.DataFrame(predictions)

    pred_df.columns = ["right_entity","relation","left_entity"]
    pred_df = pred_df[pred_df.columns[::-1]]

    if rels is not None:
        pred_df["relation"] = pred_df["relation"].apply(rels.get)
        pred_df = pred_df[pred_df["relation"].notnull()]

    pred_df.to_csv(sys.stdout,index=False)

