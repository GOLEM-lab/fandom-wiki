# fandom-wiki
Extraction of structured and unstructured information from fandom.com pages.

This repo contains the following:

* Metadata files (`data/`)
* Python programs that can either serve as modules or be used as stand-alone scripts (`src/`)
* Bash scripts that perform very specialized operations (`scripts/`)

## Setup
To start using the repo just install the PyPy packages listed in `requirements.txt` using the `pip` package manager:Bash

`pip install -r requirements.txt`

## Usage of Main Functionalities

_Technical Detail_: Most scripts (python or bash) use standard input/output streams to consume/produce data so that the same interface may be used to: be fed and feed other processes, or, read and write from/to files. In particular, this means that many of the individual functionalities bellow can be chained by use of the appropriate system IPC mechanisms.

### Download and Parse Web Data

`scripts/download_fandom_data.sh` provides functionality to donwload and parse the WikiText source of fandom pages from a list of links. To read the links from a file that lists them (such as `data/fandom_links.txt`):


`./scripts/download_fandom_data.sh < data/fandom_links.txt` 

or

`cat data/fandom_links.txt | ./scripts/download_fandom_data.sh` 


by default the script spits out the WikiText (all articles concatenated) to standard output, this may be used to