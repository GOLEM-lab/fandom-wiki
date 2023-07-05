import pandas as pd
import numpy as np

from difflib import SequenceMatcher

from argparse import ArgumentParser

import itertools as itools
import operator as op
import typing

import json
import ijson

import sys


def _build_parser():
    parser = ArgumentParser()
    
    # Input files
    input_group = parser.add_argument_group("Input options")
    input_group.add_argument("--answers", required=True, help="Filepath of the \".json\" file with the question-answer data.")

    # Output format
    output_group = parser.add_argument_group("Output options")
    output_group.add_argument("--include_confidence", action="store_true", help="Include confidence level for each extracted triple.")
    output_group.set_defaults(include_confidence=False)

    # Extraction sensitivity params
    extraction_group = parser.add_argument_group("Extraction options")
    extraction_group.add_argument("--confidence_threshold", type=float, default=0.95, help="Extract triples when the confidence level is higher than \"CONFIDENCE_THRESHOLD\"")
    extraction_group.add_argument("--relations_per_question", type=int, default=8, help="How many relations to extract per each relation verbalization question.")
    extraction_group.add_argument("--confidence_reduction", choices=("min_confidence","max_confidence","bayesian",), default="max_confidence", help="How to reduce confidence score when merging competing relation predictions, across different relation questions.")
    extraction_group.add_argument("--confidence_reduction_internal", choices=("max_confidence","bayesian",), default="bayesian", help="How to reduce confidence score when merging competing relation predictions, within each relation question.")
    extraction_group.add_argument("--relation_merge_threshold", type=float, default=0.90, help="Minimum proportion of answer overlap required to merge two answers.")

    return parser


def _filter_impossible_ans(answers : list):
    if not isinstance(answers,list): answers = [answers]
    answers.sort(reverse=True,key=op.itemgetter("score"))
    for i, ans in enumerate(answers.copy()):
        if ans["start"] == ans["end"] == 0: # Impossible answer
            ans["score"] = 0
            return answers[:i] + [ans]

    return answers

def _reduce_scores(scores, reduction_method):
    if reduction_method == "max_confidence":
        return max(scores)

    if reduction_method == "min_confidence":
        return min(scores)

    if reduction_method == "bayesian":
        reduced_score = 0
        partition_proba = 1
        for score in scores:
            reduced_score += partition_proba*score
            partition_proba *= 1-score

        return reduced_score

def _np_to_tuple(array: np.ndarray):
    try:
        return tuple(map(_np_to_tuple,array))
    except TypeError:
        return array

# TODO abstract this, also DRY
def _merge_answers(answers, 
                    external_conf_reduction="min_confidence", 
                    internal_conf_reduction="bayesian",
                    merge_threshold=0.9):
    
    # Reduce internally
    new_answers = []
    for answer_list in answers:
        answer_count = len(answer_list)
    
        # Build reduction graph (union-find DS)
        ufds = np.arange(answer_count)
        for i1, i2 in itools.combinations(ufds.copy(),2):  
            a1,a2 = answer_list[i1]["answer"],answer_list[i2]["answer"]
            if not a1 or not a2: continue # Impossible answer

            match = SequenceMatcher(a=a1,b=a2).find_longest_match(alo=0, ahi=len(a1), blo=0, bhi=len(a2))

            match_len = match.size
            if (match_len/len(a1) > merge_threshold  
                or 
                match_len/len(a2) > merge_threshold):

                ufds[i2] = ufds[i1] #(i2>i1) automatic union-find reduction

        # Reduce component
        new_answer_list = []
        ufds_u = np.unique(ufds)
        for u in ufds_u:
            ids, *_ = (ufds == u).nonzero()

            matchnig_answers = list(map(answer_list.__getitem__,ids))
            scores = map(op.itemgetter("score"),matchnig_answers)

            reduced_answer = max(matchnig_answers,key=op.itemgetter("score"))
            reduced_answer["score"] = _reduce_scores(scores,reduction_method=internal_conf_reduction)

            new_answer_list.append(reduced_answer)

        # Sort answers for later
        new_answer_list.sort(reverse=True,key=op.itemgetter("score"))

        new_answers.append(new_answer_list)
        
    # Reduce externally
    question_count = len(new_answers)
    answers_per_question = max(map(len,new_answers))
    
    ufds1 = np.repeat(np.arange(answers_per_question)[None],question_count,axis=0)
    ufds2 = np.repeat(np.arange(question_count)[None],answers_per_question,axis=0).T
    ufds = np.stack((ufds1,ufds2),axis=2)
    for i1,i2 in itools.combinations(range(question_count),2):
        
        answer_list1, answer_list2 = new_answers[i1],new_answers[i2]
        answer_count1, answer_count2 = len(answer_list1), len(answer_list2)
        for j1,j2 in itools.product(range(answer_count1),range(answer_count2)):

            a1, a2 = answer_list1[j1]["answer"], answer_list2[j2]["answer"]   
            if not a1 or not a2: continue # Impossible answer

            match = SequenceMatcher(a=a1,b=a2).find_longest_match(alo=0, ahi=len(a1), blo=0, bhi=len(a2))

            match_len = match.size
            if (match_len/len(a1) > merge_threshold  
                or 
                match_len/len(a2) > merge_threshold):

                ufds[i2,j2,0] = ufds[i1,j1,0] #(i2>i1) automatic union-find reduction
                ufds[i2,j2,1] = ufds[i1,j1,1] 

    ufds = _np_to_tuple(ufds)
    ufds_u = set(itools.chain(*ufds))

    # Reduce component
    final_answers = []
    for u in ufds_u:

        if len(new_answers[u[1]]) <= u[0]: continue # Not valid

        answer_candidates = []
        for i in range(question_count):
            try:
                candidate_id = ufds[i].index(u)
                answer_candidates.append(new_answers[i][candidate_id])
            except ValueError:
                answer_candidates.append(dict(answer="",score=new_answers[i][-1]["score"])) # Worst score

        scores = map(op.itemgetter("score"),answer_candidates)
        best_answer = max(answer_candidates,key=op.itemgetter("score"))
        best_answer["score"] = _reduce_scores(scores,reduction_method=external_conf_reduction)

        final_answers.append(best_answer)

    # Erase impossible
    final_answers = [fa for fa in final_answers if fa["answer"]]

    return final_answers
    
        
def relations_from_answers(answers : dict, 
                            external_conf_reduction="min_confidence", 
                            internal_conf_reduction="bayesian",
                            merge_threshold=0.9,
                            top_k = -1):
    relations = []
    for relation,answer_dict1 in answers:
        for class_key in answer_dict1.keys():
            answer_dict2 = answer_dict1[class_key]
            for entity  in answer_dict2.keys():
                answer_dict3 = answer_dict2[entity]

                answer_list = map(op.itemgetter("answers"),answer_dict3)
                answer_list = map(op.methodcaller("__getitem__",slice(top_k)),answer_list)
                answer_list = list(map(_filter_impossible_ans,answer_list))
                merged_answer = _merge_answers(answer_list,
                                                external_conf_reduction=external_conf_reduction,
                                                internal_conf_reduction=internal_conf_reduction,
                                                merge_threshold=merge_threshold)

                relations.extend((entity,relation,ca["answer"],ca["score"]) for ca in merged_answer)
    return relations


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    with open(args.answers,"r") as answer_file:
        answers = ijson.kvitems(answer_file,"")
        relations = relations_from_answers(answers,
                                            external_conf_reduction=args.confidence_reduction,
                                            internal_conf_reduction=args.confidence_reduction_internal,
                                            merge_threshold=args.relation_merge_threshold,
                                        top_k=args.relations_per_question)

    # Filter poor confidence
    relations = itools.filterfalse(lambda rel: rel[3] < args.confidence_threshold,relations) 

    df_columns = ["left_entity","relation","right_entity"]
    if args.include_confidence: df_columns.append("confidence")

    df = pd.DataFrame(dict(zip(df_columns,zip(*relations))))
    df.to_csv(sys.stdout,index=False)

