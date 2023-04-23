from . import qa
from ..utils.relation_utils import read_relations, generate_verbalizations

import pandas as pd
import numpy as np
import transformers

from argparse import ArgumentParser
from typing import Callable
import itertools as itools
from tqdm import tqdm

import json

import sys
import warnings


def _build_parser():
    """TODO Docstring"""
    parser = ArgumentParser()

    rel_group = parser.add_argument_group("Relation options")
    rel_group.add_argument("--relations",required=True,help="Filepath of file with a list of relations: a relation spec \"*<class_left>:<relation_name>:<class_right>\" followed by one or more verbalizations.")
    rel_group.add_argument("--OoS_relations",dest="oos_relations",action="store_true",help="Predict relations for instances whose target relations are not in the relation list. Out-of-Scope.")
    rel_group.add_argument("--infer_entity_class", action="store_true", help="Use entity type annotations to decide the class of each entity.")
    rel_group.add_argument("--entity_class", default="Thing", help="The class associated to the entities. Ignored when using \"infer_entity_class\"")
    rel_group.add_argument("--symmetric_relations",action="store_true",help="Predict relations taking as relation head both entities in each target relation.")

    rel_group.set_defaults(oos_relations=False)
    rel_group.set_defaults(infer_entity_class=False)
    rel_group.set_defaults(symmetric_relations=False)


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

class QA_For_Eval(object):
    def __init__(self,
                relation_df : pd.DataFrame,
                qa_module : Callable,
                entity_class : str = None,
                config : dict = dict()):
        
        self.relation_df = relation_df
        self.entity_class = entity_class
        self.qa_module = qa_module
        self.config = config

    def answers_for_context(self, context_df : pd.DataFrame):
        context, *_ = context_df.context.unique()
        
        if self.entity_class is not None:
            entities = context_df.left_entity.unique()
            # Check symmetric relations
            if self.config.symmetric_relations:
                entities_right = context_df.right_entity.unique()
                entities = frozenset(entities) | frozenset(entities_right)
                entities = list(entities)
           
            entity_classes = self.entity_class

        else:
            entities = context_df.left_entity, context_df.left_class
            entities = zip(*entities)

            if self.config.symmetric_relations:
                right_entities = context_df.right_entity, context_df.right_class
                right_entities = zip(*right_entities)

                entities = itools.chain(entities,right_entities)

            entities = set(entities)
            entities, entity_classes = zip(*entities)

            
        entity_df = pd.DataFrame(dict(instance_of=entity_classes,entity_label=entities))
        verb = generate_verbalizations(entity_df,self.relation_df)

        answer_df = qa.generate_answers(context,verb,self.qa_module,config=self.config)

        return answer_df

if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    # Prepare logging
    transformers.logging.set_verbosity_error()
    warnings.filterwarnings("ignore")
    tqdm.pandas()

    eval_df = pd.read_csv(sys.stdin,header=0)
    with open(args.relations,"r") as relations_f:
        rel_df = read_relations(relations_f)

    # Init QA system
    qa_module = qa.init_pipeline_system(args)
    entity_class = None if args.infer_entity_class else args.entity_class
    qa4eval = QA_For_Eval(rel_df,qa_module,entity_class,args)


    if not args.oos_relations:
        eval_df_mask = eval_df.relation.apply(set(rel_df["rel_name"].values).__contains__)
        eval_df = eval_df[eval_df_mask]

    ans = eval_df.groupby("context",group_keys=True).progress_apply(qa4eval.answers_for_context)

    ans_dict = qa.answers_to_dict(ans)
    json.dump(ans_dict,sys.stdout)

