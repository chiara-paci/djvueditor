from . import abstracts
import collections
import os.path

from . import book as libbook
from . import ocr as libocr
from . import encode as libencode

class OutlineRow(object):
    def __init__(self,project,title,page,children=[]):
        self._title=title
        self._page=page
        self._project=project
        self.children=children
        self.parent=None
        for ch in self.children:
            ch.parent=self

    def output(self,indent):
        S='%s("%s" "#%s"' % (indent,self._title,self._page.title)
        if not self.children:
            return S+")\n"
        for obj in self.children:
            S+=obj.output(indent=indent+"    ")
        S+="%s)\n" % indent
        return S

    @property
    def page(self):
        return self._page

    @property
    def path(self): 
        if self._page is None: return None
        return self._page.path

    def _get_title(self): return self._title
    def _set_title(self,value):
        self._title=value
        self._project._save()

    title=property(_get_title,_set_title)

    def update(self,title,page):
        self._title=title
        self._page=page
        self._project._save()        

    def __serialize__(self):
        children=[]
        for ch in self.children:
            children.append(ch.__serialize__())
        return (self._title,self._page.path,children)

    def count_children(self): return len(self.children)
    
    def get_row(self,ind):
        if ind>= len(self.children): return None
        return self.children[ind]

    def index_row(self,obj):
        return self.children.index(obj)

    def insert_row(self,ind,child):
        self.children.insert(ind,child)
        child.parent=self

    def append_row(self,child):
        self.children.append(child)
        child.parent=self

    def insert_rows(self,ind,count):
        for n in range(count):
            self.insert_row(ind,OutlineRow(self._project,"",None,[]))
        self._project._save()

    def create_row(self,title,page):
        self.append_row(OutlineRow(self._project,title,page,[]))
        self._project._save()

    def remove_rows(self,ind,count):
        for n in range(count):
            self.children.pop(ind)
        self._project._save()

    def move_up(self,obj):
        ind=self.children.index(obj)
        if ind==0: return
        self.children.pop(ind)
        self.children.insert(ind-1,obj)
        self._project._save()

    def move_down(self,obj):
        ind=self.children.index(obj)
        if ind==len(self.children)-1: return
        self.children.pop(ind)
        self.children.insert(ind+1,obj)
        self._project._save()

    def move_right(self,obj):
        ind=self.children.index(obj)
        if ind==0: return
        self.children.pop(ind)
        self.children[ind-1].append_row(obj)
        self._project._save()

class Outline(object):
    def __init__(self,project,serialized=[]):
        self._project=project
        self.rows=self.deserialize(serialized)

    def __serialize__(self):
        if not self.rows: return []
        S=[]
        for r in self.rows:
            S.append(r.__serialize__())
        return S

    def deserialize(self,serialized):
        S=[]
        for ser in serialized:
            title=ser[0]
            page=self._project.book.pages_by_path[ser[1]]
            children=self.deserialize(ser[2])
            S.append(OutlineRow(self._project,title,page,children))
        return S

    def output(self):
        S="(bookmarks\n"
        for obj in self.rows:
            S+=obj.output(indent="    ")
        S+=")\n"
        return S

    def write_on(self,fname):
        S=self.output()
        print(S)
        with open(fname,'w') as fd:
            fd.write(S)

    def get_row(self,parent,ind):
        if parent is not None:
            return parent.get_row(ind)
        if ind >= len(self.rows): return None
        return self.rows[ind]

    def index_row(self,obj):
        if obj.parent is None: 
            return self.rows.index(obj)
        return obj.parent.index_row(obj)

    def count_children(self,obj):
        if obj is None: return len(self.rows)
        return obj.count_children()

    def insert_rows(self,parent,ind,count):
        if parent is not None:
            return parent.insert_rows(ind,count)
        for n in range(count):
            self.rows.insert(ind,OutlineRow(self._project,"",None,[]))
        self._project._save()

    def remove_rows(self,parent,ind,count):
        if parent is not None:
            return parent.remove_rows(ind,count)
        for n in range(count):
            self.rows.pop(ind)
        self._project._save()
        
    def create_row(self,parent,title,page):
        if parent is not None: return parent.create_row(title,page)
        self.rows.append(OutlineRow(self._project,title,page,[]))
        self._project._save()

    def update_row(self,obj,title,page):
        obj.update(title,page)

    def move_up(self,obj): 
        if obj.parent is not None:
            obj.parent.move_up(obj)
            return
        ind=self.rows.index(obj)
        if ind==0: return
        self.rows.pop(ind)
        self.rows.insert(ind-1,obj)
        self._project._save()

    def move_down(self,obj): 
        if obj.parent is not None:
            obj.parent.move_down(obj)
            return
        ind=self.rows.index(obj)
        if ind==len(self.rows)-1: return
        self.rows.pop(ind)
        self.rows.insert(ind+1,obj)
        self._project._save()

    def move_left(self,obj): pass

    def move_right(self,obj): 
        if obj.parent is not None:
            obj.parent.move_right(obj)
            return
        ind=self.rows.index(obj)
        if ind==0: return
        self.rows.pop(ind)
        self.rows[ind-1].append_row(obj)
        self._project._save()

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

        def add_metadata(self,key,value):
            self._list.append( Project.ProjectMetadataItem(self._project,key,value) )
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
        return os.path.dirname(self._fpath)
                
    def __init__(self,fpath):
        abstracts.SerializedDict.__init__(self,fpath)
        self.book=None
        if "Metadata" in self:
            if type(self["Metadata"]) in [  collections.OrderedDict, dict ]:
                self["Metadata"]=list(self["Metadata"].items())
            self["Metadata"]=self.ProjectMetadata(self,self["Metadata"])
        else:
            self["Metadata"]=self.ProjectMetadata(self)

        if ("Tiff directory" not in self) and ("Tif directory" in self):
            self["Tiff directory"]=self["Tif directory"]

        self._setup_options()
        self._setup_book()

        if "Outline" in self:
            self["Outline"]=Outline(self,self["Outline"])
        else:
            self["Outline"]=Outline(self)

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
        self["Outline"]=Outline(self)
        self._save()
        self._setup_options()
        self._setup_book()

    # def _setup_annotations(self):
    #     if "Background" not in self: self["Background"]="#ffffff"
    #     if "Zoom" not in self: self["Zoom"]="d100"
    #     if "Mode" not in self: self["Mode"]="color"
    #     if "Horizontal Align" not in self: self["Horizontal Align"]="center"
    #     if "Vertical Align" not in self: self["Vertical Align"]="center"

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
        #self["Metadata"].write_on(f_metadata)

        f_bookmarks=os.path.join(self["Tiff directory"],"bookmarks")
        #self["Outline"].write_on(f_bookmarks)

        file_list=[
            (f_metadata,"metadata",""),
            (f_bookmarks,"bookmarks",""),
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

    def update_page_numbers(self):
        for p in self.book.pages:
            p.title=self["Pages"][p.path]

    def apply_ocr(self):
        max_threads=self["Max threads"]
        ocr=libocr.Tesseract(self["Ocr Options"]['tesseract_options'])
        print('Performing optical character recognition.')
        self.book.apply_ocr(ocr,max_threads)
        
    def djvubind(self,djvu_name):
        if len(self.book.pages) == 0: return
        f_metadata=os.path.join(self["Tiff directory"],"metadata")
        self["Metadata"].write_on(f_metadata)
        f_bookmarks=os.path.join(self["Tiff directory"],"bookmarks")
        self["Outline"].write_on(f_bookmarks)

        print('Binding %d file(s).' % len(self.book.pages))
        enc_opts=self["Encoding Options"].copy()
        enc_opts["ocr"]=(self["Ocr Options"]["ocr_engine"] != "no ocr")
        print('Encoding all information to %s.' % djvu_name)
        enc = libencode.Encoder(enc_opts)
        enc.enc_book(self.book, djvu_name)
