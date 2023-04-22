import pandas as pd

from argparse import ArgumentParser

import operator as op
import functools as ftools
import itertools as itools
import typing

import json

import sys

def annotations_from_document(annotation_dict : dict) -> typing.List[dict]:

    annotations = annotation_dict["annotations"]

    extracted_result = map(op.itemgetter("result"),annotations)
    extracted_result = itools.chain(*extracted_result)
    annotations = list(extracted_result)

    return annotations
    
def annotations_from_documents(annotation_list : dict) -> typing.List[dict]:
    annotations = map(annotations_from_document,annotation_list)
    annotations = list(annotations)

    return annotations


def context_from_documents(annot : list) -> typing.List[str]:
    context = map(op.itemgetter("data"),annot)
    context = map(op.itemgetter("text"),context)
    context = list(context)
    
    return context

def _triples_from_annotation(annot):
    relations = filter(lambda x: x["type"] == "relation",annot)
    triples = [(r["from_id"],r["labels"][0],r["to_id"]) for r in relations if r["labels"]]

    return triples

def relations_from_annotation(annot : list) -> typing.List[tuple]:
    
    labels = filter(lambda x: x["type"] == "labels",annot)
    labels = {label["id"] : label["value"]["text"] for label in labels}
    
    triples = _triples_from_annotation(annot)

    # Change ids for text
    left, rel, right = zip(*triples) 
    left = map(labels.__getitem__,left)
    rel = (r.split(" ")[0] for r in rel)
    right = map(labels.__getitem__,right)

    triples = zip(left, rel, right)
    triples = list(triples)

    return triples

def relations_from_annotations(annot : list, context : list) -> pd.DataFrame:
    relations_per_annotation = map(relations_from_annotation,annot)
    relation_and_context = [(*r,c) 
                                for relations, c in zip(relations_per_annotation,context) 
                                for r in relations]

    rel_df = pd.DataFrame(relation_and_context,
                columns=["left_entity","relation","right_entity","context"])
    return rel_df

def _build_parser():
    """TODO Docstring"""
    parser = ArgumentParser()

    parser.add_argument("--generate", choices=["eval_csv","relations_csv"], default="eval_csv")
    return parser


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    ds = json.load(sys.stdin)

    extracted_annotations = annotations_from_documents(ds)
    
    if args.generate == "eval_csv":
        extracted_context = context_from_documents(ds)
        relations = relations_from_annotations(extracted_annotations,extracted_context)

    else:
        triples = map(_triples_from_annotation,extracted_annotations)
        triples = itools.chain(*triples)
        
        _, rel, _ = zip(*triples)
        rel = set(rel)
        rel = map(op.methodcaller("split"," ",maxsplit=1),rel)

        relations = pd.DataFrame(rel,columns=["prop","propLabel"])    
    
    relations.to_csv(sys.stdout,index=False)




