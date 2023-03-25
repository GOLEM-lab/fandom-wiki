#!/bin/bash

INPUT_FILE=$1
FILE_BASENAME=$(basename ${INPUT_FILE})
FILE_BASENAME=${FILE_BASENAME//".json"/}

# Make directories
mkdir -p results/${FILE_BASENAME}

# Hparam
relations_per_question=( 1 2 4 8 16 32 )
confidence_reduction=( "min_confidence" "max_confidence" "bayesian" )
confidence_reduction_internal=( "max_confidence" "bayesian" )

for rpq in ${relations_per_question[@]}; do
for cr in ${confidence_reduction[@]}; do
for cri in ${confidence_reduction_internal[@]}; do

echo "$rpq $cr $cri"

python src/relation_extraction/relations_from_answers.py \
    --answers $INPUT_FILE \
    --relations_per_question $rpq \
    --confidence_reduction $cr \
    --confidence_reduction_internal $cri \
    --include_confidence \
    --confidence_threshold 0.1 \
    > results/${FILE_BASENAME}/relex_fanfiction_harrypotter_rpq${rpq}_cr${cr}_cri${cri}.csv &

done; done; done;

wait