from . import abstracts
import collections
import os.path

from . import book as libbook
from . import ocr as libocr
from . import encode as libencode


class Project(abstracts.SerializedDict): 

    class ProjectMetadataItem(abstracts.KeyValuePair):
        def __init__(self,project,key,value):
            self._project=project
            abstracts.KeyValuePair.__init__(self,key,value)

        def __setitem__(self,idx,obj): 
            ret=abstracts.KeyValuePair.__setitem__(self,idx,obj)
            self._project._save()
            return ret

    class ProjectMetadata(abstracts.ListProxy):
        def __init__(self,project,inner_list=[]):
            self._project=project
            inner_list=[ self._clean_value(x) for x in inner_list ]
            abstracts.ListProxy.__init__(self,inner_list)

        def _clean_value(self,obj):
            if type(obj) in (tuple,list): 
                key,val=obj
            if type(obj) in (dict,Project.ProjectMetadataItem,collections.OrderedDict):
                key=obj["key"]
                val=obj["value"]
            return Project.ProjectMetadataItem(self._project,key,val)

        def delete_items(self,idx_list):
            to_remove=[ self._list[idx] for idx in idx_list ]
            self._list=[ obj for obj in self._list if obj not in to_remove ]
            self._project._save()

        def add_empty_item(self):
            self._list.append( Project.ProjectMetadataItem(self._project,"","") )
            self._project._save()

        def __setitem__(self,key,obj): 
            obj=self._clean_value(obj)
            ret=abstracts.ListProxy.__setitem__(self,key,obj)
            self._project._save()
            return ret

        def __delitem__(self,key):  
            ret=abstracts.ListProxy.__delitem__(self,key)
            self._project._save()
            return ret

        def sort(self,*args,**kwargs): 
            ret=abstracts.ListProxy.sort(self,*args,**kwargs)
            self._project._save()
            return ret

        def insert(self,key,obj):
            obj=self._clean_value(obj)
            ret=abstracts.ListProxy.insert(self,key,obj)
            self._project._save()
            return ret

        def write_on(self,fname):
            with open(fname,'w') as fd:
                for obj in self._list:
                    fd.write('%(key)s "%(value)s"\n' % obj)

    class ProjectSubDict(abstracts.DictProxy):
        def __init__(self,project,base=None):
            abstracts.DictProxy.__init__(self,base=base)
            self._project=project

        def __delitem__(self,*args,**kwargs):  
            ret=self._dict.__delitem__(*args,**kwargs)
            self._project._save()
            return ret

        def __setitem__(self,*args,**kwargs): 
            ret=self._dict.__setitem__(*args,**kwargs)
            self._project._save()
            return ret

    @property
    def base_dir(self):
        return os.path.dirname(self._path)
                
    def __init__(self,fpath):
        abstracts.SerializedDict.__init__(self,fpath)
        self.book=None
        if "Metadata" in self:
            if type(self["Metadata"]) in [  collections.OrderedDict, dict ]:
                self["Metadata"]=list(self["Metadata"].items())
            self["Metadata"]=self.ProjectMetadata(self,self["Metadata"])
        else:
            self["Metadata"]=self.ProjectMetadata(self)

        self._setup_options()
        self._setup_book()

    def new_project(self,metadata,tiff_dir):
        self.clear()
        self["Tiff directory"]=tiff_dir
        f_metadata=os.path.join(self["Tiff directory"],"metadata")
        if os.path.exists(f_metadata):
            new_metadata_dict=collections.OrderedDict(metadata)
            with open(f_metadata,'r') as fd:
                for r in fd.readlines():
                    r=r.strip()
                    if not r: continue
                    t=r.strip().split()
                    key=t[0]
                    value=(" ".join(t[1:])).strip('"')
                    if key in new_metadata_dict:
                        if new_metadata_dict[key]==value: continue
                        if not new_metadata_dict[key]:
                            new_metadata_dict[key]=value
                            continue
                        while key in new_metadata_dict: key+="_"
                    new_metadata_dict[key]=value
            metadata=list(new_metadata_dict.items())

        self["Metadata"]=self.ProjectMetadata(self,metadata)
        self._save()
        self._setup_options()
        self._setup_book()

    def _setup_options(self):
        if "Encoding Options" in self:
            self["Encoding Options"]=self.ProjectSubDict(self,self["Encoding Options"])
        else:
            self["Encoding Options"]=self.ProjectSubDict(self)

        for k,default in [ 
                ("bitonal_encoder","cjb2"),
                ("color_encoder","csepdjvu"),
                ("c44_options",""),
                ("cjb2_options","-lossy"),
                ("cpaldjvu_options",""),
                ("csepdjvu_options",""),
                ("minidjvu_options","--match --pages-per-dict 100") ]:
            if k not in self["Encoding Options"]:
                self["Encoding Options"][k]=default

        if "Ocr Options" in self:
            self["Ocr Options"]=self.ProjectSubDict(self,self["Ocr Options"])
        else:
            self["Ocr Options"]=self.ProjectSubDict(self)

        for k,default in [ 
                ("ocr_engine","tesseract"),
                ("tesseract_options",""),
                ("cuneiform_options","") ]:
            if k not in self["Ocr Options"]:
                self["Ocr Options"][k]=default

        if "Max threads" not in self: self["Max threads"]=10

        self._save()

    def _setup_book(self):
        if "Pages" in self:
            self["Pages"]=self.ProjectSubDict(self,self["Pages"])
        else:
            self["Pages"]=self.ProjectSubDict(self)
        if "Tiff directory" not in self: return
        file_list=self._file_list()
        self.book=libbook.Book()
        self.book.set_pages(file_list)
        
    def _file_list(self):
        f_metadata=os.path.join(self["Tiff directory"],"metadata")
        self["Metadata"].write_on(f_metadata)

        f_bookmarks=os.path.join(self["Tiff directory"],"bookmarks")
        # da aggiungere <------

        file_list=[
            (f_metadata,"metadata",""),
            # (f_bookmarks,"bookmarks",""), <--- da aggiungere
        ]
        if "Cover back" in self:
            file_list.append( (self["Cover back"], "cover_back", "cover" ) )
        if "Cover front" in self:
            file_list.append( (self["Cover front"], "cover_front", "back" ) )
        
        cback=self["Cover back"] if "Cover back" in self else ""
        cfront=self["Cover front"] if "Cover front" in self else ""
        page_list=[]
        with os.scandir(self["Tiff directory"]) as it:
            for entry in it:
                if not entry.is_file(): continue
                if entry.path in [cback,cfront,f_metadata,f_bookmarks]: continue
                ext = entry.name.split('.')[-1]
                ext = ext.lower()
                if (ext not in ['tif', 'tiff', 'pnm', 'pbm', 'pgm', 'ppm']): continue
                page_list.append( entry.path )
        
        page_list.sort()

        ### qui il modello si puo' complicare (title=numero di pagina)
        ### unico vincolo non ce ne devono essere due uguali
        ### v. djvubind
        num=1
        for p in page_list:
            if p in self["Pages"]:
                title=self["Pages"][p]
            else:
                title=str(num)
                self["Pages"][p]=title
            file_list.append( (p,"page",title) )
            num+=1
        return file_list

    def apply_ocr(self):
        max_threads=self["Max threads"]
        ocr=libocr.Tesseract(self["Ocr Options"]['tesseract_options'])
        print('Performing optical character recognition.')
        self.book.apply_ocr(ocr,max_threads)
        
    def djvubind(self,djvu_name):
        if len(self.book.pages) == 0: return
        self["Metadata"].write_on(f_metadata)
        print('Binding %d file(s).' % len(self.book.pages))
        enc_opts=self["Encoding Options"].copy()
        enc_opts["ocr"]=(self["Ocr Options"]["ocr_engine"] != "no ocr")
        print('Encoding all information to %s.' % djvu_name)
        enc = libencode.Encoder(enc_opts)
        enc.enc_book(self.book, djvu_name)
