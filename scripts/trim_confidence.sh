#!/bin/bash

export CONF_LIM=$1

# Print header
read LINE_READ
echo $LINE_READ

function process_line {

    LINE_READ=$1
    conf=$(rev <<< $LINE_READ | cut -d, -f1 | rev )

    if (( $(echo "$conf > $CONF_LIM" | bc -l) )); then
        echo $LINE_READ
    fi
}

while read LINE_READ; do process_line "$LINE_READ"; done
