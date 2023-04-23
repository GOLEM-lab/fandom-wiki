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


def relations_from_annotation(annot : list) -> typing.List[tuple]:
    labels = filter(lambda x: x["type"] == "labels",annot)
    labels = {label["id"] : label["value"] for label in labels}
    
    relations = filter(lambda x: x["type"] == "relation",annot)
    triples = [( 
            (r["from_id"],r["labels"][0].split(" ")[0],r["to_id"]) 
            if r["direction"] == "right" else
            (r["to_id"],r["labels"][0].split(" ")[0],r["from_id"])
        ) for r in relations if r["labels"]]

    # Change ids for text
    left, rel, right = zip(*triples) 
    
    left = map(labels.__getitem__,left)
    left = ((l["text"],l["labels"][0].split(" ")[0]) for l in left)
    left = zip(*left)    
    
    right = map(labels.__getitem__,right)
    right = ((r["text"],r["labels"][0].split(" ")[0]) for r in right)
    right = zip(*right)

    triples = zip(*left, rel,*right)
    triples = list(triples)

    return triples


def relations_from_annotations(annot : list, context : list) -> pd.DataFrame:
    relations_per_annotation = map(relations_from_annotation,annot)
    relation_and_context = [(*r,c) 
                                for relations, c in zip(relations_per_annotation,context) 
                                for r in relations]

    rel_df = pd.DataFrame(relation_and_context,
                columns=["left_entity","left_class","relation","right_entity","right_class","context"])
    return rel_df

def relation_spec_from_annotation(annot : list) -> pd.DataFrame:
    labels = filter(lambda x: x["type"] == "labels",annot)
    labels = {label["id"] : label["value"]["labels"] for label in labels}
    
    relations = filter(lambda x: x["type"] == "relation",annot)
    triples = [( 
            (r["from_id"],*r["labels"][0].split(" ",maxsplit=1),r["to_id"]) 
            if r["direction"] == "right" else
            (r["to_id"],*r["labels"][0].split(" ",maxsplit=1),r["from_id"])
        ) for r in relations if r["labels"]]

    new_triples = []
    for left, *rel, right in triples:
        left, right = labels[left], labels[right]

        product = ((*rel,l.split(" ")[0],r.split(" ")[0]) for l,r in itools.product(left,right))
        new_triples.extend(product)

    return new_triples


def relation_spec_from_annotations(annot : list) -> pd.DataFrame:
    triples = map(relation_spec_from_annotation,annot)
    triples = itools.chain(*triples)
    triples = set(triples)

    rel_df = pd.DataFrame(triples,
                columns=["prop","propLabel","left_class","right_class"])
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
        relations = relation_spec_from_annotations(extracted_annotations)
    
    relations.to_csv(sys.stdout,index=False)




