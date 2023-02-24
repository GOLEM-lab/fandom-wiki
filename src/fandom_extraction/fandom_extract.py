"""TODO complete documentation/license"""

import sys
import operator as op
from bs4 import BeautifulSoup

# Extract source
def wtsource_from_html(html : str):
    """ Extract WikiText source from html (supplied as a string) of a "Source Edit" Fandom page
        (Usually located at a URL ending in an "action=edit" parameter, e.g 
        https://bakerstreet.fandom.com/wiki/John_Watson?action=edit).
        
        Returns WikiText source as a string."""

    soup = BeautifulSoup(html, 'html.parser')

    text_boxes = soup.find_all(id="wpTextbox1")
    text_boxes = map(op.attrgetter("string"),text_boxes)
    text_boxes = list(text_boxes)

    assert len(text_boxes) == 1 # Just to make sure the following assumption holds
    text_box = text_boxes[0]

    return text_box

if __name__ == "__main__":
    """TODO add cmd-line help"""
    
    content = sys.stdin.read()
    text_box= wtsource_from_html(content)
    sys.stdout.write(text_box)