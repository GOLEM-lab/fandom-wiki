import pandas as pd

import operator as op

import io

def read_relations(relations : io.TextIOBase) -> pd.DataFrame:
    
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
                            verbalizations=list())
            relation_list.append(rel_spec)
        else:   # Verbalization
            if not relation_list:
                raise RuntimeError(f"Invalid relation file format in line {line_i}. Verbalization with no active relation.\n"+
                                    "Verbalizations must be preceded by a relation spec (which has format \"*<class_left>:<relation_name>:<class_right>\").")

            if f"{cl_left}" not in line:
                raise RuntimeError(f"Invalid relation file format in line {line_i}. Missing entity format tag \"{{{cl_left}}}\" .\n"+
                                    "Verbalizations must contain an entity format tag with format \"{<class_left>}\" somewhere in the sentence.")

            relation_list[-1]["verbalizations"].append(line)
            
    relations = pd.DataFrame(relation_list)
    return relations

def generate_verbalizations(entities : pd.DataFrame, relations : pd.DataFrame):

    ent_rel = pd.merge(entities,relations,left_on="instance_of",right_on="cl_left")
    ent_rel = ent_rel.drop("instance_of",axis=1)
    formated = ent_rel.apply(lambda x: 
            list(map(
                op.methodcaller("format_map",{x.cl_left : x.entity_label}),
                x.verbalizations)),
        axis=1)
    formated.rename("verbalizations",inplace=True)
    
    res =  pd.concat((ent_rel[["entity_label","rel_name"]],formated),axis=1)
    return res