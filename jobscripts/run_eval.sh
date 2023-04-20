#!/bin/env /bin/bash

#init
if [[ ! -z "$FW_RUN_EVAL_ENV_ACTIVATION_COMMAND" ]]; then
    $FW_RUN_EVAL_ENV_ACTIVATION_COMMAND
    
else
    if [[ ! -z "$FW_RUN_EVAL_CONDA_ENV" ]]; then
        conda activate env/
    else
        source env/bin/activate
    fi
fi

# Parse exported args
FW_RUN_EVAL_INPUT_FILE=${FW_RUN_EVAL_INPUT_FILE:-"data/enwiki-20160501/validation.csv"}
FW_RUN_EVAL_RELATIONS_FILE=${FW_RUN_EVAL_RELATIONS_FILE:-"data/meta/wd_relations_naive.txt"}
FW_RUN_EVAL_FILE_COMMAND=${FW_RUN_EVAL_FILE_COMMAND:-cat "${FW_RUN_EVAL_INPUT_FILE}"}

FW_RUN_EVAL_ARGS=${FW_RUN_EVAL_ARGS:-"-fp16 --symmetric_relations --relations_per_question 8"}

if [[ ! -z "$FW_RUN_EVAL_USE_NOREL" ]]; then
    FW_RUN_EVAL_OUTPUT_FILE=${FW_RUN_EVAL_OUTPUT_FILE:-"results/wikidata_eval_answers_norel.json"}
    $FW_RUN_EVAL_FILE_COMMAND |  python -m src.relation_extraction.qa_run_eval --relations "$FW_RUN_EVAL_RELATIONS_FILE" $FW_RUN_EVAL_ARGS --use_norel > $FW_RUN_EVAL_OUTPUT_FILE
else
    FW_RUN_EVAL_OUTPUT_FILE=${FW_RUN_EVAL_OUTPUT_FILE:-"results/wikidata_eval_answers.json"}
    $FW_RUN_EVAL_FILE_COMMAND |  python -m src.relation_extraction.qa_run_eval --relations "$FW_RUN_EVAL_RELATIONS_FILE" $FW_RUN_EVAL_ARGS > $FW_RUN_EVAL_OUTPUT_FILE
fi