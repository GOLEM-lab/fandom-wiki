"""TODO complete documentation/license"""

from pipes import Template
import regex



class WikitextPatterns(object):
    """Class that encapsulates r-regex (recursive regular expression) patterns to match
        WikiText elements (such as templates and links)."""
    
    # Dummy class to act as a Namespace
    class Templates(object):
        pass
    
    # TODO comments on regex
    # XML
    ## XML Name
    XML_NAME = "[^=\\s>/]++"

    ## XML Attribute Value
    XML_ATTR_VALUE ="(?:\"[^\"]*+\"|'[^']*+')"

    ## XML Attributes
    Templates.XML_ATTRIBUTE = "{att_name}" + "\\s*+=\\s*+" + "{att_value}"
    XML_ATTRIBUTE = Templates.XML_ATTRIBUTE.format(
        att_name=XML_NAME,
        att_value=XML_ATTR_VALUE)

    _XML_NAME_ATTR_MAP = dict(elem_name=XML_NAME,att_pattern=XML_ATTRIBUTE) # Simplify further substitutions

    ## XML Tags
    Templates.XML_OPEN_TAG = "<{elem_name}(?:\\s*+{att_pattern})*+\\s*+>"
    Templates.XML_CLOSE_TAG = "</{elem_name}\\s*+>"
    Templates.XML_UNBALANCED_TAG = "<{elem_name}(?:\\s*+{att_pattern})*+\\s*+/>"
    Templates.XML_LONE_TAG = "<{elem_name}\\s*+>"


    XML_OPEN_TAG = Templates.XML_OPEN_TAG.format(**_XML_NAME_ATTR_MAP)
    XML_CLOSE_TAG = Templates.XML_CLOSE_TAG.format(elem_name=XML_NAME)
    XML_UNBALANCED_TAG = Templates.XML_UNBALANCED_TAG.format(**_XML_NAME_ATTR_MAP)
    XML_LONE_TAG = Templates.XML_LONE_TAG.format(**_XML_NAME_ATTR_MAP)

    ## XML Elements
    XML_ELEM = (
        "(?P<xml_balanced_elem>" +
        XML_OPEN_TAG +

        "(?:" +
        "(?&xml_balanced_elem)|." +
        ")*?" +

        XML_CLOSE_TAG +
        ")"
    )
    
    Templates.XML_ELEM = (
        Templates.XML_OPEN_TAG +

        "(?:" +
        "{}|.".format(XML_ELEM) +
        ")*?" +

        Templates.XML_CLOSE_TAG
    )


    XML_COMMENT = "(?P<xml_comment><!--(?:(?!-->).)*?-->)"

    XML_STUFF = "(?P<xml_stuff>{}|{}|{}|{})".format(XML_COMMENT,XML_UNBALANCED_TAG,XML_LONE_TAG,XML_ELEM)

    # WIKITEXT Template
    WT_TEMPLATE = (
    "(?P<wt_template>" +                                    
    "{{" +                              

    "(?:{(?&wt_template)}" +                                 
    "|(?&wt_template)" +
    "|{}".format(XML_STUFF)+                                         
    "|[^}{])*?" +                                     

    "}})"                                                  
    )

    Templates.WT_TEMPLATE = (
    "(" +                                    
    "{{\\s*?{template_name}" +                              

    "(?:{"+WT_TEMPLATE+"}" +                                 
    "|(?&wt_template)" +
    "|(?&xml_stuff)" +                                     
    "|[^}{])*?" +                                     

    "}})"                                                  
    )

    # WIKITEXT Link
    WT_LINK = "\\[\\[(?P<wiki_ref>.*?)(?:\\|(?P<wiki_ref_display>.*?))?\\]\\]"

    # WIKITEXT Value
    WT_VALUE = "(?P<wt_value>(?:{"+WT_TEMPLATE+"}|(?&wt_template)|"+WT_LINK+"|.)*?)"
    WT_TEMPLATE_FIELD = (                                  
    "(?:"+
    
     # Template Name Extraction
     "{{\\s*+(?:"+
     "(?P<template_name>(?>"+WT_VALUE+"(?=[|:])):(?!\\s)(?&wt_value))\\s*+(?=[|}])"+
     "|(?P<template_name>(?>(?&wt_value)(?=[|:]))):\\s++(?P<param_value>(?&wt_value))\\s*+(?=[|}])"+
     "|(?P<template_name>(?>(?&wt_value)(?=\\s*+[|:}])))\\s*+(?=[|}])"+
     ")"+

    ")"+

    # Parameter extraction
    "|(?:"+
    
     "\\|(?:"+
     "\\s*+(?P<param_name>(?>(?&wt_value)(?=\\s*+[=|])))\\s*+=\\s*+(?P<param_value>(?&wt_value))\\s*+(?=[|}])"+
     "|(?P<param_value>(?>(?&wt_value)(?=[=|}])))(?=[|}])"+
     ")"+

    ")"                                 
    )


    def __init__(self):
        # Compile regular expressions
        # XML
        self.XML_COMMENT = regex.compile(self.XML_COMMENT, regex.DOTALL | regex.V1)
        self.XML_ELEM = regex.compile(self.XML_ELEM, regex.DOTALL | regex.V1)
        self.XML_UNBALANCED_TAG = regex.compile(self.XML_UNBALANCED_TAG, regex.DOTALL | regex.V1)
        self.XML_STUFF = regex.compile(self.XML_STUFF, regex.DOTALL | regex.V1)


        # Wikitext
        self.WT_TEMPLATE = regex.compile(self.WT_TEMPLATE, regex.DOTALL | regex.V1)
        self.WT_TEMPLATE_FIELD = regex.compile(self.WT_TEMPLATE_FIELD, regex.DOTALL | regex.V1)
        self.WT_LINK = regex.compile(self.WT_LINK, regex.DOTALL | regex.V1)
        
    def extract_templates(self,text,*,template_name=None,nested=False):
        """TODO Docstring"""
        template_regex = self.WT_TEMPLATE
        if template_name is not None:
            template_regex = self.Templates.WT_TEMPLATE.replace("{template_name}","(?:{})(?:\\s|\\||:|}})".format(template_name))
            template_regex = regex.compile(template_regex,regex.DOTALL | regex.V1)
            
        matches = template_regex.findall(text,overlapped=nested)

        if matches:
            matches , *_ = zip(*matches) # Extract only first group

        return matches

    def template_to_dict(self,template_text : str):
        """TODO Docstring"""
        
        # TODO Comments
        fields = self.WT_TEMPLATE_FIELD.findall(template_text)

        template_name = fields[0][self.WT_TEMPLATE_FIELD.groupindex["template_name"]-1]
        
        param_dict = dict()
        positional_param = 0
        for field in fields:
            param_name = field[self.WT_TEMPLATE_FIELD.groupindex["param_name"]-1]
            param_value = field[self.WT_TEMPLATE_FIELD.groupindex["param_value"]-1]
            
            if not param_value: 
                continue
            if not param_name: 
                positional_param += 1
                param_name = str(positional_param)

            param_dict[param_name] = param_value
        
        template_dict = dict(template_name=template_name,params=param_dict)
        return template_dict

        

        

        
