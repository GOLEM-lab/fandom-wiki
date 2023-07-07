from langchain.output_parsers import PydanticOutputParser
from langchain.prompts.few_shot import FewShotPromptTemplate, FewShotPromptWithTemplates
from langchain.prompts.prompt import PromptTemplate

import pandas as pd

from pydantic import BaseModel, Field
from enum import Enum, EnumMeta
from typing import List, Dict, Optional

def reformat_examples(example_df : pd.DataFrame) -> List[Dict[str,str]]:
    
    def make_relations_dict(df : pd.DataFrame):
        records = df.to_dict(orient="records")
        records = records
        return records

    relation_columns_old = ["context","left_entity","right_entity","relation"]
    relation_columns_new = ["text","subj","obj","rel"]

    example_df = example_df.rename(columns=dict(zip(relation_columns_old,relation_columns_new)))
    example_df = example_df[relation_columns_new]
    
    example_df_group = example_df.groupby("text",group_keys=False)
    example_df = example_df_group[relation_columns_new[1:]].apply(make_relations_dict)
    example_df.name = "relations"
    example_df = example_df.reset_index()
        
    examples = example_df.to_dict(orient="records")
    return examples

class RelationExtractionPromptBuilder:
    EXAMPLE_INPUT = "Text:\n{text}"
    EXAMPLE_OUTPUT = "Relations:\n{relations}"

    EXAMPLE_TEMPLATE = "\n\n".join((EXAMPLE_INPUT,EXAMPLE_OUTPUT))

    PROMPT_HEADER = "Extract relations from the text."

    def __init__(self, relations : Dict[str,str], examples : Optional[dict] = None):
        self.relations = relations
        self.examples = examples

    def _get_output_parser(self) -> PydanticOutputParser:
        RelationEnum = Enum("RelationEnum", self.relations)

        class RelationTriple(BaseModel):
            subj : str = Field(description="Subject of the relation")
            obj : str = Field(description="Object of the relation")
            rel : RelationEnum = Field(description="Type of relation")

        class Relations(BaseModel):
            relations : List[RelationTriple] = Field(description="List of relation triples.")

        parser = PydanticOutputParser(pydantic_object=Relations)

        return parser

    def _get_examples_prompt(self,prefix_prompt=None):

        if self.examples is None:
            raise ValueError("\"examples\" attribute is None. Cannot generate a few-shot prompt without examples.")

        example_prompt = PromptTemplate.from_template(self.EXAMPLE_TEMPLATE)
        suffix_prompt = PromptTemplate.from_template(self.EXAMPLE_INPUT)

        prompt = FewShotPromptWithTemplates(
            examples=self.examples, 
            example_prompt=example_prompt, 
            suffix=suffix_prompt,
            prefix=prefix_prompt,
            input_variables=["text"],
            partial_variables=)

        return prompt

    def get_prompt(self):

        # Get prompt sections
        output_parser = self._get_output_parser()
        output_parser_prompt = output_parser.get_format_instructions()

        try:
            prefix_template = "\n\n".join((self.PROMPT_HEADER,"{instructions}"))
            prefix_template = PromptTemplate(template=prefix_template,
                                        input_variables=[],
                                        partial_variables=dict(instructions=output_parser_prompt))
            final_prompt = self._get_examples_prompt(prefix_template)
        except ValueError:
            final_prompt = None


        # Assemble
        if final_prompt is not None: 
            return final_prompt
            
        final_template = "\n\n".join((self.PROMPT_HEADER,"{instructions}","{input}"))
        final_prompt = PromptTemplate(template=final_template,
                                    input_variables=["text"],
                                    partial_variables=dict(instructions=output_parser_prompt))

        return final_prompt

    
