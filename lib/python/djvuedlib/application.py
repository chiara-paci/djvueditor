# -*- coding: utf-8 -*-

import os.path

import PySide2.QtWidgets as qtwidgets
import PySide2.QtCore as qtcore
import PySide2.QtGui as qtgui

from . import widgets
from . import wizards
from . import project as libproject
from . import actions
from . import docks
from . import mainwidget

import signal


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

    def __init__(self,base_dir,open_file=None):
        ## path
        qss_fname=os.path.join(base_dir,"etc","djvueditor.qss")
        self.djvubind_conf=os.path.join(base_dir,"etc","djvubind.conf")
        font_dir=os.path.join(base_dir,"share","fonts")

        ## init
        qtwidgets.QApplication.__init__(self,[])
        self.project=None

        for fname in self._font_files:
            fpath=os.path.join(font_dir,fname)
            font_id = qtgui.QFontDatabase.addApplicationFont(fpath)

        font_db = qtgui.QFontDatabase()
        font_families = font_db.families()
        #font_styles = font_db.styles('FontAwesome')
        #font_styles = font_db.styles('Raleway')
        #x=font_db.font("Font Awesome 5 Free",None,10)
        #print(x)

        self.window=qtwidgets.QMainWindow()
        #self.window.resize(1500,1000)
        self.window.resize(1500,700)
        self.window.setFont(self.main_font())
        self.window.setWindowTitle("DjvuEditor")

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
        ## Docks

        self.dock_metadata=docks.DockMetadata(self)
        self.window.addDockWidget(qtcore.Qt.LeftDockWidgetArea, self.dock_metadata)
        self.actions["open_dock_metadata"]=self.dock_metadata.toggleViewAction()
        menus["View"].append("open_dock_metadata")

        self.dock_configuration=docks.DockConfiguration(self)
        self.window.addDockWidget(qtcore.Qt.LeftDockWidgetArea, self.dock_configuration)
        self.actions["open_dock_configuration"]=self.dock_configuration.toggleViewAction()
        menus["View"].append("open_dock_configuration")

        self.window.tabifyDockWidget(self.dock_metadata,self.dock_configuration)

        self.setup_menu_bar(menus)

        ###############################
        ## Main

        self.main=mainwidget.ProjectWidget(self)
        self.window.setCentralWidget(self.main)
        
        ###############################
        ## Final setup

        self.emit_status("Ready")
        if open_file is not None:
            self.open_project(open_file)
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

    def open_project(self,project_fname):
        self.project=libproject.Project(project_fname)
        self.window.setWindowTitle("DjvuEditor: "+project_fname)
        self.refresh_project()

    def refresh_project(self):
        self.dock_metadata.set_project(self.project)
        self.dock_configuration.set_project(self.project)
        self.main.set_project(self.project)

    def new_project(self,project_fname,metadata,tiff_dir):
        self.project=libproject.Project(project_fname)
        self.project.new_project(metadata,tiff_dir)
        self.window.setWindowTitle("DjvuEditor: "+project_fname)
        self.refresh_project()

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

    def emit_status(self,msg):
        self.window.statusBar().showMessage(msg)

    def exec_(self):
        self.window.show()
        qtwidgets.QApplication.exec_()
