"""TODO complete documentation/license"""

from wikitext_regex import WikitextPatterns

from argparse import ArgumentParser
import json

import sys
import regex
import itertools as itools

# Exported names
wikitext_patterns = WikitextPatterns()
def extract_templates(text,*,template_name=None,nested=False):
    """TODO Docstring"""
    matches = wikitext_patterns.extract_templates(text,template_name=template_name,nested=nested)
    templates = list(map(wikitext_patterns.template_to_dict,matches))
    
    return templates

def clean_comments(text):
    """TODO Docstring"""
    text = wikitext_patterns.XML_COMMENT.sub("",text)
    return text

def clean_xml(text):
    """TODO Docstring"""
    text = wikitext_patterns.XML_STUFF.sub("",text)
    return text

def substitute_wt_links(text,use_display_when_possible=False):
    """TODO Docstring"""
    text = wikitext_patterns.WT_LINK.sub("\\g<wiki_ref>",text)
    return text

def _build_parser():
    """TODO Docstring"""
    parser = ArgumentParser(
        add_help="Script that performs extraction and mild-preprocessing of data from text in\n"+
        "WikiText source format.\n\nInput text is consumed from the standard input stream (stdin), likewise\n"+
        "Output is produced in the standard output stream (stdout).")

    # Wikitext preprocessing
    parser.add_argument("--substitute_wt_links",dest="substitute_wt_links",action="store_true",help="Substitute wikitext link objects for the link text.")
    parser.add_argument("--no-substitute_wt_links",dest="substitute_wt_links",action="store_false",help="Leave wikitext links unchanged (Default).")
    parser.add_argument("--wt_links_to_display_text",dest="wt_links_to_display_text",action="store_true",help="When doing WT link substitution, substitute for the display text when possible.")
    parser.set_defaults(substitute_wt_links=False)
    parser.set_defaults(wt_links_to_display_text=False)

    parser.add_argument("--no-clean_comments",dest="no-clean_comments",action="store_false",help="Do not clean WT source comments.")
    parser.add_argument("--clean_xml",dest="clean_xml",action="store_true",help="Clean xml elements from source.")
    parser.set_defaults(clean_comments=True)
    parser.set_defaults(clean_xml=False)

    # Template extraction 
    parser.add_argument("-t","--templates",dest="templates",type=str,nargs="*",help="Name of the template to extract.")
    parser.add_argument("--nested",action="store_true",help="Extract nested WikiText elements. Significantly more computationally expensive.")
    parser.add_argument("--template_param_wl",type=str,nargs="*",default=[".*"],help="Template named params whitelist (which to extract, ignoring the rest; default all).")
    parser.add_argument("--template_param_bl",type=str,nargs="*",default=[".++."],help="Template named params blacklist (which to ignore, extracting the rest; default none).")
    parser.set_defaults(nested=False)

    return parser

if __name__ == "__main__":

    # Parse args
    parser = _build_parser()
    args = parser.parse_args()

    text = sys.stdin.read()

    # Preprocess (TODO: Abstract this)
    if args.clean_comments:
        text = clean_comments(text)

    if args.clean_xml:
        text = clean_xml(text)

    if args.substitute_wt_links:
        text = substitute_wt_links(text,args.wt_links_to_display_text)

    if args.templates:
        template_criteria = "|".join(args.templates)
        if not template_criteria: template_criteria = None
        templates = extract_templates(text,template_name=template_criteria,nested=args.nested)

        # TODO: Abstract this maybe
        template_param_wl = regex.compile("|".join(args.template_param_wl),regex.DOTALL | regex.V1)
        template_param_bl = regex.compile("|".join(args.template_param_bl),regex.DOTALL | regex.V1)

        filtered_templates = templates
        for template in templates:
            params = template["params"]
            keep_keys = filter(template_param_wl.match,params)
            keep_keys = itools.filterfalse(template_param_bl.match,keep_keys)
            keep_keys = set(keep_keys)
            
            template["params"] = {p_name: p_value for p_name, p_value in params.items() if p_name in keep_keys}
            
        template_dict = dict(templates=templates)
        json.dump(template_dict,sys.stdout)
        
    else:
        sys.exit("No extraction operation selected, please check --help.")

