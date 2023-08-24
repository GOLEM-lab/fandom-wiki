# fandom-wiki
Extraction of structured and unstructured information from fandom.com pages.

This repo contains the following:

* Metadata files (`data/`)
* Python programs that can either serve as modules or be used as stand-alone scripts (`src/`)
* Bash scripts that perform very specialized operations (`scripts/`)

## Setup and Dependencies
All the code is developed for and tested on:
* Python 3.10(.9)
* Bash 5.1.16

However most functionality is expected to work on similar setups.

To start using the repo install the PyPy packages listed in `requirements.txt` using the `pip` package manager:

`pip install -r requirements.txt`

The only non-PyPy software requirement is the `curl` terminal application. Which is only required for downloading data from web-servers.

## Usage of Main Functionalities

_Technical Detail_: Most scripts (python or bash) use standard input/output streams to consume/produce data so that the same interface may be used to: be fed and feed other processes, or, read and write from/to files. In particular, this means that many of the individual functionalities bellow can be chained by use of the appropriate system IPC mechanisms.

### Download and Parse Web Data

`scripts/download_fandom_data.sh` provides functionality to donwload and parse the WikiText source of fandom pages from a list of links. The links are read from standard input, one link per line, comments starting with "#" are ignored.

To read the links from a file that lists them (such as `data/fandom_links.txt`):

`scripts/download_fandom_data.sh < data/fandom_links.txt`

or using pipes `|`:

`cat data/fandom_links.txt | scripts/download_fandom_data.sh`

In the above command, `cat` may be substituted by any program that produces (in stdout) links in the described format, for instance a web-crawler that identifies the pages of interest.

By default, the script spits out the WikiText (all articles concatenated) to standard output, this may be used to write a single file containing all the WikiText data:

`scripts/download_fandom_data.sh < data/fandom_links.txt > data/all_wikitext.txt`

If separation of the data from each link is wanted, the `-od` option can be used to specify an "output directory" in which to dump the files corresponding to the articles pointed by each link. The files will be organized in subdirectories according to the name of the wiki they belong to.

`scripts/download_fandom_data.sh -od data/wikis/ < data/fandom_links.txt`

The above script will produce a directory tree looking similar to (with possibly more data):

```
data
├── fandom_links.txt
└── wikis
    ├── harrypotter
    │   ├── Draco_Malfoy.txt
    │   └── Sirius_Black.txt
    ├── marvelcinematicuniverse
    │   ├── Black_Widow.txt
    │   ├── Captain_America.txt
    │   └── Winter_Soldier.txt
    └── starwars
        ├── Anakin_Skywalker.txt
        ├── Ben_Solo.txt
        └── Rey_Skywalker.txt
```

#### Customizing the Data Download Pipeline
For **large-scale download** operations, flooding the web-servers with requests typically sets off anti-saturation mechanisms from the servers. As a consequence the download speed capacity is largely limited and sometimes slowed down to a halt, for instance if the server blacklists the IP temporarily as a preemptive measure against DDoS attacks.

There are many strategies that may be employed to mitigate this situation. One reliable solution when applicable, is to exchange metadata with the web-server to ensure that request policies are followed and, possibly, announce the good intent of the requests (when the web-server implements such policies). Most download managers can be configured to behave _perceptivelly_ like described.

Since the download script uses `curl` under-the-hood, it will benefit from the configuration to curl. To customize (locally) the `curl` configuration, create a `.curlrc` file in the preferred directory:

`mkdir config && touch config/.curlrc`

then edit the file and include the necessary confuration ([curl reference](https://everything.curl.dev/)). Finally execute the download command with the `CURL_HOME` environment variable set to the directory where `.curlrc` is located:

`CURL_HOME=${PWD}/config/ scripts/download_fandom_data.sh -od data/wikis/ < data/fandom_links.txt`

As another alternative, one may decide to implement a custom download script. In that case it is worth having a look at `src/fandom_extraction/fandom_extract.py`, which implements the HTML parsing capabilities (it obtains the WikiText from the article editing HTML page).

### Parsing WikiText Elements
Parsing WikiText elements involves extracting structured units of data from a WikiText source file. Some example of these units are **Templates** (such as InfoBoxes or Quotes), **Categories**, **Links (to other articles)**, **References** and **Sections** among others. So far only template extraction is fully implemented.

To perform WikiText parsing `src/fandom_extraction/wikitext_extract.py` is a python script that has a variety of options that enable different extraction, filtering and cleaning operations. The script works by reading WikiText from standard input, it then writes the parsed elements in `JSON` format to standard output.

To showcase a particular use-case, lets consider:

`cat data/wikis/*/* | python -m src.fandom_extraction.wikitext_extract --templates Character character "Character Infobox" "Individual infobox" --template_param_wl name sex born nation affiliation job actor --clean_xml > data/infobox_templates.json`

Breaking the command down:

* `cat data/wikis/*/*` Concatenates all (previously) donwloaded fandom articles
* `python src.fandom_extraction.wikitext_extract` The wikitext parsing script ran as a python module, it consumes the concatenated wikitext
* `--templates Character character "Character Infobox" "Individual infobox"` Extract the templates that match the given template names. In this case the template names correspond to the Infobox generation templates.
* `--template_param_wl name sex born nation affiliation job actor` Store only the given parameters (infobox fields in this case) from the extracted templates.
* `--clean_xml` Clean the XML data in the WikiText before parsing. XML data is often not interesting (page styling for example) so we don't want it in the output. Cleaning XML also makes parsing faster as there is less text to parse and less complexity.
* `> data/infobox_templates.json` Redirect the output to an output file (instead of letting it print in the terminal).

The script parameters `--templates` and `--template_param_wl` take a list of names in the example, however regular expressions (and lists of them) are also allowed so the above parameter values can be written as

`--templates "([Cc]aracter|[Ii]ndividual)( [Ii]nfobox)?"`

and

`--template_param_wl "name|sex|born|nation|affiliation|job|actor"`

There are plenty other options that the script accepts which can be consulted in detail by using the parameter `--help`

`python -m src.fandom_extraction.wikitext_extract --help`

Finally if the WikiText parser implementation is of interest, it is available in the python module `src/fandom_extraction/wikitext_regex.py`

### Relation Extraction from Text

At the time of writing this guide, two fundamentally distinct methods have been implemented for relation extraction:

1. Reducing Relation Extraction to a Question Answering Task.
2. LLM prompting for direct Relation Extraction.

We shall next briefly describe each approach.

#### Reducing Relation Extraction to a Question Answering Task

In this approach we reduce the task of extracting a relation triple `<subject>:<relation>:<object>`, to answering a question of the type `"What entity has relation <relation> with <subject>?"` or possibly a more natural question for the given `subject` and `relation`. E.g. to extract the relation `<Harry Potter>:<enemy of>:<Voldemort>`, we might ask the question `"Who is an enemy of Harry Potter?"`. We then feed the question, together with the text that relation extraction is to be performed on, as context to an Extractive-Question-Answering system (in particular, we used a QA fine-tunned LM). The answer outputed by the system (if any), is then a `<object>` candidate, which we might keep or discard according to different criteria (such as the confidence of the QA system in the answer).

To implement this scheme three data sources are needed:
1. Question templates associated to each relation (e.g. ). Each relation might have more than one associated question.
2. List of entities to place as subject in the relations (e.g. )
3. Piece of text to perform relation extraction on.

From the first two (1,2), all the possible triples which have a subject from (2) and a relation from (1) are considered. Some optimization is possible if entities have a class annotated and the relations specify the classes that they support. Then the questions associated to all the triples are created and fed to the QA system along with context, thus generating answers to the questions. To do this run:

`python -m src.relation_extraction.qa --entities <entites_file> --relations <relations_file> < <context_file> > <output_file>`

for example:

`python -m src.relation_extraction.qa --entities data/meta/test_entities.csv --relations data/meta/annotations_relations_handcrafted.txt < data/wikis/harrypotter/Hermione_Granger.txt > results/hermione_answers.json`

The context (`<context_file>`) is formatless text, the expected format and fields for the rest of data sources can be checked in the files referenced in the example. The script outputs a `.json` file that contains the generated answers for each question in `<relations_file>`.
Additional options are available through command line arguments (e.g. to controll the underlying QA model, and its parameters), the documentation can be accessed through `python -m src.relation_extraction.qa --help`.

We have thus far extracted the output (answers) from the QA segment of the pipeline, however for most purposes (benchmarking, compatibility, knowledge graph building, ...) we are interested in relation triples, so it is time to reduce answers into triples. To that end, we can employ the following script:

`python -m src.relation_extraction.relations_from_answers --answers <answers_file> > <output_relations>`

Where `<answers_file>` is the previously obtained output and `<output_relations>` will be a `.csv` file with triples, and possibly a confidence score of the system for each triple. As with the previous script, there are a lot of options to tailor the behaviour of the script to each users need. Once again, consult them trough the `--help` argument.

There is only one thing left to do, which is to evaluate the generated relations, since this part of the workflow is common to every relation extraction method it will be discussed in a separate section. We will now comment on the other implemented approach, namely the use of LLMs to solve the task direclty.






