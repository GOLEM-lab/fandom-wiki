from ..relation_extraction.llm_prompt import filter_examples, reformat_examples

import pandas as pd

from argparse import ArgumentParser

def _build_parser():
    parser = ArgumentParser()
    
    # Input files
    input_group = parser.add_argument_group("Input options")
    input_group.add_argument("--relations", required=True, help="Filepath of the \".csv\" file containing the relations to predict and their descriptions.")
    input_group.add_argument("--examples", required=True, help="Filepath of the \".csv\" file containing examples to use for few-shot.")

    return parser

if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    rel_df = pd.read_csv(args.relations)
    ex_df = pd.read_csv(args.examples)

    ex_df = filter_examples(ex_df,rel_df)
    examples = reformat_examples(ex_df)

    rels = rel_df.propLabel.unique()
    ex_rels = [set(relation["relation"] for relation in ex["relations"]) for ex in examples]


    # Print matrix
    row_template = " ".join(["{:14}"]*(len(rels)+2))
    print(row_template.format("",*rels,"total"))
    for i,ex in enumerate(ex_rels):
        relation_row = list(map(ex.__contains__,rels))
        print(row_template.format(i,*relation_row,sum(relation_row)))

    
        
    
        
