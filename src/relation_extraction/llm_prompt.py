from langchain.output_parsers import PydanticOutputParser
from langchain.prompts.few_shot import FewShotPromptTemplate
from langchain.prompts.prompt import PromptTemplate

import pandas as pd
import numpy as np

from enum import Enum, EnumMeta
from typing import List, Dict, Optional

from argparse import ArgumentParser
import pprint

def filter_examples(example_df : pd.DataFrame, relation_df : pd.DataFrame):

    relations = relation_df["prop"].unique()
    relation_labels = relation_df["propLabel"].unique()

    relation_remap = dict(zip(relations,relation_labels))

    example_df : pd.DataFrame = example_df[example_df["relation"].isin(relations)]
    example_df = example_df.copy()

    example_df["relation"] = example_df["relation"].map(relation_remap)

    return example_df

def reformat_examples(example_df : pd.DataFrame) -> List[Dict[str,str]]:
    
    def make_relations_dict(df : pd.DataFrame):
        records = df.to_dict(orient="records")
        return records

    def make_relations_prettydict(df : pd.DataFrame):
        records = df.to_dict(orient="records")
        records = pprint.pformat(records)
        records = records.replace("{","{{")
        records = records.replace("}","}}")

        return records

    relation_columns_old = ["context","left_entity","right_entity","relation"]
    relation_columns_new = ["text","subject","object","relation"]

    example_df = example_df.rename(columns=dict(zip(relation_columns_old,relation_columns_new)))
    example_df = example_df[relation_columns_new]
    
    example_df_group = example_df.groupby("text",group_keys=False)
    example_df = example_df_group[relation_columns_new[1:]].apply(make_relations_dict)
    example_df.name = "relations"
    example_df = example_df.reset_index()
    example_df["relations_text"] = example_df_group[relation_columns_new[1:]].apply(make_relations_prettydict).to_list()
        
    examples = example_df.to_dict(orient="records")
    return examples

class RelationExtractionPromptBuilder:
    EXAMPLE_INPUT = "Text:\n{text}"
    EXAMPLE_OUTPUT = "Relations:\n{relations_text}"

    EXAMPLE_TEMPLATE = "\n\n".join((EXAMPLE_INPUT,EXAMPLE_OUTPUT))
    EXAMPLE_TEMPLATE_FINAL = "\n\n".join((EXAMPLE_INPUT,"Relations:\n"))

    PROMPT_HEADER = "Extract relations from the text."

    INST_HEADER = "The relation must be one of the following:"
    INST_FOOTER = "And the result must be provided in JSON format."

    def __init__(self, relations : pd.DataFrame, examples : Optional[dict] = None):
        self.relations = relations
        self.examples = examples

    def _get_instructions(self):
        rel_desc = [f"\"{r.propLabel}\": {r.description}" for _, r in self.relations.iterrows()]
        rel_desc = "\n".join(rel_desc)

        instructions = "\n\n".join((self.INST_HEADER, rel_desc, self.INST_FOOTER))

        return instructions


    def _get_examples_prompt(self,prefix_prompt=None):

        if self.examples is None:
            raise ValueError("\"examples\" attribute is None. Cannot generate a few-shot prompt without examples.")

        example_prompt = PromptTemplate.from_template(self.EXAMPLE_TEMPLATE)

        prompt = FewShotPromptTemplate(
            examples=self.examples, 
            example_prompt=example_prompt, 
            suffix=self.EXAMPLE_TEMPLATE_FINAL,
            prefix=prefix_prompt,
            input_variables=["text"])

        return prompt

    def get_prompt(self):
        instructions = self._get_instructions()
        prefix = "\n\n".join((self.PROMPT_HEADER,instructions))
        try:
            final_prompt = self._get_examples_prompt(prefix)
        except ValueError:
            final_prompt = None

        # Assemble
        if final_prompt is not None: 
            return final_prompt
            
        final_template = "\n\n".join((self.PROMPT_HEADER,instructions,"Text:","{text}"))
        final_prompt = PromptTemplate.from_template(final_template)

        return final_prompt

def build_prompt(
        rel_df : pd.DataFrame, 
        ex_df : pd.DataFrame = None,
        *,
        random_example_selection : bool = True,
        num_examples : int = 2) -> PromptTemplate:

    ex = None
    if ex_df is not None:
        ex_df = filter_examples(ex_df,rel_df)
        ex = reformat_examples(ex_df)

        if random_example_selection:
            perm = np.random.permutation(len(ex))
            perm = perm[:num_examples]

            ex = list(map(ex.__getitem__,perm))

        else:
            ex = ex[:num_examples]
    
    repb = RelationExtractionPromptBuilder(rel_df,ex)
    prompt = repb.get_prompt()

    return prompt

def _build_parser():
    parser = ArgumentParser()
    
    # Input files
    input_group = parser.add_argument_group("Input options")
    input_group.add_argument("--relations", required=True, help="Filepath of the \".csv\" file containing the relations to predict and their descriptions.")
    input_group.add_argument("--target", required=True, help="Filepath of the \".csv\" file containing the target examples")
    input_group.add_argument("--examples", help="Filepath of the \".csv\" file containing examples to use for few-shot.")

    behaviour_group = parser.add_argument_group("Behaviour options")
    behaviour_group.add_argument("--num_examples", type=int, default=3, help="Maximum number of examples to use.")
    behaviour_group.add_argument("--example_selection", choices=["sequential","random"], default="sequential", help="How to choose the examples to use.")

    return parser

if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    rel_df = pd.read_csv(args.relations)
    ex_df = None
    if args.examples:
        ex_df = pd.read_csv(args.examples)

    tgt_df = pd.read_csv(args.target)
    tgt_df = filter_examples(tgt_df,rel_df)
    tgt = reformat_examples(tgt_df)

    prompt = build_prompt(
        rel_df=rel_df,
        ex_df=ex_df,
        random_example_selection=(args.example_selection == "random"),
        num_examples=args.num_examples)

    for e in tgt:
        p = prompt.format(text=e["text"])
        
        print(p)

        print()

        print("### ANNOTATION")
        print(e["relations_text"])
        print("### END ANNOTATION")

        print()
