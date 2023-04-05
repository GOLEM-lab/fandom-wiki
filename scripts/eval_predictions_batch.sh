#!/bin/bash

INPUT_DIR=$1
CONF_LIM=$2
RELATION_FILE=$3

CONF_LIM=${CONF_LIM:-0}


for f in "${INPUT_DIR}/"*".csv"; do
    echo $f 

    cat data/enwiki-20160501/validation.csv | 
    python -m src.utils.compute_eval_score \
        --predictions $f \
        --gold /dev/stdin \
        --relations $RELATION_FILE
done