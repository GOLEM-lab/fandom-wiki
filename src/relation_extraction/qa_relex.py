import transformers
import pandas as pd
import numpy as np

from difflib import SequenceMatcher

from argparse import ArgumentParser

import typing
import operator as op
import functools as ftools
import itertools as itools

import io
import sys


def read_entities(entities : io.TextIOBase):
    
    entity_list = map(op.methodcaller("strip"),entities.readlines())
    entity_list = filter(bool,entity_list)
    entity_list = map(op.methodcaller("split",":"),entity_list)
    entity_list = list(entity_list)           

    classes = set(map(op.itemgetter(1),entity_list))
    classes = dict(zip(classes,itools.repeat(None)))

    for c in classes:
        c_entities = filter(lambda e: e[1] == c,entity_list)
        c_entities = map(op.itemgetter(0),c_entities)
        classes[c] = list(c_entities)

    return classes

def read_relations(relations : io.TextIOBase):
    
    relation_list = []
    for line_i, line in enumerate(relations.readlines()):
        line = line.strip()
        if not line:
            continue

        if line.startswith("*"): # New relation
            cl_left, rel_name, cl_right = line[1:].split(":")
            rel_spec = dict(cl_left=cl_left,
                            rel_name=rel_name,
                            cl_right=cl_right,
                            verbaliztions=list())
            relation_list.append(rel_spec)
        else:   # Verbalization
            if not relation_list:
                raise RuntimeError(f"Invalid relation file format in line {line_i}. Verbalization with no active relation.\n"+
                                    "Verbalizations must be preceded by a relation spec (which has format \"*<class_left>:<relation_name>:<class_right>\").")

            if f"{cl_left}" not in line:
                raise RuntimeError(f"Invalid relation file format in line {line_i}. Missing entity format tag \"{{{cl_left}}}\" .\n"+
                                    "Verbalizations must contain an entity format tag with format \"{<class_left>}\" somewhere in the sentence.")

            relation_list[-1]["verbaliztions"].append(line)

    relations_by_subject = set(map(op.itemgetter("cl_left"),relation_list))    
    relations_by_subject = dict(zip(relations_by_subject,itools.repeat(None)))

    for s in relations_by_subject:
        s_rel = filter(lambda r: r["cl_left"] == s,relation_list)
        relations_by_subject[s] = list(s_rel)

    return relations_by_subject

def generate_verbalizations(entity_dict, relation_dict):
    classes = set(entity_dict) & set(relation_dict)
    for class_ in classes:
        for entity,relation in itools.product(entity_dict[class_],relation_dict[class_]):
            verb_inst = map(op.methodcaller("format_map",{class_:entity}),relation["verbaliztions"])
            verb_inst = list(verb_inst)

            yield (entity,relation), verb_inst

def generate_answers(context,verbalizations,qa,config):
    verb_accumulator = []
    parition_indices = []
    ent_rel_pairs = []
    for ent_rel, verb_inst in verbalizations:
        verb_accumulator.extend(verb_inst)
        parition_indices.append(len(verb_accumulator))
        ent_rel_pairs.append(ent_rel)

        if len(verb_accumulator) < config.batch_size:
            continue

        res = qa(question=verb_accumulator,context=context,
            batch_size=config.batch_size,
            max_seq_len=config.max_seq_len,
            doc_stride=config.doc_stride,
            top_k=config.relations_per_question,
            handle_impossible_answer=config.use_norel)

        for ent_rel2, start_i, end_i in zip(ent_rel_pairs,
                                            [0] + parition_indices[:-1],
                                            parition_indices):

            yield ent_rel2, res[start_i:end_i]
            
        verb_accumulator.clear()
        parition_indices.clear()
        ent_rel_pairs.clear()

    if not verb_accumulator:
        return

    # Residual Batch
    res = qa(question=verb_accumulator,context=context,
        batch_size=config.batch_size,
        max_seq_len=config.max_seq_len,
        doc_stride=config.doc_stride,
        top_k=config.relations_per_question,
        handle_impossible_answer=config.use_norel)

    for ent_rel2, start_i, end_i in zip(ent_rel_pairs,
                                        [0] + parition_indices[:-1],
                                        parition_indices):

            yield ent_rel2, res[start_i:end_i]

def _filter_impossible_ans(answers : list):
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
    
        
def relations_from_answers(answers : typing.Iterable, 
                            external_conf_reduction="min_confidence", 
                            internal_conf_reduction="bayesian",
                            merge_threshold=0.9):
    relations = []
    for (entity,relation), answer_list in answers:
        answer_list = list(map(_filter_impossible_ans,answer_list))
        merged_answer = _merge_answers(answer_list,
                                        external_conf_reduction=external_conf_reduction,
                                        internal_conf_reduction=internal_conf_reduction,
                                        merge_threshold=merge_threshold)

        relations.extend((entity,relation["rel_name"],ca["answer"],ca["score"]) for ca in merged_answer)
    return relations

    
def _build_parser():
    parser = ArgumentParser()
    
    # Input files
    input_group = parser.add_argument_group("Input options")
    input_group.add_argument("--entities", required=True, help="Filepath of file with a list of entities: \"<entity_name>:<class>\".")
    input_group.add_argument("--relations", required=True, help="Filepath of file with a list of relations: a relation spec \"*<class_left>:<relation_name>:<class_right>\" followed by one or more verbalizations.")

    # Output format
    output_group = parser.add_argument_group("Output options")
    output_group.add_argument("--include_confidence", action="store_true", help="Include confidence level for each extracted triple.")
    output_group.set_defaults(include_confidence=False)

    # Extraction sensitivity params
    extraction_group = parser.add_argument_group("Extraction options")
    extraction_group.add_argument("--confidence_threshold", type=float, default=0.95, help="Extract triples when the confidence level is higher than \"CONFIDENCE_THRESHOLD\"")
    extraction_group.add_argument("--relations_per_question", type=int, default=16, help="How many relations to extract per each relation verbalization question.")
    extraction_group.add_argument("--confidence_reduction", choices=("min_confidence","max_confidence","bayesian",), default="max_confidence", help="How to reduce confidence score when merging competing relation predictions, across different relation questions.")
    extraction_group.add_argument("--confidence_reduction_internal", choices=("max_confidence","bayesian",), default="bayesian", help="How to reduce confidence score when merging competing relation predictions, within each relation question.")
    extraction_group.add_argument("--relation_merge_threshold", type=float, default=0.90, help="Minimum proportion of answer overlap required to merge two answers.")
    extraction_group.add_argument("--use_norel", action="store_true", help="Enable the possibility of predicting \"no-relation\"."+
                                                                "A no-relation prediction invalidates all predictions with strictly lower confidence."+
                                                                "This mechanism is complementary to the \"CONFIDENCE_THRESHOLD\" parameter.")
    extraction_group.set_defaults(use_norel=False)

    # System settings
    system_group = parser.add_argument_group("System options")
    system_group.add_argument("-lm", "--language_model", dest="language_model", default="deepset/roberta-large-squad2", help="QA Language model to use (HuggingFace).")
    system_group.add_argument("-bs", "--batch_size", dest="batch_size", type=int, default=32, help="Batch-size to use (inference).")
    system_group.add_argument("--max_seq_len", type=int, default=384, help="Maximum sequence length per processed context chunk. Higher values are computationally more expensive. May help with long distance dependencies in relations.")
    system_group.add_argument("--doc_stride", type=int, default=128, help="Maximum overlap length between neighbouring chunks. Higher values are computationally more expensive. May help with long distance dependencies in relations.")

    return parser

if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    with open(args.entities,"r") as entities_f:
        entity_dict = read_entities(entities_f)

    with open(args.relations,"r") as relations_f:
        relation_dict = read_relations(relations_f)

    # Read input context
    context = sys.stdin.read()

    # Initialize qa system
    qa = transformers.pipeline(model=args.language_model,device=0)

    verbalizations = generate_verbalizations(entity_dict,relation_dict)
    answers = generate_answers(context,verbalizations,qa,config=args)
    relations = relations_from_answers(answers,
                                        external_conf_reduction=args.confidence_reduction,
                                        internal_conf_reduction=args.confidence_reduction_internal,
                                        merge_threshold=args.relation_merge_threshold)

    # Filter poor confidence
    relations = itools.filterfalse(lambda rel: rel[3] < args.confidence_threshold,relations) 

    df_columns = ["entity1","relation_name","entity2"]
    if args.include_confidence: df_columns.append("confidence")

    df = pd.DataFrame(dict(zip(df_columns,zip(*relations))))
    df.to_csv(sys.stdout,index=False)

    

    
