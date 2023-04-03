import pandas as pd

from argparse import ArgumentParser

import functools as ftools
import operator as op
import sys

def questions_from_relation_label(relation_label,subject_class,heuristics=False):
    subject = "{"+f"{subject_class}"+"}"

    if heuristics:
        rl_tokens = relation_label.split(" ")
        if rl_tokens[-1] == "of":
            template = f"wh_ques is {subject} a {relation_label}?"
            wh_modes = ["Who","What"]

        elif rl_tokens[-1] == "in":
            pre_label = " ".join(rl_tokens[:-2])
            post_label = " ".join(rl_tokens[-2:])
            template = f"wh_ques {pre_label} is {subject} {post_label}?"
            wh_modes = ["What"]

        elif rl_tokens[-1] in ("by","at") :
            template = f"wh_ques is {subject} {relation_label}?"
            if rl_tokens[-1] == "at":
                wh_modes = ["Where","When"]
            else:
                wh_modes = ["Who"]

        elif rl_tokens[0] == "has":
            label = " ".join(rl_tokens[1:])
            template = f"wh_ques {subject}'s {label}?"
            wh_modes = ["Who","What"]
        else:
            template = f"wh_ques is {subject}'s {relation_label}?"
            wh_modes = ["What","Who"]

        questions = map(ftools.partial(template.replace,"wh_ques"),wh_modes)
        questions = map(op.methodcaller("replace","  "," "),questions)
        return list(questions)

    return [f"{subject} {relation_label}?"]


def _build_parser():
    """TODO Docstring"""
    parser = ArgumentParser()

    parser.add_argument("--subject_class",required=True,help="The class of the entities that can be subject of the relation.")
    parser.add_argument("--object_class",default="Thing",help="The class of the entities that can be object of the relation. By default: \"Thing\".")

    parser.add_argument("--question_heuristics",action="store_true",help="Use heuristics to determine plausible aspects of the question that corresponds to the relation.")
    parser.add_argument("--relation_label_spec",action="store_true",help="Use the label of the relation instead of the ID to define the relation spec.")
    

    parser.set_defaults(question_heuristics=False)
    parser.set_defaults(relation_label_spec=False)

    return parser


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    # Read relations
    rel_df = pd.read_csv(sys.stdin, header=0)

    # Get questions
    questions_from_relation_label = ftools.partial(questions_from_relation_label,
                                        subject_class=args.subject_class,
                                        heuristics=args.question_heuristics)
    questions = rel_df["propLabel"].apply(questions_from_relation_label)

    if args.relation_label_spec:
        lq = pd.concat((rel_df["propLabel"],questions),axis=1)
    else:
        lq = pd.concat((rel_df["prop"],questions),axis=1)

    for _,(r,qs) in lq.iterrows():
        print(f"*{args.subject_class}:{r}:{args.object_class}")
        for q in qs:
            print(q)

        print()


    





