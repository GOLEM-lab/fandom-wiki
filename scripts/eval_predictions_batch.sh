#!/bin/bash

INPUT_DIR=$1
CONF_LIM=$2
RELATION_FILE=$3

CONF_LIM=${CONF_LIM:-0}


for f in "${INPUT_DIR}/"*".csv"; do
    echo $f

    PIPE=$(mktemp -u)
    mkfifo $PIPE

    cat $f | scripts/trim_confidence.sh $CONF_LIM > $PIPE &

    head -n 1000 data/enwiki-20160501/validation.csv | 
    python -m src.utils.compute_eval_score \
        --predictions $PIPE \
        --gold /dev/stdin \
        --relations $RELATION_FILE

    rm $PIPE
done