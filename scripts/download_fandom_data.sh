#!/bin/bash

EXECUTION_PATH=$(dirname "$0") 

# Parse args
while [[ ! -z "$@" ]]; do

    [ ! -z "$OUT_DIR" ] && echo "Too many arguments."
        
    case "$1" in
        -od|-output_dir|--output_dir) OUT_DIR="$2"; shift 2 ;;
        *) OUT_DIR="$1"; shift ;;
    esac
done

function process_line {

    LINE_READ="$1" # Get function params

    # Strip comments and check if line is empty
    LINE_READ="${LINE_READ//#*/}"
    [ -z "$LINE_READ" ] && return 1
        
    # Download page and parse HTML to extract WikiText
    WIKITEXT=$(curl "${LINE_READ}?action=edit" 2>/dev/null | python "${EXECUTION_PATH}/../src/fandom_extraction/fandom_extract.py")
    STATUS=$?

    # Check if download and extraction went fine
    if (( $STATUS != 0 )); then 
        return 2
    fi

    # Write wikitext
    if [ ! -z "$OUT_DIR" ]; then

        # Extract Wiki and Article Name
        WIKI_NAME=$(echo "$LINE_READ" | grep -oP "https://(.*)\.fandom")
        ART_NAME=$(echo "$LINE_READ" | grep -oP "wiki/(.*)$") 

        WIKI_NAME="${WIKI_NAME//"https://"/}"
        WIKI_NAME="${WIKI_NAME//".fandom"/}"
        ART_NAME="${ART_NAME//"wiki/"/}"

        [ ! -d "${OUT_DIR}/${WIKI_NAME}" ] && mkdir -p "${OUT_DIR}/${WIKI_NAME}" 
        echo "$WIKITEXT" > "${OUT_DIR}/${WIKI_NAME}/${ART_NAME}.txt"
    else
        echo "$WIKITEXT"
    fi

}

# Process lines
while read LINE_READ; do process_line "$LINE_READ"; done
process_line "$LINE_READ" # Last line
