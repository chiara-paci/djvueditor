# -*- coding: utf-8 -*-

import os.path
import xml.etree.ElementTree as ET

import PySide2.QtWidgets as qtwidgets

from . import widgets

class NewProjectWizard(qtwidgets.QWizard):
    class IntroPage(qtwidgets.QWizardPage):
        def __init__(self):
            qtwidgets.QWizardPage.__init__(self)
            self.setTitle("New project")
            label = qtwidgets.QLabel(self.tr("This wizard will generate a skeleton for a new project, " \
                                             "starting from a directory of tiff (for example, a Scantailor output directory))."))
            label.setWordWrap(True)
            
            layout = qtwidgets.QVBoxLayout()
            layout.addWidget(label)
            self.setLayout(layout)

    class TiffDirPage(qtwidgets.QWizardPage):
        def __init__(self,*args,**kwargs):
            qtwidgets.QWizardPage.__init__(self,*args,**kwargs)
            self.setTitle("Tiff directory")
            self.setSubTitle("Tiff directory.")
            self.tiff_dir = widgets.OpenDirWidget()
            layout = qtwidgets.QFormLayout()
            layout.addRow("tiff_dir*", self.tiff_dir)
            self.setLayout(layout)
            self.registerField("tiff_dir*", self.tiff_dir.field)
            self.tiff_dir.field.textChanged.connect(self.completeChanged)

    class MetadataPage(qtwidgets.QWizardPage):
        def __init__(self,*args,**kwargs):
            qtwidgets.QWizardPage.__init__(self,*args,**kwargs)
            self.setTitle("Metadata")
            self.setSubTitle("Only title is mandatory. You can set or change all values later.")

            layout = qtwidgets.QFormLayout()
            for label in [ "title*","author","date","subject" ]:
                widget=qtwidgets.QLineEdit()
                layout.addRow(label,widget)
                self.registerField(label,widget)
            self.setLayout(layout)

    class CreatePage(qtwidgets.QWizardPage):
        def __init__(self,*args,**kwargs):
            qtwidgets.QWizardPage.__init__(self,*args,**kwargs)
            self.setTitle("Create Project")
            self.setSubTitle("Specify a project file.")

            self.project_fname = widgets.SaveFileWidget()
            self.errors= qtwidgets.QLabel()

            v_layout = qtwidgets.QVBoxLayout()
            layout = qtwidgets.QFormLayout()
            layout.addRow("project_fname*", self.project_fname)
            v_layout.addLayout(layout)
            v_layout.addWidget(self.errors)

            self.setLayout(v_layout)
            self.registerField("project_fname*", self.project_fname.field)
            self.project_fname.field.textChanged.connect(self.completeChanged)

    def __init__(self, parent):
        qtwidgets.QWizard.__init__(self, parent)
        self.setOption(qtwidgets.QWizard.IndependentPages)
        self.addPage(self.IntroPage())
        self.addPage(self.TiffDirPage(self))
        self.addPage(self.MetadataPage(self))
        self.addPage(self.CreatePage(self))
        self.setWindowTitle("New Project Wizard")
