from . import abstracts
import collections
import os.path


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
                
    def __init__(self,fpath):
        abstracts.SerializedDict.__init__(self,fpath)
        if type(self["Metadata"]) in [  collections.OrderedDict, dict ]:
            self["Metadata"]=list(self["Metadata"].items())
            self._save()
        self["Metadata"]=self.ProjectMetadata(self,self["Metadata"])

    def new_project(self,metadata,scantailor_fname,xmltree):
        self.clear()
        def traverse(xmlelem,parent):
            elem={
                "name": xmlelem.tag,
                "attributes": xmlelem.attrib,
                "children": []
            }
            parent["children"].append(elem)
            for ch in xmlelem.findall("*"):
                traverse(ch,elem)

        self["Metadata"]=self.ProjectMetadata(self,metadata)
        root=xmltree.getroot()
        self["Tif directory"]=root.attrib["outputDirectory"]
        self["Scantailor"]={
            "name": scantailor_fname,
            "children": []
        }
        traverse(root,self["Scantailor"])
        self._save()

    @property
    def base_dir(self):
        return os.path.dirname(self._path)

    def file_list(self):
        f_metadata=os.path.join(self["Tif directory"],"metadata")
        self["Metadata"].write_on(f_metadata)

        f_bookmarks=os.path.join(self["Tif directory"],"bookmarks")
        # da aggiungere <------

        file_list=[
            (f_metadata,"metadata",""),
            # (f_bookmarks,"bookmarks",""), <--- da aggiungere
        ]
        if "Cover back" in self:
            file_list.append( (self["Cover back"], "cover_back", "" ) )
        if "Cover front" in self:
            file_list.append( (self["Cover front"], "cover_front", "" ) )
        
        cback=self["Cover back"] if "Cover back" in self else ""
        cfront=self["Cover front"] if "Cover front" in self else ""
        page_list=[]
        with os.scandir(self["Tif directory"]) as it:
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
        title=1
        for p in page_list:
            file_list.append( (p,"page",str(title)) )
            title+=1

        return file_list
