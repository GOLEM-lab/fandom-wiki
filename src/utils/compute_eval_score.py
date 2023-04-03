from .relation_utils import read_relations

import pandas as pd

from argparse import ArgumentParser

import sys

def _build_parser():
    """TODO Docstring"""
    parser = ArgumentParser()

    parser.add_argument("--predictions",required=True,help="Path of the \".csv\" file containing the system relation predictions.")
    parser.add_argument("--gold",required=True,help="Path of the \".csv\" file containing the gold relations.")

    parser.add_argument("--relations",help="Evaluate only on the target relations that appear in the provided relations file.")

    return parser


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    pred_df = pd.read_csv(args.predictions,header=0)
    gold_df = pd.read_csv(args.gold,header=0)

    if args.relations:
        with open(args.relations,"r") as rel_file:
            rel_df = read_relations(rel_file)

        gold_df_mask = gold_df.relation.apply(set(rel_df["rel_name"].values).__contains__)
        gold_df = gold_df[gold_df_mask]

    merged = pd.merge(pred_df,gold_df)

    precision = len(merged) / len(pred_df)
    recall = len(merged) / len(gold_df)
    f1 =    (2*precision*recall / (precision + recall) 
                if (precision + recall) != 0 else 
            (precision + recall))

    # TODO add confusion matrix and micro-level scores

    print(f"Precision: {precision}")
    print(f"Recall: {recall}")
    print()
    print(f"F1: {f1}")












