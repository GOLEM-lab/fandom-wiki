from langchain.output_parsers import PydanticOutputParser
from langchain.prompts.few_shot import FewShotPromptTemplate
from langchain.prompts.prompt import PromptTemplate

from pydantic import BaseModel, Field
from enum import Enum, EnumMeta
from typing import List, Dict, Optional

class RelationExtractionPromptBuilder:
    EXAMPLE_INPUT = "Text:\n{text}"
    EXAMPLE_OUTPUT = "Relations:\n{relations}"

    EXAMPLE_TEMPLATE = "\n".join(EXAMPLE_INPUT,EXAMPLE_OUTPUT)

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

    def _get_examples_prompt(self):

        if self.examples is None:
            raise ValueError("\"examples\" attribute is None. Cannot generate a few-shot prompt without examples.")

        example_prompt = PromptTemplate.from_template(self.EXAMPLE_TEMPLATE)

        prompt = FewShotPromptTemplate(
            examples=self.examples, 
            example_prompt=example_prompt, 
            suffix=self.EXAMPLE_INPUT, 
            input_variables=["text"])

        return prompt

    def get_prompt(self):

        # Get prompt sections
        output_parser = self._get_output_parser()
        try:
            example_prompt = self._get_examples_prompt()
        except ValueError:
            example_prompt = None

        output_parser_prompt = output_parser.get_format_instructions()

        # Assemble
        paragraph = [PROMPT_HEADER,output_parser_prompt]
        if example_prompt is not None: 
            example_prompt = example_prompt.format("{input}")
            paragraph.append(example_prompt)

        final_prompt = "\n".join(paragraph)
        final_prompt = PromptTemplate.from_template(final_prompt)

        return final_prompt

    
