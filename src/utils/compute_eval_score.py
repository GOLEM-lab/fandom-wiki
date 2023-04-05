from .relation_utils import read_relations

import pandas as pd

from argparse import ArgumentParser

import sys

def f1(pre,rec):
    f1 = pre + rec
    if f1 != 0:
        f1 = 2*pre*rec/f1
    return f1

def compute_scores(pred_df : pd.DataFrame, gold_df : pd.DataFrame):
    merged_df = pd.merge(pred_df,gold_df)
    relations = set(pred_df.relation.values) & set(gold_df.relation.values)
    relations = list(relations)

    # Compute micro
    precision, recall = [], []
    for rel in relations:
        pre = (merged_df.relation == rel).sum() / (pred_df.relation == rel).sum()
        rec = (merged_df.relation == rel).sum() / (gold_df.relation == rel).sum()

        precision.append(pre)
        recall.append(rec)

    data = dict(relations=relations,precision=precision,recall=recall)
    score_df = pd.DataFrame(data)

    # Compute f1
    score_df["f1"] = score_df[["precision","recall"]].apply(lambda x: f1(x.precision,x.recall),axis=1)

    new_rows = []
    # Make micro-average
    micro_avg = score_df[["precision","recall","f1"]].mean()
    micro_avg = dict(zip(score_df.columns,("micro_average",*micro_avg.values)))
    new_rows.append(micro_avg)

    # Add macro
    pre = len(merged_df) / len(pred_df)
    rec = len(merged_df) / len(gold_df)
    macro_avg = dict(zip(score_df.columns,("macro_average",pre,rec,f1(pre,rec))))
    new_rows.append(macro_avg)

    new_df = pd.DataFrame(new_rows)

    # Append rows
    score_df = pd.concat((score_df,new_df),ignore_index=True)
    return score_df

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

    scores_df = compute_scores(pred_df,gold_df)

    scores_df.to_csv(sys.stdout)











