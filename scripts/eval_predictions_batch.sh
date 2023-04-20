#!/bin/bash

INPUT_DIR=$1
CONF_LIM=$2
RELATION_FILE=$3

CONF_LIM=${CONF_LIM:-0}

DIR_BASENAME=$(basename ${INPUT_DIR})
DIR_BASENAME=results/${DIR_BASENAME}_scores
mkdir -p $DIR_BASENAME

for f in "${INPUT_DIR}/"*".csv"; do
    echo $f

    PIPE=$(mktemp)
    rm $PIPE && mkfifo $PIPE
    

    OUTPUT_FILE=$(basename ${f})
    OUTPUT_FILE=${DIR_BASENAME}/${OUTPUT_FILE}

    cat $f | python -c "import pandas as pd; import sys; df = pd.read_csv(sys.stdin,header=0); df[df.confidence >= $CONF_LIM].to_csv(sys.stdout,index=False)" > $PIPE &

    cat data/enwiki-20160501/validation.csv | 
    python -m src.utils.compute_eval_score \
        --predictions $PIPE \
        --gold /dev/stdin \
        --relations $RELATION_FILE > $OUTPUT_FILE

    rm $PIPE
done