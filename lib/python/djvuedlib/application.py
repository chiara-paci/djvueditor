# -*- coding: utf-8 -*-

import os.path
import xml.etree.ElementTree as ET

import PySide2.QtWidgets as qtwidgets
import PySide2.QtCore as qtcore
import PySide2.QtGui as qtgui

from . import widgets
from . import wizards
from . import project as libproject
from . import actions
from . import docks

from . import djvubindwrapper

import signal

class ProjectWidget(qtwidgets.QWidget):

    def __init__(self,app):
        self._app=app
        qtwidgets.QWidget.__init__(self)
        v_layout = qtwidgets.QVBoxLayout()
        button = qtwidgets.QPushButton("Create Djvu")
        button.clicked.connect(self._app._djvubind)
        v_layout.addWidget(button)
        self.cover_front=widgets.OpenFileWidget()
        self.cover_back=widgets.OpenFileWidget()
        self.max_threads=qtwidgets.QSpinBox()
        self.max_threads.setMinimum(1)
        f_layout=qtwidgets.QFormLayout()
        f_layout.addRow("cover_front", self.cover_front)
        f_layout.addRow("cover_back", self.cover_back)
        f_layout.addRow("max_threads", self.max_threads)
        f_widget=qtwidgets.QWidget(self)
        f_widget.setLayout(f_layout)
        v_layout.addWidget(f_widget)
        self.setLayout(v_layout)

        self.cover_front.field.textChanged.connect(self._cover_front_changed)
        self.cover_back.field.textChanged.connect(self._cover_back_changed)
        self.max_threads.valueChanged.connect(self._max_threads_changed)

    def _cover_front_changed(self):
        val=self.cover_front.text()
        self._app.project["Cover front"]=val

    def _cover_back_changed(self):
        val=self.cover_back.text()
        self._app.project["Cover back"]=val

    def _max_threads_changed(self):
        val=self.max_threads.value()
        self._app.project["Max threads"]=val

    def set_project(self,project): 
        self._project=project

        self.cover_front.field.textChanged.disconnect(self._cover_front_changed)
        if "Cover front" in self._app.project:
            self.cover_front.setText(self._app.project["Cover front"])
        self.cover_front.field.textChanged.connect(self._cover_front_changed)

        self.cover_back.field.textChanged.disconnect(self._cover_back_changed)
        if "Cover back" in self._app.project:
            self.cover_back.setText(self._app.project["Cover back"])
        self.cover_back.field.textChanged.connect(self._cover_back_changed)

        self.max_threads.valueChanged.disconnect(self._max_threads_changed)
        if "Max threads" in self._app.project:
            self.max_threads.setValue(self._app.project["Max threads"])
        self.max_threads.valueChanged.connect(self._max_threads_changed)


class DjvuEditorGui(qtwidgets.QApplication):
    _font_files=[
        "Raleway-VariableFont_wght.ttf",
        'Font Awesome 5 Brands-Regular-400.otf',
        'Font Awesome 5 Free-Regular-400.otf',
        'Font Awesome 5 Free-Solid-900.otf',
    ]

    _font_family="Raleway"

    def main_font(self,style="Medium",size=12):
        font_db = qtgui.QFontDatabase()
        return font_db.font(self._font_family,style,size)

    def awesome_font(self,family="Free",style="Solid",size=12):
        font_db = qtgui.QFontDatabase()
        family="Font Awesome 5 "+family
        font=font_db.font(family,style,size)
        print(font)
        return font
            
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

        self.dock_scantailor=docks.DockScanTailor(self)
        self.window.addDockWidget(qtcore.Qt.LeftDockWidgetArea, self.dock_scantailor)
        self.actions["open_dock_scantailor"]=self.dock_scantailor.toggleViewAction()
        menus["View"].append("open_dock_scantailor")

        self.setup_menu_bar(menus)

        ###############################
        ## Main

        self.main=ProjectWidget(self)
        self.window.setCentralWidget(self.main)
        
        ###############################
        ## Final setup

        self.emit_status("Ready")
        if open_file is not None:
            self.open_project(open_file)
        widgets.SignalWakeupHandler(self)
        signal.signal(signal.SIGINT, lambda sig,_: self.quit())

    def _djvubind(self): 
        dialog = qtwidgets.QFileDialog(self.window)
        dialog.setFileMode(qtwidgets.QFileDialog.AnyFile)
        dialog.setAcceptMode(qtwidgets.QFileDialog.AcceptSave)
        dialog.setDirectory(".")
        if dialog.exec_():
            fnames = dialog.selectedFiles()
            djvu_name = fnames[0]
            if not djvu_name.endswith(".djvu"):
                djvu_name+=".djvu"

            print("djvubind",self.project["Tif directory"],djvu_name)

            f_metadata=os.path.join(self.project["Tif directory"],
                                    "metadata")

            #self.project["Metadata"].write_on(f_metadata)

            covers={}
            if "Cover back" in self.project:
                covers["cover_back"]=self.project["Cover back"]
            if "Cover front" in self.project:
                covers["cover_front"]=self.project["Cover front"]

            max_threads=self.project["Max threads"]

            djvubindwrapper.djvubind_main(
                self.djvubind_conf,
                self.project.file_list(),
                #self.project["Tif directory"],
                djvu_name,max_threads
            )

    def open_project(self,project_fname):
        self.project=libproject.Project(project_fname)
        self.window.setWindowTitle("DjvuEditor: "+project_fname)
        self.dock_scantailor.set_project(self.project)
        self.dock_metadata.set_project(self.project)
        self.main.set_project(self.project)

    def new_project(self,project_fname,metadata,scantailor_fname,xmltree):
        self.project=libproject.Project(project_fname)
        self.project.new_project(metadata,scantailor_fname,xmltree)
        self.window.setWindowTitle("DjvuEditor: "+project_fname)
        self.dock_metadata.set_project(self.project)
        self.dock_scantailor.set_project(self.project)
        self.main.set_project(self.project)

    def _set_stylesheet(self,qss_fname):
        with open(qss_fname,'r') as fd:
            txt=fd.read()
        print(txt)
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
