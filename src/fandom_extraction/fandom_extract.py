"""TODO complete documentation/license"""
from argparse import ArgumentParser


import sys
import operator as op
from bs4 import BeautifulSoup

def detect_pagetype_from_html(html : BeautifulSoup):

    text_box = html.find(id="wpTextbox1")
    if text_box is None: return "modern"

    element_class = text_box['class']
    if "dummyTextbox" in element_class:
        return "modern"
    else:
        return "legacy"


# Extract source
def _parse_wtsource_legacy(html : BeautifulSoup):
    text_box = html.find(id="wpTextbox1")
    text_box = text_box.string

    return text_box

def _parse_wtsource_modern(html : BeautifulSoup):
    text_box = html.find(role="textbox")
    
    paragraphs = text_box.find_all("p")
    paragraphs = map(op.attrgetter("string"),paragraphs)
    
    text = "\n".join(paragraphs)

    return text

def parse_wtsource(html : str, page_type="auto"):
    """ Extract WikiText source from html (supplied as a string) of a "Source Edit" Fandom page
        (Usually located at a URL ending in an "action=edit" parameter, e.g 
        https://bakerstreet.fandom.com/wiki/John_Watson?action=edit).
        
        Returns WikiText source as a string."""

    soup = BeautifulSoup(html, 'html.parser')

    if page_type == "auto":
        page_type = detect_pagetype_from_html(soup)

    if page_type == "legacy":
        return _parse_wtsource_legacy(soup)
    else:
        return _parse_wtsource_modern(soup)
    

def _build_parser():
    parser = ArgumentParser()

    parser.add_argument("--page_type",choices=["auto","legacy","modern"],default="auto",help="What kind of Wikitext source edit to parse.")

    return parser

if __name__ == "__main__":    
    parser = _build_parser()
    args = parser.parse_args()

    content = sys.stdin.read()
    sys.stderr.write(content)

    text_box= parse_wtsource(content,page_type=args.page_type)
    sys.stdout.write(text_box)