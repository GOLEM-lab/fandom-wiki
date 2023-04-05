#!/bin/bash

source env/bin/activate

cat data/enwiki-20160501/validation.csv |  python -m src.relation_extraction.qa_run_eval --relations data/meta/wd_relations_naive.txt -fp16 --symmetric_relations --relations_per_question 8 > results/wikidata_eval_answers.json
