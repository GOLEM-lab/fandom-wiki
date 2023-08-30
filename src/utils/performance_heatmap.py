import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

import operator as op

from argparse import ArgumentParser


def _build_parser():
    parser = ArgumentParser()
    
    # Input files
    input_group = parser.add_argument_group("Input options")
    input_group.add_argument("--scores", required=True, help="Filepath of the \".csv\" file containing the performance scores to plot.")
    input_group.add_argument("--relations",  help="Filepath of the \".csv\" file containing relation spec, in order to use relation name as opposed to ID.")

    input_group = parser.add_argument_group("Output options")
    input_group.add_argument("-o","--output", required=True, help="Output filepath.")



    return parser

if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    score_df = pd.read_csv(args.scores)
    rel_df = pd.read_csv(args.relations) if args.relations else None

    # Change relations column
    relation_mask = score_df["relations"].apply(op.methodcaller("startswith","P")) 
    score_df = score_df[relation_mask]

    if rel_df is not None:
        merged_df = pd.merge(score_df,rel_df, left_on="relations",right_on="prop")
        merged_df = merged_df[["propLabel","precision","recall","f1"]]
        score_df = merged_df.rename({"propLabel":"relations"},axis=1)

    score_df.set_index("relations",inplace=True)

    heatmap = sns.heatmap(score_df,vmin=0,vmax=1,cmap="Greens")
    plt.tight_layout()
    heatmap_fig = heatmap.get_figure()
    heatmap_fig.savefig(args.output)

