from langchain.output_parsers import PydanticOutputParser
from langchain.prompts.few_shot import FewShotPromptTemplate
from langchain.prompts.prompt import PromptTemplate

from pydantic import BaseModel, Field
from enum import Enum, EnumMeta
from typing import List

import csv


def relations_from_csv(csvreader : csv.DictReader) -> EnumMeta:
    csvreader = iter(csvreader) 
    header = next(csvreader)

    prop_col = header.index("prop")
    propLabel_col = header.index("propLabel")

    enum_dict = {r[prop_col] : r[propLabel_col] for r in csvreader}
    RelationEnum = Enum("RelationEnum",enum_dict)

    return RelationEnum

    
def output_parser_from_relations(relationType : EnumMeta) -> PydanticOutputParser:
    
    class RelationTriple(BaseModel):
        subj : str = Field(description="Subject of the relation")
        obj : str = Field(description="Object of the relation")
        rel : relationType = Field(description="Type of relation")

    class Relations(BaseModel):
        relations : List[RelationTriple] = Field(description="List of relation triples.")

    parser = PydanticOutputParser(pydantic_object=Relations)

    return parser

EXAMPLE_INPUT = "Text:\n{text}"
EXAMPLE_OUTPUT = "Relations:\n{realtions}"

EXAMPLE_TEMPLATE = "\n".join(EXAMPLE_INPUT,EXAMPLE_OUTPUT)

def get_examples_prompt(examples : dict):
    example_prompt = PromptTemplate.from_template(EXAMPLE_TEMPLATE)

    prompt = FewShotPromptTemplate(
        examples=examples, 
        example_prompt=example_prompt, 
        suffix=EXAMPLE_INPUT, 
        input_variables=["text"])

    return prompt


FINAL_TEMPLATE = (
"""Extract relations from the text.
{instructions}
{exmaples}""")
def get_final_prompt(examples_prompt, output_parser):

    final_prompt = FINAL_TEMPLATE.format(
        instructions=output_parser.get_format_instructions(),
        exmaples=examples_prompt.format("{input}"))
    final_prompt = PromptTemplate.from_template(final_prompt)


    return final_prompt

    
