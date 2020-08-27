# -*- coding: utf-8 -*-

import PySide2.QtWidgets as qtwidgets
import PySide2.QtCore as qtcore
import PySide2.QtGui as qtgui
import PySide2.QtNetwork as qtnetwork

import os.path
import collections
import re

from . import abstracts

class ProjectTableModel(qtcore.QAbstractTableModel):
    _section=""
    _columns=[]
    
    def __init__(self, *args, **kwargs):
        qtcore.QAbstractTableModel.__init__(self,*args, **kwargs)
        self._project=None

    def columnCount(self,index):
        return len(self._columns)

    def rowCount(self, index):
        if self._project is None: return 0
        return len(self._project[self._section])

    def headerData(self,section,orientation,role):
        if role not in [ qtcore.Qt.DisplayRole, qtcore.Qt.EditRole ]: 
            return qtcore.QAbstractItemModel.headerData(self,section,orientation,role)
        if orientation==qtcore.Qt.Orientation.Vertical:
            return qtcore.QAbstractItemModel.headerData(self,section,orientation,role)
        return self._columns[section]

    def set_project(self,project): 
        self._project=project
        self.layoutChanged.emit()

    def flags(self,index):
        return qtcore.Qt.ItemIsEditable | qtcore.QAbstractTableModel.flags(self,index)

class MetadataModel(ProjectTableModel):
    _section="Metadata"
    _columns=["key","value"]

    def data(self, index, role):
        if self._project is None: return None
        if role not in [ qtcore.Qt.DisplayRole, qtcore.Qt.EditRole ]: return None
        return self._project["Metadata"][index.row()][index.column()]

    def setData(self,index,value,role):
        if role not in [ qtcore.Qt.DisplayRole, qtcore.Qt.EditRole ]: return False
        self._project["Metadata"][index.row()][index.column()]=value
        self.dataChanged.emit(index, index)
        return True

    def delete_rows(self,indexes):
        rows=list(set([ idx.row() for idx in indexes ]))
        self._project["Metadata"].delete_items(rows)
        self.layoutChanged.emit()

    def add_row(self):
        self._project["Metadata"].add_empty_item()
        self.layoutChanged.emit()

    def add_metadata(self,key,value):
        self._project["Metadata"].add_metadata(key,value)
        self.layoutChanged.emit()

class PageNumberingModel(ProjectTableModel):
    pageNumberChanged = qtcore.Signal()
    _section="Pages"
    _columns=["page","title"]

    def data(self, index, role):
        if self._project is None: return None
        if role not in [ qtcore.Qt.DisplayRole, qtcore.Qt.EditRole ]: return None
        keys=list(self._project["Pages"].keys())
        col=index.column()
        if col==0: return os.path.basename(keys[index.row()])
        return self._project["Pages"][keys[index.row()]]

    def setData(self,index,value,role):
        if role not in [ qtcore.Qt.DisplayRole, qtcore.Qt.EditRole ]: return False
        col=index.column()
        if col==0: return False
        keys=list(self._project["Pages"].keys())
        col=index.column()
        self._set_page_num(keys[index.row()],value)
        self.dataChanged.emit(index, index)
        self.pageNumberChanged.emit()
        return True

    def flags(self,index):
        col=index.column()
        if col==0: return qtcore.QAbstractTableModel.flags(self,index)
        return ProjectTableModel.flags(self,index)

    def _set_page_num(self,path,value):
        self._project["Pages"][path]=value
        self._project.book.pages_by_path[path].title=value

    def number_from(self,index,start,numtype): 
        keys=list(self._project["Pages"].keys())
        if numtype=="roman upper":
            sequence=abstracts.SequenceRoman(start,lower=False)
        elif numtype=="roman lower":
            sequence=abstracts.SequenceRoman(start)
        else:
            sequence=abstracts.SequenceStr(start)
        row=index.row()
        while row < len(self._project["Pages"]):
            seq=sequence()
            key=keys[row]
            self._set_page_num(key,seq)
            #self._project["Pages"][key]=seq
            row+=1
        self.dataChanged.emit(index, index)
        self.pageNumberChanged.emit()

    def number(self,indexes,start,numtype):
        keys=list(self._project["Pages"].keys())
        if numtype=="roman upper":
            sequence=abstracts.SequenceRoman(start,lower=False)
        elif numtype=="roman lower":
            sequence=abstracts.SequenceRoman(start)
        else:
            sequence=abstracts.SequenceStr(start)
        for index in indexes:
            seq=sequence()
            row=index.row()
            key=keys[row]
            self._set_page_num(key,seq)
            #self._project["Pages"][key]=seq
        self.dataChanged.emit(index, index)
        self.pageNumberChanged.emit()

class BaseItemModel(qtcore.QAbstractItemModel): 
    _columns=[]

    def __init__(self,*args,**kwargs):

        qtcore.QAbstractItemModel.__init__(self,*args,**kwargs)

        self.move_up=self.MoveAction(self,self._move_up)
        self.move_down=self.MoveAction(self,self._move_down)
        self.move_left=self.MoveAction(self,self._move_left)
        self.move_right=self.MoveAction(self,self._move_right)

    def _move_up(self,obj): return
    def _move_down(self,obj): return
    def _move_left(self,obj): return
    def _move_right(self,obj): return

    def columnCount(self,index):
        return len(self._columns)

    def headerData(self,section,orientation,role):
        if role not in [ qtcore.Qt.DisplayRole, qtcore.Qt.EditRole ]: 
            return qtcore.QAbstractItemModel.headerData(self,section,orientation,role)
        if orientation==qtcore.Qt.Orientation.Vertical:
            return qtcore.QAbstractItemModel.headerData(self,section,orientation,role)
        return self._columns[section]

    def _is_empty(self): return True

    def _count_children(self,obj): return 0
    def rowCount(self, index = qtcore.QModelIndex()):
        if self._is_empty(): return 0
        if index.isValid():
            obj = index.internalPointer()
        else:
            obj=None
        c=self._count_children(obj)
        return c

    def _get_child(self,parent_obj,ind): return None
    def index(self,row,column,parent=qtcore.QModelIndex()): 
        if self._is_empty(): return qtcore.QModelIndex()
        if not parent.isValid(): 
            parent_obj=None
        else:
            parent_obj = parent.internalPointer()
        obj=self._get_child(parent_obj,row)
        if not obj: return qtcore.QModelIndex()
        return self.createIndex(row, column, obj)

    def _child_parent(self,child): return child.parent
    def _index(self,obj): return 0
    def parent(self, index):
        if self._is_empty(): return qtcore.QModelIndex()
        if not index.isValid():
            return qtcore.QModelIndex()
        child=index.internalPointer()
        if self._child_parent(child) is None: return qtcore.QModelIndex()
        row=self._index(child.parent)
        return self.createIndex(row,0,child.parent)

    def _insert_multi(self,parent_obj,ind,count): pass
    def insertRows(self,row,count,parent=qtcore.QModelIndex()):
        if self._is_empty(): return False
        self.beginInsertRows(parent,row,row+count-1)
        if not parent.isValid():
            parent_obj=None
        else:
            parent_obj=parent.internalPointer()
        self._insert_multi(parent_obj,row,count)
        self.endInsertRows()            
        self.layoutChanged.emit()
        return True

    def _remove_multi(self,parent_obj,ind,count): pass
    def removeRows(self,row,count,parent=qtcore.QModelIndex()):
        if self._is_empty(): return False
        self.beginRemoveRows(parent,row,row+count-1)
        if not parent.isValid():
            parent_obj=None
        else:
            parent_obj=parent.internalPointer()
        self._remove_multi(parent_obj,row,count)
        self.endRemoveRows()            
        self.layoutChanged.emit()
        return True

    def _create(self,parent_obj,*args,**kwargs): pass
    def _update(self,obj,*args,**kwargs): pass
    def _duplicate(self,obj): pass

    def duplicateRow(self,index):
        if self._is_empty(): return False
        if not index.isValid(): return False
        obj=index.internalPointer()
        self._duplicate(obj)
        self.layoutChanged.emit()
        return True

    def createRow(self,index,*args,**kwargs):
        if self._is_empty(): return False
        if index.isValid():
            obj=index.internalPointer()
        else:
            obj=None
        self._create(obj,*args,**kwargs)
        self.dataChanged.emit(index,index)
        self.layoutChanged.emit()
        return True

    def updateRow(self,index,*args,**kwargs):
        if self._is_empty(): return False
        if not index.isValid(): return False
        obj=index.internalPointer()
        self._update(obj,*args,**kwargs)
        self.layoutChanged.emit()
        return True

    class MoveAction(object):
        def __init__(self,model,callback):
            self._model=model
            self._callback=callback

        def __call__(self,index):
            if self._model._is_empty(): return 
            obj=index.internalPointer()
            self._callback(obj)
            self._model.layoutChanged.emit()
            row=self._model._index(obj)
            return self._model.createIndex(row,0,obj)

    class ChangeAction(object):
        def __init__(self,model,callback):
            self._model=model
            self._callback=callback
            
        def __call__(self,index,*args,**kwargs):
            if self._model._is_empty(): return 
            obj=index.internalPointer()
            self._callback(obj,*args,**kwargs)
            self._model.dataChanged.emit(index, index)
            self._model.layoutChanged.emit()

            
class OutlineModel(BaseItemModel):
    _columns=["toc_line","page"]

    def __init__(self,*args,**kwargs):
        BaseItemModel.__init__(self,*args,**kwargs)
        self._project=None

    def _is_empty(self): return self._project is None
    def _count_children(self,obj):  return self._project["Outline"].count_children(obj)
    def _get_child(self,parent_obj,ind): return self._project["Outline"].get_row(parent_obj,ind)
    # def _child_parent(self,child): return child.parent
    def _index(self,obj): return self._project["Outline"].index_row(obj)
    def _insert_multi(self,parent_obj,ind,count): self._project["Outline"].insert_rows(parent_obj,ind,count)
    def _remove_multi(self,parent_obj,ind,count): self._project["Outline"].remove_rows(parent_obj,ind,count)
    def _move_up(self,obj): self._project["Outline"].move_up(obj)
    def _move_down(self,obj): self._project["Outline"].move_down(obj)
    def _move_left(self,obj): self._project["Outline"].move_left(obj)
    def _move_right(self,obj): self._project["Outline"].move_right(obj)

    def set_project(self,project):
        self._project=project
        self.layoutChanged.emit()

    def data(self, index, role):
        if not index.isValid(): return None
        if role not in [ qtcore.Qt.DisplayRole, qtcore.Qt.EditRole]: 
            return None
        obj=index.internalPointer()
        col=index.column()
        if col==1: return str(obj.page)
        return obj.title

    def flags(self,index):
        col=index.column()
        if col==0:
            return qtcore.Qt.ItemIsEditable | BaseItemModel.flags(self,index)
        return BaseItemModel.flags(self,index)

    def setData(self,index,value,role):
        if role not in [ qtcore.Qt.DisplayRole, qtcore.Qt.EditRole ]: return False
        col=index.column()
        if col==1: return False
        obj=index.internalPointer()
        obj.title=value
        self.dataChanged.emit(index, index)
        return True

    def _create(self,parent_obj,*args,**kwargs):
        self._project["Outline"].create_row(parent_obj,*args,**kwargs)

    def create_row(self,index,title,page):
        return self.createRow(index,title,page)

    def _update(self,obj,*args,**kwargs):
        self._project["Outline"].update_row(obj,*args,**kwargs)

    def update_row(self,index,title,page):
        return self.updateRow(index,title,page)

class OcrModel(BaseItemModel):
    _columns=["level","xmin","ymin","xmax","ymax","content"]

    def __init__(self,page,*args,**kwargs):
        BaseItemModel.__init__(self,*args,**kwargs)
        self._page=page
        self.merge_above_rule=self.ChangeAction(self,self._merge_above_rule)
        self.merge_below_rule=self.ChangeAction(self,self._merge_below_rule)
        self.upper_rule=self.ChangeAction(self,self._upper_rule)
        self.lower_rule=self.ChangeAction(self,self._lower_rule)
        self.capitalize_rule=self.ChangeAction(self,self._capitalize_rule)
        self.accentize_rule=self.ChangeAction(self,self._accentize_rule)
        self.fix_apostrophes_rule=self.ChangeAction(self,self._fix_apostrophes_rule)
        self.split_rule=self.ChangeAction(self,self._split_rule)
        self.shift_down_rule=self.ChangeAction(self,self._shift_down_rule)
        self.shift_up_rule=self.ChangeAction(self,self._shift_up_rule)
        self.shift_left_rule=self.ChangeAction(self,self._shift_left_rule)
        self.shift_right_rule=self.ChangeAction(self,self._shift_right_rule)
        self.crop_to_children=self.ChangeAction(self,self._crop_to_children)

    def _is_empty(self): return self._page is None
    def _count_children(self,obj): return self._page.count_children_text_rule(obj)
    def _get_child(self,parent_obj,ind): return self._page.get_text_rule(parent_obj,ind)
    # def _child_parent(self,child): return child.parent
    def _index(self,obj): return self._page.index_text_rule(obj)
    def _insert_multi(self,parent_obj,ind,count): self._page.insert_text_rules(parent_obj,ind,count)
    def _remove_multi(self,parent_obj,ind,count): self._page.remove_text_rules(parent_obj,ind,count)
    def _move_up(self,obj): self._page.move_up(obj)        
    def _move_down(self,obj): self._page.move_down(obj)        
    def _move_left(self,obj): self._page.move_left(obj)        
    def _move_right(self,obj): self._page.move_right(obj)        

    def headerData(self,section,orientation,role):
        if role == qtcore.Qt.TextAlignmentRole:
            if section in [1,2,3,4]:
                return qtcore.Qt.AlignRight
            return None
        return BaseItemModel.headerData(self,section,orientation,role)

    def data(self, index, role):
        if not index.isValid(): return None
        if role not in [ qtcore.Qt.DisplayRole, qtcore.Qt.EditRole, 
                         qtcore.Qt.TextAlignmentRole ]: 
            return None
        obj=index.internalPointer()
        col=index.column()
        if role == qtcore.Qt.TextAlignmentRole:
            if col in [1,2,3,4]:
                return qtcore.Qt.AlignRight
            return None
        if col==0: return obj.level
        if col==1: return obj.xmin
        if col==2: return obj.ymin
        if col==3: return obj.xmax
        if col==4: return obj.ymax
        return obj.content

    def flags(self,index):
        col=index.column()
        if col!=5:
            return qtcore.Qt.ItemIsEditable | BaseItemModel.flags(self,index)
        obj=index.internalPointer()
        if obj.children:
            return BaseItemModel.flags(self,index)
        return qtcore.Qt.ItemIsEditable | BaseItemModel.flags(self,index)

    def setData(self,index,value,role):
        if role not in [ qtcore.Qt.DisplayRole, qtcore.Qt.EditRole ]: return False
        col=index.column()
        obj=index.internalPointer()
        if col==0:
            obj.level=value
            self.dataChanged.emit(index, index)
            return True
        if col==5:
            if obj.children: return False
            obj.text=value
            self.dataChanged.emit(index, index)
            return True
        try:
            if col==1: obj.xmin=int(value)
            if col==2: obj.ymin=int(value)
            if col==3: obj.xmax=int(value)
            if col==4: obj.ymax=int(value)
        except ValueError as e:
            return False
        self.dataChanged.emit(index, index)
        return True

    def _duplicate(self,obj):
        self._page.duplicate_text_rule(obj)

    def _create(self,parent_obj,*args,**kwargs):
        self._page.create_text_rule(parent_obj,*args,**kwargs)

    def create_rule(self,parent,level,xmin,ymin,xmax,ymax,text):
        return self.createRow(parent,level,xmin,ymin,xmax,ymax,text)
        
    def _split_rule(self,obj,splitted): self._page.split_rule(obj,splitted)
    def _shift_down_rule(self,obj,val): self._page.shift_down_text_rule(obj,val)
    def _shift_up_rule(self,obj,val): self._page.shift_up_text_rule(obj,val)
    def _shift_left_rule(self,obj,val): self._page.shift_left_text_rule(obj,val)
    def _shift_right_rule(self,obj,val): self._page.shift_right_text_rule(obj,val)
    def _merge_above_rule(self,obj): self._page.merge_above_text_rule(obj)
    def _merge_below_rule(self,obj): self._page.merge_below_text_rule(obj)

    def _crop_to_children(self,obj): obj.crop_to_children()

    def _upper_rule(self,obj):
        if obj.children: return
        obj.text=obj.text.upper()

    def _lower_rule(self,obj):
        if obj.children: return
        obj.text=obj.text.lower()

    def _capitalize_rule(self,obj):
        if obj.children: return
        obj.text=obj.text.capitalize()

    def _accentize_rule(self,obj):
        if obj.children: return
        obj.text=self._accentize(obj.text)

    def _accentize(self,txt):
        commas=""
        if txt[-1] in ".,;:?!'"+'"':
            commas=txt[-1]
            txt=txt[:-1]
        if txt[-1] not in "aeiouèéAEIOUÈÉ": return txt+commas
        if txt[-1]=="a": return txt[:-1]+"à"+commas
        if txt[-1]=="i": return txt[:-1]+"ì"+commas
        if txt[-1]=="o": return txt[:-1]+"ò"+commas
        if txt[-1]=="u": return txt[:-1]+"ù"+commas
        if txt[-1]=="è": return txt[:-1]+"é"+commas
        if txt[-1]=="é": return txt[:-1]+"è"+commas
        if txt[-1]=="A": return txt[:-1]+"À"+commas
        if txt[-1]=="I": return txt[:-1]+"Ì"+commas
        if txt[-1]=="O": return txt[:-1]+"Ò"+commas
        if txt[-1]=="U": return txt[:-1]+"Ù"+commas
        if txt[-1]=="È": return txt[:-1]+"É"+commas
        if txt[-1]=="É": return txt[:-1]+"È"+commas
        if txt=="e": return "è"+commas
        if txt=="E": return "È"+commas
        if txt.lower()=="ce":
            if txt[-1]=="e": return txt[:-1]+"'è"+commas
            if txt[-1]=="E": return txt[:-1]+"'È"+commas
        if txt.lower().endswith("che"):
            if txt[-1]=="e": return txt[:-1]+"é"+commas
            if txt[-1]=="E": return txt[:-1]+"É"+commas
        if txt[-1]=="e": return txt[:-1]+"è"+commas
        if txt[-1]=="E": return txt[:-1]+"È"+commas

    def _fix_apostrophes_rule(self,obj):
        if obj.children: return
        obj.text=self._fix_apostrophes(obj.text)

    def _fix_apostrophes(self,txt):
        txt=txt.replace("’","'")
        txt=txt.replace("|'","l'")
        txt=re.sub(r"'+","'",txt)
        return txt
    

