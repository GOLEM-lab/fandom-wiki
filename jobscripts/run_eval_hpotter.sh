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
FW_RUN_EVAL_INPUT_FILE=${FW_RUN_EVAL_INPUT_FILE:-"data/annotation/harry_potter_annotations.csv"}
FW_RUN_EVAL_RELATIONS_FILE=${FW_RUN_EVAL_RELATIONS_FILE:-"data/meta/annotations_relations_handcrafted_filter.txt"}
FW_RUN_EVAL_FILE_COMMAND=${FW_RUN_EVAL_FILE_COMMAND:-cat "${FW_RUN_EVAL_INPUT_FILE}"}

FW_RUN_EVAL_ARGS=${FW_RUN_EVAL_ARGS:-"-fp16 --symmetric_relations --relations_per_question 128 --infer_entity_class"}

if [[ ! -z "$FW_RUN_EVAL_USE_NOREL" ]]; then
    FW_RUN_EVAL_OUTPUT_FILE=${FW_RUN_EVAL_OUTPUT_FILE:-"results/harrypotter_test_answers_norel.json"}
    $FW_RUN_EVAL_FILE_COMMAND |  python -m src.relation_extraction.qa_run_eval --relations "$FW_RUN_EVAL_RELATIONS_FILE" $FW_RUN_EVAL_ARGS --use_norel > $FW_RUN_EVAL_OUTPUT_FILE
else
    FW_RUN_EVAL_OUTPUT_FILE=${FW_RUN_EVAL_OUTPUT_FILE:-"results/harrypotter_test_answers.json"}
    $FW_RUN_EVAL_FILE_COMMAND |  python -m src.relation_extraction.qa_run_eval --relations "$FW_RUN_EVAL_RELATIONS_FILE" $FW_RUN_EVAL_ARGS > $FW_RUN_EVAL_OUTPUT_FILE
fi