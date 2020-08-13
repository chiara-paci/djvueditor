# -*- coding: utf-8 -*-


import PySide2.QtWidgets as qtwidgets
import PySide2.QtCore as qtcore
import PySide2.QtGui as qtgui

from . import wizards

class Separator(qtwidgets.QAction):
    def __init__(self,application):
        self._app=application
        qtwidgets.QAction.__init__(self,"",self._app.window)
        self.setSeparator(True)

class ActionQuit(qtwidgets.QAction):
    def __init__(self,application):
        self._app=application
        qtwidgets.QAction.__init__(self,qtgui.QIcon(":/images/quit.png"),"Quit",self._app.window)
        self.setShortcuts(qtgui.QKeySequence.Quit)
        self.setStatusTip("Quit")
        self.setMenuRole(qtwidgets.QAction.QuitRole)
        self.triggered.connect(self._action)

    def _action(self):
        self._app.quit()

class ActionNew(qtwidgets.QAction):
    def __init__(self,application):
        self._app=application
        qtwidgets.QAction.__init__(self,qtgui.QIcon(":/images/new.png"),"New",self._app.window)
        self.setShortcuts(qtgui.QKeySequence.New)
        self.setStatusTip("New project")
        self.setMenuRole(qtwidgets.QAction.ApplicationSpecificRole)
        self.triggered.connect(self._action)

    def _action(self):
        wizard=wizards.NewProjectWizard(self._app.window)
        ret=wizard.exec_()
        print(ret)
        if not ret: return
        metadata=[]
        for label in [ "title","author","date","subject" ]:
            metadata.append( [label,wizard.field(label)] )
        scantailor_fname=wizard.field("scantailor_fname")
        project_fname=wizard.field("project_fname")

        self._app.new_project(project_fname,metadata,scantailor_fname,
                              wizard.scantailor_page.xmltree)

class ActionOpen(qtwidgets.QAction):
    def __init__(self,application):
        self._app=application
        qtwidgets.QAction.__init__(self,qtgui.QIcon(":/images/open.png"),"Open",
                                   self._app.window)
        self.setShortcuts(qtgui.QKeySequence.Open)
        self.setStatusTip("Open project")
        self.setMenuRole(qtwidgets.QAction.ApplicationSpecificRole)
        self.triggered.connect(self._action)

    def _action(self):
        dialog = qtwidgets.QFileDialog(self._app.window)
        dialog.setFileMode(qtwidgets.QFileDialog.AnyFile)
        dialog.setAcceptMode(qtwidgets.QFileDialog.AcceptOpen)
        if self._app.project is not None:
            dialog.setDirectory(self._app.project.base_dir)
        else:
            dialog.setDirectory(".")
        if not dialog.exec_(): return
        fnames = dialog.selectedFiles()
        self._app.open_project(fnames[0])
