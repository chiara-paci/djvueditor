# -*- coding: utf-8 -*-

import html

class OcrBlock(object):
    levels=['page','column','region','para','line','word','char']

    def __init__(self,level,xmin,ymin,xmax,ymax,content):
        self.parent=None
        self._level=level
        self._xmin=xmin
        self._ymin=ymin
        self._xmax=xmax
        self._ymax=ymax

        if type(content) is str:
            self.text=html.unescape(content)
            self.children=[]
        else:
            self.text=""
            self.children=content
            for ch in self.children:
                ch.parent=self

    def _get_xmin(self): return self._xmin
    def _get_ymin(self): return self._ymin
    def _get_xmax(self): return self._xmax
    def _get_ymax(self): return self._ymax

    def _get_level(self): 
        if self.parent is None:
            ok_levels=self.levels
        else:
            ok_levels=self.levels[1+self.levels.index(self.parent.level):]
        if self._level in ok_levels: 
            return self._level
        self._level=ok_levels[0]
        return self._level

    def _set_xmin(self,value):
        self._xmin=value
        if self.parent is None: return
        if self.parent._xmin<=self._xmin: return
        self.parent.xmin=self._xmin

    def _set_ymin(self,value):
        self._ymin=value
        if self.parent is None: return
        if self.parent._ymin<=self._ymin: return
        self.parent.ymin=self._ymin

    def _set_xmax(self,value):
        self._xmax=value
        if self.parent is None: return
        if self.parent._xmax>=self._xmax: return
        self.parent.xmax=self._xmax

    def _set_ymax(self,value):
        self._ymax=value
        if self.parent is None: return
        if self.parent._ymax>=self._ymax: return
        self.parent.ymax=self._ymax

    def _set_level(self,value):
        if self.parent is None:
            ok_levels=self.levels
        else:
            ok_levels=self.levels[1+self.levels.index(self.parent.level):]
        if value in ok_levels: 
            self._level=value
            return
        if self._level in ok_levels: 
            return
        self._level=ok_levels[0]
        return 

    level=property(_get_level,_set_level)
    xmin=property(_get_xmin,_set_xmin)
    ymin=property(_get_ymin,_set_ymin)
    xmax=property(_get_xmax,_set_xmax)
    ymax=property(_get_ymax,_set_ymax)

    @property
    def _w(self):
        return self._xmax-self._xmin

    @property
    def _h(self):
        return self._ymax-self._ymin

    @property
    def content(self):
        if not self.children: return self.text
        return " ".join([ ch.content for ch in self.children ])

    def __str__(self):
        S="<%s (%d,%d) (%d,%d)" % (self.level,self.xmin,self.ymin,self.xmax,self.ymax)
        if not self.children:
            S+=' "%s">' % self.text
            return S
        for ch in self.children:
            S+=' %s' % str(ch)
        S+='>'
        return S

    def __repr__(self): return self.__str__()

    def out_tree(self,indent=""):
        S="%s(%s %d %d %d %d" % (indent,self.level,self.xmin,self.ymin,self.xmax,self.ymax)
        if not self.children:
            S+=' "%s")\n' % self.text.replace('"','\\"')
            return S
        S+="\n"
        for ch in self.children:
            S+=ch.out_tree(indent=indent+"    ")
        S+="%s)\n" % indent
        return S

    def _bg_color(self):
        return (255,255,128,128)

    def _fg_color(self):
        if self.level=="page": return (255,255,0,255)
        if self.level=="column": return (0,0,0,255)
        if self.level=="region": return (0,255,255,255)
        if self.level=="para": return (255,0,255,255)
        if self.level=="line": return (0,0,255,255)
        if self.level=="word": return (0,255,0,255)
        return (255,0,0,255)

    def highlight_rects(self):
        if self.level in ["word","char"]:
            ret= [
                ( (self.xmin,self.ymin,self._w,self._h),
                  self._bg_color(),self._fg_color() )
            ]
        else:
            ret= [
                ( (self.xmin,self.ymin,self._w,self._h),self._bg_color(),None )
            ]
        for ch in self.children:
            ret+=ch.border_rects()
        return ret

    def border_rects(self):
        ret= [
            ( (self.xmin,self.ymin,self._w,self._h),None,self._fg_color() )
        ]
        for ch in self.children:
            ret+=ch.border_rects()
        return ret

    def remove_rules(self,ind,count):
        for c in range(count):
            self.children.pop(ind)

    def sub_rule_levels(self):
        return self.levels[1+self.levels.index(self.level):]

    def insert_rules(self,ind,count):
        sub_rule_levels=self.levels[1+self.levels.index(self.level):]
        if not sub_rule_levels: return
        level=sub_rule_levels[0]
        for c in range(count):
            block=OcrBlock(level,self._xmin,self._ymin,self._xmax,self._ymax,"")
            self.insert_rule(ind,block)

    def create_rule(self,level,xmin,ymin,xmax,ymax,text):
        block=OcrBlock(level,xmin,ymin,xmax,ymax,text)
        self.insert_rule(0,block)

    def insert_rule(self,ind,obj):
        ok_levels=self.sub_rule_levels()
        if obj.level not in ok_levels:
            obj.level=ok_levels[0]
        self.children.insert(ind,obj)
        obj.parent=self
        self._xmin=min(self._xmin,obj._xmin)
        self._ymin=min(self._ymin,obj._ymin)
        self._xmax=max(self._xmax,obj._xmax)
        self._ymax=max(self._ymax,obj._ymax)

    def append_rule(self,obj):
        ok_levels=self.sub_rule_levels()
        if obj.level not in ok_levels:
            obj.level=ok_levels[0]
        self.children.append(obj)
        obj.parent=self
        self._xmin=min(self._xmin,obj._xmin)
        self._ymin=min(self._ymin,obj._ymin)
        self._xmax=max(self._xmax,obj._xmax)
        self._ymax=max(self._ymax,obj._ymax)

    def index(self,child):
        return self.children.index(child)

    def count_children(self):
        return len(self.children)

    def get_rule(self,ind):
        if ind>=len(self.children): return None
        return self.children[ind]

    def split_rule(self,obj,splitted):
        ind=self.children.index(obj)
        words=splitted[1:]
        words.reverse()
        for w in words:
            dup=obj.copy()
            dup.text=w
            self.children.insert(ind+1,dup)
        obj.text=splitted[0]

    def pop_rule(self,obj): 
        ind=self.children.index(obj)
        return self.children.pop(ind)

    def move_left(self,obj): 
        p_ind=self.parent.index(self)
        self.pop_rule(obj)
        self.parent.insert_rule(p_ind+1,obj)

    def move_up(self,obj):
        ind=self.children.index(obj)
        if ind==0: return
        self.children.pop(ind)
        self.children.insert(ind-1,obj)

    def move_down(self,obj):
        ind=self.children.index(obj)
        if ind==len(self.children)-1: return
        self.children.pop(ind)
        self.children.insert(ind+1,obj)

    def move_right(self,obj):
        ind=self.children.index(obj)
        if ind==0: return
        self.children.pop(ind)
        self.children[ind-1].append_rule(obj)

    def merge_below_rule(self,obj):
        ind=self.children.index(obj)
        if ind==len(self.children)-1: return
        obj.concatenate_after(self.children[ind+1])
        self.children.pop(ind+1)

    def merge_above_rule(self,obj):
        ind=self.children.index(obj)
        if ind==0: return
        obj.concatenate_before(self.children[ind-1])
        self.children.pop(ind-1)

    def duplicate_rule(self,obj):
        ind=self.children.index(obj)
        dup=obj.copy()
        self.children.insert(ind+1,dup)

    def copy(self,parent=None):
        if parent is None: parent=self.parent
        dup=OcrBlock(self._level,self._xmin,self._ymin,self._xmax,self._ymax,self.text)
        dup.parent=parent
        if not self.children: return dup
        dup.children=[ ch.copy(parent=dup) for ch in self.children ]
        return dup

    def concatenate_after(self,other):
        if self.level!=other.level:
            if self.levels.index(self.level) > other.levels.index(self.level):
                self.level=other.level
        self.text+=other.text
        if other.children:
            self.children+=[ ch.copy(parent=self) for ch in other.children ]
        self._xmin=min(self._xmin,other._xmin)
        self._ymin=min(self._ymin,other._ymin)
        self._xmax=max(self._xmax,other._xmax)
        self._ymax=max(self._ymax,other._ymax)

    def concatenate_before(self,other):
        if self.level!=other.level:
            if self.levels.index(self.level) > other.levels.index(self.level):
                self.level=other.level
        self.text=other.text+self.text
        if other.children:
            self.children=[ ch.copy(parent=self) for ch in other.children ]+self.children
        self._xmin=min(self._xmin,other._xmin)
        self._ymin=min(self._ymin,other._ymin)
        self._xmax=max(self._xmax,other._xmax)
        self._ymax=max(self._ymax,other._ymax)

    def crop_to_children(self):
        if not self.children: return
        self._xmin=min( [ ch._xmin for ch in self.children ] )
        self._ymin=min( [ ch._ymin for ch in self.children ] )
        self._xmax=max( [ ch._xmax for ch in self.children ] )
        self._ymax=max( [ ch._ymax for ch in self.children ] )

    def shift_down(self,val):
        if self.children:
            for obj in self.children: 
                obj.shift_down(val)
            self.crop_to_children()
            return
        self._ymin=max(0,self._ymin-val)
        self._ymax=max(0,self._ymax-val)

    def shift_up(self,val):
        if self.children:
            for obj in self.children: 
                obj.shift_up(val)
            self.crop_to_children()
            return
        self._ymin+=val
        self._ymax+=val

    def shift_left(self,val):
        if self.children:
            for obj in self.children: 
                obj.shift_left(val)
            self.crop_to_children()
            return
        self._xmin=max(0,self._xmin-val)
        self._xmax=max(0,self._xmax-val)

    def shift_right(self,val):
        if self.children:
            for obj in self.children: 
                obj.shift_right(val)
            self.crop_to_children()
            return
        self._xmin+=val
        self._xmax+=val

class OcrGrammar(object):
    def __init__(self,ast):
        self.ast=ast
        self.rules=[]
        for rule in self.ast:
            if type(rule)==list:
                self.rules+=self._delist(rule)
            else:
                self.rules.append(rule)

    def out_tree(self):
        S=""
        for r in self.rules:
            S+=r.out_tree()
        return S

    def _delist(self,L):
        if type(L)!=list:
            return [L]
        ret=[]
        for obj in L:
            ret+=self._delist(obj)
        return ret

    def __str__(self):
        return u"GRAMMAR"

    def __repr__(self): return self.__str__()

    def insert_rules(self,parent,ind,count):
        if parent is None:
            block=OcrBlock("page",0,0,0,0,"")
            for c in range(count):
                self.rules.insert(ind,block.copy())
            return
        parent.insert_rules(ind,count)

    def remove_rules(self,parent,ind,count):
        if parent is None:
            for c in range(count):
                self.rules.pop(ind)
            return
        parent.remove_rules(ind,count) 

    def index(self,obj):
        if obj.parent is None:
            return self.rules.index(obj)
        return obj.parent.index(obj)

    def count_children(self,obj):
        if obj is None:
            return len(self.rules)
        return obj.count_children()

    def get_rule(self,parent,ind):
        if parent is None:
            if ind >= len(self.rules): return None
            return self.rules[ind]
        return parent.get_rule(ind)

    def duplicate_rule(self,obj):
        if obj.parent is not None:
            obj.parent.duplicate_rule(obj)
            return
        ind=self.rules.index(obj)
        dup=obj.copy()
        self.rules.insert(ind+1,dup)

    def merge_below_rule(self,obj):
        if obj.parent is not None:
            obj.parent.merge_below_rule(obj)
            return
        ind=self.rules.index(obj)
        if ind==len(self.rules)-1: return
        obj.concatenate_after(self.rules[ind+1])
        self.rules.pop(ind+1)

    def merge_above_rule(self,obj):
        if obj.parent is not None:
            obj.parent.merge_below_rule(obj)
            return
        ind=self.rules.index(obj)
        if ind==0: return
        obj.concatenate_before(self.rules[ind-1])
        self.rules.pop(ind-1)

    def split_rule(self,obj,splitted):
        if obj.children: return
        if obj.parent is not None:
            obj.parent.split_rule(obj,splitted)
            return
        ind=self.rules.index(obj)
        words=splitted[1:]
        words.reverse()
        for w in words:
            dup=obj.copy()
            dup.text=w
            self.rules.insert(ind+1,dup)
        obj.text=splitted[0]

    def shift_down_rule(self,obj,val):
        obj.shift_down(val)

    def shift_up_rule(self,obj,val):
        obj.shift_up(val)

    def shift_right_rule(self,obj,val):
        obj.shift_right(val)

    def shift_left_rule(self,obj,val):
        obj.shift_left(val)

    def create_rule(self,parent,level,xmin,ymin,xmax,ymax,text):
        if parent is None:
            block=OcrBlock(level,xmin,ymin,xmax,ymax,text)
            self.rules.insert(0,block)
            return
        parent.create_rule(level,xmin,ymin,xmax,ymax,text)

    def move_up(self,obj): 
        if obj.parent is not None:
            obj.parent.move_up(obj)
            return
        ind=self.rules.index(obj)
        if ind==0: return
        self.rules.pop(ind)
        self.rules.insert(ind-1,obj)

    def move_down(self,obj): 
        if obj.parent is not None:
            obj.parent.move_down(obj)
            return
        ind=self.rules.index(obj)
        if ind==len(self.rules)-1: return
        self.rules.pop(ind)
        self.rules.insert(ind+1,obj)

    def move_left(self,obj): 
        if obj.parent is None: return
        if obj.parent.parent is not None:
            obj.parent.move_left(obj)
            return
        p_ind=self.rules.index(obj.parent)
        obj.parent.pop_rule(obj)
        self.rules.insert(p_ind+1,obj)

    def move_right(self,obj): 
        if obj.parent is not None:
            obj.parent.move_right(obj)
            return
        ind=self.rules.index(obj)
        if ind==0: return
        self.rules.pop(ind)
        self.rules[ind-1].append_rule(obj)

class HiddenTextSemantics(object):
    def __init__(self):
        pass

    def grammar(self, ast):
        return OcrGrammar(ast)

    def list_rule(self, ast):
        ast=list(ast)
        return ast

    def rule(self, ast):
        args=ast[1:-1]
        return OcrBlock(*args)

    def integer(self,ast):
        return int(ast)

    def content(self,ast):
        if ast[0]=='"': return ast[1]
        return ast

    def etext(self,ast): return ast
    def label(self,ast): return ast
    def xmin(self,ast): return ast
    def ymin(self,ast): return ast
    def xmax(self,ast): return ast
    def ymax(self,ast): return ast

    def _default(self,ast):
        return ast
