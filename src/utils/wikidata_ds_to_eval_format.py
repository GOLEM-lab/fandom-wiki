import pandas as pd

from argparse import ArgumentParser

import json

import sys

def _build_parser():
    """TODO Docstring"""
    parser = ArgumentParser()

    return parser


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    ds = json.load(sys.stdin)

    left_entities,relation_ids,right_entities, context = [], [], [], []
    for inst in ds:
        tokens = inst["tokens"]
        sentence = " ".join(tokens)

        relations = inst["edgeSet"]
        context += [sentence]*len(relations)
        for relation in relations:
            left_ent = " ".join(map(tokens.__getitem__,relation["left"]))
            right_ent = " ".join(map(tokens.__getitem__,relation["right"]))
            rel_id = relation["kbID"]

            left_entities.append(left_ent)
            right_entities.append(right_ent)
            relation_ids.append(rel_id)

    data = dict(left_entity=left_entities,
                relation=relation_ids,
                right_entity=right_entities,
                context=context)
    data_df = pd.DataFrame(data)

    data_df.to_csv(sys.stdout,index=False)









