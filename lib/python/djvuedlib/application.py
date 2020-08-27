# -*- coding: utf-8 -*-

import os.path
import collections
import datetime

import PySide2.QtWidgets as qtwidgets
import PySide2.QtCore as qtcore
import PySide2.QtGui as qtgui

from . import widgets
from . import project as libproject
from . import actions
from . import models
from . import docks
from . import mainwidget

import signal

class DjvuEditorBatch(object):
    def __init__(self,base_dir,project_fname):
        self._project=libproject.Project(project_fname)

    def save_djvu(self,djvu_name):
        if not djvu_name.endswith(".djvu"):
            djvu_name+=".djvu"
        djvu_name=os.path.abspath(djvu_name)
        self._project.djvubind(djvu_name)

class DjvuEditorGui(qtwidgets.QApplication):
    _font_files=[
        "Raleway-VariableFont_wght.ttf",
        'Font Awesome 5 Brands-Regular-400.otf',
        'Font Awesome 5 Free-Regular-400.otf',
        'Font Awesome 5 Free-Solid-900.otf',
    ]

    _font_family="Raleway"
            
    def quit(self):
        print("")
        self.window.close()

    def __init__(self,base_dir,open_file=None,page_num=None):
        qtwidgets.QApplication.__init__(self,[])
        self.project=None

        font_dir=os.path.join(base_dir,"share","fonts")
        for fname in self._font_files:
            fpath=os.path.join(font_dir,fname)
            font_id = qtgui.QFontDatabase.addApplicationFont(fpath)

        self.window=qtwidgets.QMainWindow()
        self.window.resize(1500,700)
        self.window.setFont(self.main_font())
        self.window.setWindowTitle("DjvuEditor")

        qss_fname=os.path.join(base_dir,"etc","djvueditor.qss")
        self._set_stylesheet(qss_fname) 

        ##############################
        ## Actions

        self.actions={ 
            "open": actions.ActionOpen(self),
            "new": actions.ActionNew(self),
            "quit": actions.ActionQuit(self)
        }

        menus={
            "File": [ "new", "open", "-", "quit" ],
            "View": [ ],
        }

        ##############################
        ## Models

        self.models={}

        self.models["page_numbering"]=models.PageNumberingModel()
        self.models["outline"]=models.OutlineModel()
        self.models["metadata"]=models.MetadataModel()

        ##############################
        ## Docks

        self.docks=collections.OrderedDict()

        for label,cls in [ 
                ("configuration",docks.DockConfiguration),
                ("metadata",docks.DockMetadata),
                ("page_numbering",docks.DockPageNumbering),
                ("outline",docks.DockOutline) ]:
            dock=cls(self)
            self.window.addDockWidget(qtcore.Qt.LeftDockWidgetArea,dock)
            self.actions["open_dock_%s" % label]=dock.toggleViewAction()
            menus["View"].append("open_dock_%s" % label)
            self.docks[label]=dock

        self.docks["outline"].set_model(self.models["outline"])
        self.docks["metadata"].set_model(self.models["metadata"])
        self.docks["page_numbering"].set_model(self.models["page_numbering"])
        
        keys=list(self.docks.keys())
        for i in range(len(keys)-1):
            self.window.tabifyDockWidget(self.docks[keys[i]],self.docks[keys[i+1]])

        ###############################
        ## Main

        self.setup_menu_bar(menus)
        self.main=mainwidget.ProjectWidget(self)
        self.window.setCentralWidget(self.main)
        
        ###############################
        ## Final setup

        self.emit_status("Ready")
        if open_file is not None:
            self.open_project(open_file,page_num=page_num)
        widgets.SignalWakeupHandler(self)
        signal.signal(signal.SIGINT, lambda sig,_: self.quit())

    def main_font(self,style="Medium",size=12):
        font_db = qtgui.QFontDatabase()
        return font_db.font(self._font_family,style,size)

    def awesome_font(self,family="Free",style="Solid",size=12):
        font_db = qtgui.QFontDatabase()
        family="Font Awesome 5 "+family
        font=font_db.font(family,style,size)
        return font

    def open_project(self,project_fname,page_num=None):
        self.project=libproject.Project(project_fname)
        self.window.setWindowTitle("DjvuEditor: "+project_fname)
        self.refresh_project()
        if page_num is None: return
        self.main.goto_page(page_num)
        

    def new_project(self,project_fname,metadata,tiff_dir):
        self.project=libproject.Project(project_fname)
        self.project.new_project(metadata,tiff_dir)
        self.window.setWindowTitle("DjvuEditor: "+project_fname)
        self.refresh_project()

    def refresh_project(self):
        for k in self.models:
            self.models[k].set_project(self.project)
        for k in self.docks:
            self.docks[k].set_project(self.project)
        self.main.set_project(self.project)

    def _set_stylesheet(self,qss_fname):
        with open(qss_fname,'r') as fd:
            txt=fd.read()
        self.window.setStyleSheet(txt)

    def setup_menu_bar(self,menus):
        mbar=self.window.menuBar()
        mbar.setFont(self.main_font(size=10))
        for menu_label in menus:
            menu=qtwidgets.QMenu(menu_label)
            menu.setFont(self.main_font(size=10))
            menu.setStyleSheet("background-color:#e5edfb;")
            for action in menus[menu_label]:
                if action=="-":
                    menu.addAction(actions.Separator(self))
                else:
                    menu.addAction(self.actions[action])
            mbar.addMenu(menu)

    def emit_status(self,msg,*args,**kwargs):
        msg="[%s] %s" % (str(datetime.datetime.today()),msg)
        self.window.statusBar().showMessage(msg)

    def exec_(self):
        self.window.show()
        qtwidgets.QApplication.exec_()
