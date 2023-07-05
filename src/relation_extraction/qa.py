from ..utils.relation_utils import read_relations,generate_verbalizations

import transformers
import pandas as pd
import numpy as np

from difflib import SequenceMatcher

from argparse import ArgumentParser
import tqdm

import typing
import operator as op
import functools as ftools
import itertools as itools

import json

import io
import sys


def generate_answers(context, verbalizations : pd.DataFrame ,qa,config):
    
    # Unroll questions
    all_verb = list(itools.chain(*verbalizations.verbalizations))
    verb_lengths = verbalizations.verbalizations.apply(len)
    verb_end = np.cumsum(verb_lengths)
    verb_start = np.concatenate(([0],verb_end))

    verb_ranges = (range(s,e) for s,e in zip(verb_start,verb_end))

    # Run QA system # TODO manual batching to avoid OOM errors
    ans = qa(question=all_verb,context=context)

    # Align with questions
    ans_dicts = [[dict(question=all_verb[i],answers=ans[i]) for i in rg] for rg in verb_ranges]

    # Create dataframe aligned
    res = verbalizations[["entity_label","rel_name","cl_right"]]
    res["answers"] = ans_dicts

    return res

def _aggregate_group(df : pd.DataFrame, group_name : str):
    
    print(df)
    
    agg_df = df.groupby(group_name).agg(agg_function)

    print(agg_df)

    return agg_df

def answers_to_dict(answers: pd.DataFrame):
 
    list_merger = lambda x: list(itools.chain(*x))
    dict_merger = lambda x: ftools.reduce(op.or_, x, {})

    grouped_answers = answers.drop("context",axis=1)
    grouped_answers = grouped_answers.groupby(["rel_name","cl_right","entity_label"]).agg(list_merger)
    grouped_answers.reset_index(inplace=True)
    grouped_answers["answers"] = grouped_answers.apply(lambda x: {x.entity_label : x.answers},axis=1)
    
    grouped_answers.drop("entity_label",axis=1,inplace=True)
    grouped_answers = grouped_answers.groupby(["rel_name","cl_right"]).agg(dict_merger)
    grouped_answers.reset_index(inplace=True)
    grouped_answers["answers"] = grouped_answers.apply(lambda x: {x.cl_right : x.answers},axis=1)

    grouped_answers.drop("cl_right",axis=1,inplace=True)
    grouped_answers = grouped_answers.groupby("rel_name").agg(dict_merger)
    grouped_answers.reset_index(inplace=True)
    ans_dicts = grouped_answers.apply(lambda x: {x.rel_name : x.answers},axis=1)

    ans_dicts = ans_dicts.aggregate(dict_merger)

    return ans_dicts


def init_pipeline_system(config):
    
    # Instantiate pipeline
    model_config = transformers.AutoConfig.from_pretrained(config.language_model)
    pipeline = transformers.pipeline(model=config.language_model,device=0,
                                    config=model_config,)

    # Set pipeline working mode
    pipeline.model.eval()
    if config.fp16: pipeline.model.half()

    # Set call options
    pipeline = ftools.partial(pipeline,
                        batch_size=config.batch_size,max_seq_len=config.max_seq_len,
                        doc_stride=config.doc_stride,top_k=config.relations_per_question,
                        handle_impossible_answer=config.use_norel)

    return pipeline

    
def _build_parser():
    parser = ArgumentParser()
    
    # Input files
    input_group = parser.add_argument_group("Input options")
    input_group.add_argument("--entities", required=True, help="Filepath of file with a list of entities: \"<entity_name>:<class>\".")
    input_group.add_argument("--relations", required=True, help="Filepath of file with a list of relations: a relation spec \"*<class_left>:<relation_name>:<class_right>\" followed by one or more verbalizations.")

    # Extraction sensitivity params
    extraction_group = parser.add_argument_group("Extraction options")
    extraction_group.add_argument("--relations_per_question", type=int, default=8, help="How many relations to extract per each relation verbalization question.")
    extraction_group.add_argument("--use_norel", action="store_true", help="Enable the possibility of predicting \"no-relation\"."+
                                                                "A no-relation prediction invalidates all predictions with strictly lower confidence."+
                                                                "This mechanism is complementary to the \"CONFIDENCE_THRESHOLD\" parameter.")
    extraction_group.set_defaults(use_norel=False)

    # System settings
    system_group = parser.add_argument_group("System options")
    system_group.add_argument("-lm", "--language_model", dest="language_model", default="deepset/roberta-large-squad2", help="QA Language model to use (HuggingFace).")
    system_group.add_argument("-bs", "--batch_size", dest="batch_size", type=int, default=1, help="Batch-size to use (inference).")
    system_group.add_argument("-fp16", dest="fp16", action="store_true", help="Use Half-precision for faster inference and lower memory usage. Only works for modern GPUs (CUDA capability > 7.0).")
    system_group.add_argument("--max_seq_len", type=int, default=384, help="Maximum sequence length per processed context chunk. Higher values are computationally more expensive. May help with long distance dependencies in relations.")
    system_group.add_argument("--doc_stride", type=int, default=128, help="Maximum overlap length between neighbouring chunks. Higher values are computationally more expensive. May help with long distance dependencies in relations.")
    system_group.set_defaults(fp16=False)

    return parser

if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    ## INIT 
    entities = pd.read_csv(args.entities,header=0)
    with open(args.relations,"r") as relations_f:
        relations = read_relations(relations_f)
    
    # Read input context
    context = sys.stdin.read()

    # Initialize qa system
    qa = init_pipeline_system(args)
    
    ## RUN
    # Generate answers
    verbalizations = generate_verbalizations(entities,relations)
    answers = generate_answers(context,verbalizations,qa,config=args)
    answer_dict = answers_to_dict(answers)

    # output 
    json.dump(answer_dict,sys.stdout)
    

    

    
