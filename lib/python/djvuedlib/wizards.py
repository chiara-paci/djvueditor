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
                                             "starting from a ScanTailor output directory."))
            label.setWordWrap(True)
            
            layout = qtwidgets.QVBoxLayout()
            layout.addWidget(label)
            self.setLayout(layout)

    class ScanTailorPage(qtwidgets.QWizardPage):
        def __init__(self):
            qtwidgets.QWizardPage.__init__(self)
            self.setTitle("ScanTailor file")
            self.setSubTitle("Specify a Scan Tailor file.")

            self.scantailor_fname = widgets.OpenFileWidget()
            self.errors= qtwidgets.QLabel()

            v_layout = qtwidgets.QVBoxLayout()
            layout = qtwidgets.QFormLayout()
            layout.addRow("scantailor_fname*", self.scantailor_fname)
            v_layout.addLayout(layout)
            v_layout.addWidget(self.errors)

            self.tree=qtwidgets.QTreeWidget()
            self.tree.setColumnCount(2)
            self.tree.setHeaderLabels(["tag","attributes"])

            v_layout.addWidget(self.tree)

            self.setLayout(v_layout)
            self.registerField("scantailor_fname*", self.scantailor_fname.field)
            self.scantailor_fname.field.textChanged.connect(self.completeChanged)

            self.xmltree=None

        def _set_tree(self,xmltree):
            self.xmltree=xmltree

            self.tree.clear()

            def traverse2(xmlelem,indent=""):
                for ch in xmlelem.findall("*"):
                    tag=ch.tag
                    attrs=", ".join(["%s=%s" % (k,ch.attrib[k]) for k in ch.attrib])
                    print(indent,tag,attrs)
                    traverse2(ch,indent=indent+"    ")

            def traverse(xmlelem,parent=None):
                if parent is None: 
                    parent=self.tree
                elem=qtwidgets.QTreeWidgetItem(parent)
                tag=xmlelem.tag
                attrs=", ".join(["%s=%s" % (k,xmlelem.attrib[k]) for k in xmlelem.attrib])
                elem.setText(0,tag)
                elem.setText(1,attrs)
                for ch in xmlelem.findall("*"):
                    traverse(ch,parent=elem)

            root=xmltree.getroot()
            traverse(root)

        def isComplete(self):
            fname=self.scantailor_fname.text()
            if not fname: return False
            if not os.path.isfile(fname): 
                self.errors.setText("%s is not a file" % fname)
                return False
            try:
                xmltree = ET.parse(fname)
            except ET.ParseError as e:
                self.errors.setText("%s is not an xml file" % fname)
                return False
            self.errors.setText("")

            self._set_tree(xmltree)
            return True
            
            #return qtwidgets.QWizardPage.isComplete(self)


    class ScanTailorDirPage(qtwidgets.QWizardPage):
        def __init__(self):
            qtwidgets.QWizardPage.__init__(self)
            self.setTitle("ScanTailor output dir")
            self.setSubTitle("Specify a Scan Tailor output directory.")

            self.scantailor_dir = widgets.OpenDirWidget()
            self.errors= qtwidgets.QLabel()

            v_layout = qtwidgets.QVBoxLayout()
            layout = qtwidgets.QFormLayout()
            layout.addRow("scantailor_dir*", self.scantailor_dir)
            v_layout.addLayout(layout)
            v_layout.addWidget(self.errors)

            self.setLayout(v_layout)
            self.registerField("scantailor_dir*", self.scantailor_dir.field)
            self.scantailor_dir.field.textChanged.connect(self.completeChanged)

    class MetadataPage(qtwidgets.QWizardPage):
        def __init__(self):
            qtwidgets.QWizardPage.__init__(self)
            self.setTitle("Metadata")
            self.setSubTitle("Only title is mandatory. You can set or change all values later.")
            layout = qtwidgets.QFormLayout()
            for label in [ "title*","author","date","subject" ]:
                widget=qtwidgets.QLineEdit()
                layout.addRow(label,widget)
                self.registerField(label,widget)
            self.setLayout(layout)

    class CreatePage(qtwidgets.QWizardPage):
        def __init__(self):
            qtwidgets.QWizardPage.__init__(self)
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
        self.scantailor_page=self.ScanTailorPage()
        self.addPage(self.scantailor_page)
        self.addPage(self.MetadataPage())
        self.addPage(self.CreatePage())
        self.setWindowTitle("New Project Wizard")
