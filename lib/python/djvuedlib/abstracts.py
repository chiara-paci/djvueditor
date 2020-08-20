import collections
import collections.abc
import abc
import json
import os.path

from . import jsonlib

class DictProxy(collections.abc.MutableMapping,abc.ABC):
    """Abstract for masquerading an OrderedDict. 

    A  DictProxy has  OrderedDict  standard behaviour,  with just  few
    details changed. See for example SerializedDict.

    """

    def __init__(self,base=None):
        collections.abc.MutableMapping.__init__(self)
        if base is None:
            self._dict=collections.OrderedDict()
        else:
            self._dict=collections.OrderedDict(base)
    
    def copy(self): return self._dict.copy()

    def __str__(self): return self._dict.__str__()
    def __repr__(self): return self._dict.__repr__()
    def __getitem__(self,*args,**kwargs):  return self._dict.__getitem__(*args,**kwargs)
    def __delitem__(self,*args,**kwargs):  return self._dict.__delitem__(*args,**kwargs)
    def __setitem__(self,*args,**kwargs): self._dict.__setitem__(*args,**kwargs)
    def __iter__(self,*args,**kwargs): return self._dict.__iter__(*args,**kwargs)
    def __len__(self,*args,**kwargs): return self._dict.__len__(*args,**kwargs)
    def __contains__(self,*args,**kwargs):  return self._dict.__contains__(*args,**kwargs)
    def __reversed__(self,*args,**kwargs): return self._dict.__reversed__(*args,**kwargs)

    def __serialize__(self): return self._dict

class ListProxy(collections.abc.MutableSequence,abc.ABC):
    """Abstract for masquerading a list.
    """

    def __init__(self,inner_list):
        collections.abc.MutableSequence.__init__(self)
        self._list=inner_list

    def __str__(self): return self._list.__str__()
    def __repr__(self): return self._list.__repr__()
    def __getitem__(self,key): return self._list.__getitem__(key)
    def __delitem__(self,key): return self._list.__delitem__(key)
    def __setitem__(self,key,obj): return self._list.__setitem__(self,key,obj)
    def __len__(self,*args,**kwargs): return self._list.__len__(*args,**kwargs)
    def __iter__(self,*args,**kwargs): return self._list.__iter__(*args,**kwargs)
    def __reversed__(self,*args,**kwargs): return self._list.__reversed__(*args,**kwargs)
    def __contains__(self,*args,**kwargs): return self._list.__contains__(*args,**kwargs)
    def sort(self,*args,**kwargs): return self._list.sort(*args,**kwargs)
    def insert(self,key,obj): return self._list.insert(self,key,obj)

    def __serialize__(self): return self._list

class KeyValuePair(collections.abc.MutableMapping,abc.ABC):

    def __init__(self,key,value):
        collections.abc.MutableMapping.__init__(self)
        self._key=key
        self._value=value

    def __str__(self): return "(%s,%s)" % (self._key,self._value)

    def __getitem__(self,idx):
        if idx not in [ 0, 1, "key","value" ]:
            raise KeyError(idx)
        if idx in [ 0, "key"]: return self._key
        return self._value

    def __setitem__(self,idx,obj):
        if idx not in [ 0, 1, "key","value" ]:
            raise KeyError(idx)
        if idx in [ 0, "key"]: 
            self._key=obj
            return
        self._value=obj

    def __delitem__(self,idx): return 
    def __iter__(self,*args,**kwargs): return ["key","value"].__iter__(*args,**kwargs)
    def __len__(self,*args,**kwargs): return 2
    def __contains__(self,idx): return idx in [ 0, 1, "key","value" ]
    def __reversed__(self,*args,**kwargs): return  KeyValuePair(self._value,self._key) 
    def __serialize__(self): return (self._key,self._value)


class SerializedDict(DictProxy):
    """A standard OrderedDict that keeps a copy of self on filesystem, in
       ''fpath'', in json format."""

    def __init__(self,fpath):
        DictProxy.__init__(self)
        self._fpath=fpath
        if os.path.exists(self._fpath):
            self._dict=jsonlib.json_load(self._fpath)
            for k in self._dict:
                val=self._dict[k]
                if isinstance(val,collections.OrderedDict):
                    if "year" in val:
                        self._dict[k]=common.dict_to_utc(val)
        
    def _save(self):
        with open(self._fpath,"w") as fd:
            json.dump(self._dict,fd)

    def __delitem__(self,*args,**kwargs):  
        ret=self._dict.__delitem__(*args,**kwargs)
        self._save()
        return ret

    def __setitem__(self,*args,**kwargs): 
        ret=self._dict.__setitem__(*args,**kwargs)
        self._save()
        return ret


    
