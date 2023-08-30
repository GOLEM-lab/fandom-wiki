#!/bin/bash

INPUT_DIR=$1
CONF_LIM=$2
RELATION_FILE=$3

CONF_LIM=${CONF_LIM:-0}

IMIN=$(dirname $0)

DIR_BASENAME=$(basename ${INPUT_DIR})
DIR_BASENAME=results/${DIR_BASENAME}_scores
mkdir -p $DIR_BASENAME

function eval_file {

    f=$1
    echo $f

    PIPE=$(mktemp)
    rm $PIPE && mkfifo $PIPE
    

    OUTPUT_FILE=$(basename ${f})
    OUTPUT_FILE=${DIR_BASENAME}/${OUTPUT_FILE}

    cat $f | $IMIN/filter_csv_confidence.sh $CONF_LIM > $PIPE &

    #cat data/enwiki-20160501/validation.csv | 
    cat data/annotation/harry_potter_annotations.csv | 
    
    python -m src.utils.compute_eval_score \
        --predictions $PIPE \
        --gold /dev/stdin \
        --relations_csv $RELATION_FILE > $OUTPUT_FILE

    rm $PIPE

}

for f in "${INPUT_DIR}/"*".csv"; do
    eval_file $f &
done

wait