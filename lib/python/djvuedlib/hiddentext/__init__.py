# -*- coding: utf-8 -*-

import re

from . import djvused_hiddentext_parser
from . import djvused_hiddentext_semantics

from .djvused_hiddentext_semantics import OcrBlock as DjvusedOcrBlock

def djvused_parse_text(text):
    text=re.sub(r'\s+',' ',text)
    text=text.strip()
    text=re.sub(r'\\\\','&#92;',text)
    text=re.sub(r'\\"','&#34;',text)
    semantics=djvused_hiddentext_semantics.HiddenTextSemantics()
    parser=djvused_hiddentext_parser.djvused_hiddentextParser()
    return parser.parse(text,rule_name='grammar',semantics=semantics) 

def djvused_parse_file(fname):
    with open(fname,'r') as fd:
        text=fd.read()
    return djvused_parse_text(text)


    # class MyParser(bind_conf_parser.bind_confParser): pass

    # def t_clean(s):
    #     s=re.sub('//.*$','',s)
    #     s=re.sub('#.*$','',s)
    #     s=s.replace('\n',' ')
    #     s=s.replace('\t',' ')
    #     if type(s)==unicode: return s
    #     return unicode(s.decode('utf-8'))

    # fd=open(fname,"r")
    # txt=u" ".join(map(t_clean,fd.readlines()))
    # fd.close()

    # txt=re.sub('/\*.*?\*/',' ',txt)
    # txt=re.sub(' +',' ',txt).strip()

    # parser = MyParser()

    # return parser.parse(txt,rule_name=rule_name,semantics=semantics)
