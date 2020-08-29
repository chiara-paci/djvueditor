# -*- coding: utf-8 -*-

import PySide2.QtWidgets as qtwidgets
import PySide2.QtCore as qtcore
import PySide2.QtGui as qtgui
import PySide2.QtNetwork as qtnetwork

import os.path
import collections

from . import widgets,abstracts,models,actions

QSS_TITLES="text-align:center;background-color:#6289b0"
#QSS_TITLES="text-align:center;border:1px solid #89a3d4"

class BaseDock(qtwidgets.QDockWidget):
    dock_title=""

    class DockToolBar(widgets.AwesomeToolBar):
        def __init__(self,parent):
            widgets.AwesomeToolBar.__init__(self,parent)
            self.setSizePolicy(qtwidgets.QSizePolicy.Minimum,qtwidgets.QSizePolicy.Minimum)
            self.setStyleSheet("color:white;%s" % QSS_TITLES)

    def bar_layout(self):
        t_layout = qtwidgets.QHBoxLayout()

        title_w=qtwidgets.QLabel(self.dock_title)
        title_w.setFont(self._app.main_font(style="SemiBold",size=10))
        title_w.setSizePolicy(qtwidgets.QSizePolicy.Expanding,
                              qtwidgets.QSizePolicy.Expanding)
        title_w.setStyleSheet("color:white;%s" % QSS_TITLES)
        title_w.setAlignment(qtcore.Qt.AlignHCenter)

        toolbar=self.DockToolBar(parent=self)

        if self.isFloating():
            self._pin_action=toolbar.addAction("","unlocked: lock")
        else:
            self._pin_action=toolbar.addAction("","locked: unlock")

        self.status="pinned"

        self._pin_action.triggered.connect(self._pin_action_triggered)

        close_action=toolbar.addAction("","close")
        close_action.triggered.connect(self._close_action_triggered)
        
        t_layout.addWidget(title_w)
        t_layout.addWidget(toolbar)

        t_layout.setMargin(0)

        return t_layout

    def __init__(self,application):
        self._app=application
        qtwidgets.QDockWidget.__init__(self,self.dock_title,self._app.window)
        self.setFont(self._app.main_font(size=10))

        self.setStyleSheet(
            "QDockWidget {color:white;} "
            "QDockWidget::title {%s}" % QSS_TITLES
        )

        t_layout=self.bar_layout()

        bar_widget = qtwidgets.QWidget()
        bar_widget.setLayout(t_layout)
        bar_widget.setStyleSheet("padding:0;color:white;%s" % QSS_TITLES)

        self.setTitleBarWidget(bar_widget)

        self.topLevelChanged.connect(self._toplevel_changed)

    def _toplevel_changed(self,floating):
        if floating:
            self._pin_action.setText("")
            self._pin_action.setToolTip("unlocked: lock")
            return
        self._pin_action.setText("")
        self._pin_action.setToolTip("locked: unlock")

    def _pin_action_triggered(self): 
        if self.isFloating():
            self.setFloating(False)
        else:
            self.setFloating(True)
 
    def _close_action_triggered(self): 
        self.hide()

    def set_project(self,project): pass

class DockProjectTable(BaseDock):
    def __init__(self,application):
        BaseDock.__init__(self,application)
        self.view=qtwidgets.QTableView() 
        self.view.setStyleSheet("background:white; border: 1px solid #6289b0")
        self.view.setFont(self._app.main_font(size=10))
        self.view.horizontalHeader().setFont(self._app.main_font(size=10))
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.verticalHeader().setFont(self._app.main_font(size=10))
        #self.view.setSelectionMode(self.view.SingleSelection)
        self.view.setSelectionBehavior(self.view.SelectRows)
        self.setWidget(self.view)

    def set_model(self,model):
        self.model=model
        self.view.setModel(model)
    

class DockPageNumbering(DockProjectTable):
    pageNumberChanged = qtcore.Signal()

    class NumberForm(qtwidgets.QFormLayout): 
        def __init__(self):
            qtwidgets.QFormLayout.__init__(self)
            self.start=qtwidgets.QSpinBox()
            self.start.setValue(1)
            self.numtype=qtwidgets.QComboBox()
            for v in ["arabic","roman lower","roman upper"]:
                self.numtype.addItem(v)

            self.addRow("start", self.start)
            self.addRow("type", self.numtype)

        def get_data(self):
            start=self.start.value()
            numtype=self.numtype.currentText()
            return start,numtype

    dock_title="Page Numbering"

    def _number_from_triggered(self):
        indexes = self.view.selectedIndexes()
        dialog=widgets.FormDialog(self.window(),"Number from",self.NumberForm())
        start,numtype,ok=dialog.get_data()
        if not ok: return
        self.model.number_from(indexes[0],start,numtype)

    def _number_triggered(self):
        indexes = self.view.selectedIndexes()
        dialog=widgets.FormDialog(self.window(),"Number selected",self.NumberForm())
        start,numtype,ok=dialog.get_data()
        if not ok: return
        self.model.number(indexes,start,numtype)

    def bar_layout(self):
        t_layout = BaseDock.bar_layout(self)
        toolbar=self.DockToolBar(parent=self)
        action=toolbar.addAction( "","number from selected page")
        action.triggered.connect(self._number_from_triggered)
        action=toolbar.addAction("","number selected pages")
        action.triggered.connect(self._number_triggered)
        t_layout.insertWidget(0,toolbar)
        return t_layout

class DockMetadata(DockProjectTable):

    class MetadataForm(qtwidgets.QFormLayout): 
        def __init__(self):
            qtwidgets.QFormLayout.__init__(self)
            self.key=qtwidgets.QLineEdit()
            self.value=qtwidgets.QLineEdit()
            self.addRow("key", self.key)
            self.addRow("value", self.value)

        def get_data(self):
            key=self.key.text()
            value=self.value.text()
            return key,value

    dock_title="Metadata"

    def _add_action_triggered(self):
        dialog=widgets.FormDialog(self.window(),"Metadata",self.MetadataForm())
        key,value,ok=dialog.get_data()
        if not ok: return
        self.model.add_metadata(key,value)

    def _delete_action_triggered(self):
        indexes = self.view.selectedIndexes()
        self.model.delete_rows(indexes)

    def bar_layout(self):
        t_layout = BaseDock.bar_layout(self)
        toolbar=self.DockToolBar(parent=self)
        add_action=toolbar.addAction("","add")
        add_action.triggered.connect(self._add_action_triggered)
        del_action=toolbar.addAction("","delete")
        del_action.triggered.connect(self._delete_action_triggered)
        t_layout.insertWidget(0,toolbar)
        return t_layout

class DockConfiguration(BaseDock):

    class ConfSpinBox(qtwidgets.QSpinBox):
        def __init__(self,application,label):
            qtwidgets.QSpinBox.__init__(self)
            self._app=application
            self._label=label
            self.valueChanged.connect(self._changed)

        def _changed(self):
            val=self.value()
            if self._app.project is not None:
                self._app.project[self._label]=val

        def set_project(self,project):
            if self._label not in project: return
            self.valueChanged.disconnect(self._changed)
            self.setValue(project[self._label])
            self.valueChanged.connect(self._changed)

    class ConfEncodingLineEdit(qtwidgets.QLineEdit):
        section="Encoding Options"

        def __init__(self,application,label):
            qtwidgets.QLineEdit.__init__(self)
            self._app=application
            self._label=label
            self.textChanged.connect(self._changed)
        
        def _changed(self):
            val=self.text()
            if self._app.project is not None:
                self._app.project[self.section][self._label]=val

        def set_project(self,project):
            if self._label not in project[self.section]: return
            self.textChanged.disconnect(self._changed)
            self.setText(project[self.section][self._label])
            self.textChanged.connect(self._changed)

    class ConfEncodingComboBox(qtwidgets.QComboBox):
        section="Encoding Options"

        def __init__(self,application,label,values):
            qtwidgets.QComboBox.__init__(self)
            self.setEditable(False)
            self.setInsertPolicy(self.NoInsert)
            self._app=application
            self._label=label
            
            for v in values: self.addItem(v)

            self.currentTextChanged.connect(self._changed)
        
        def _changed(self):
            val=self.currentText()
            if self._app.project is not None:
                self._app.project[self.section][self._label]=val

        def set_project(self,project):
            if self._label not in project[self.section]: return
            self.currentTextChanged.disconnect(self._changed)
            self.setCurrentText(project[self.section][self._label])
            self.currentTextChanged.connect(self._changed)

    class ConfOcrLineEdit(ConfEncodingLineEdit):
        section="Ocr Options"

    class ConfOcrComboBox(ConfEncodingComboBox):
        section="Ocr Options"

    dock_title="Configuration"

    def __init__(self,application):
        self._app=application
        BaseDock.__init__(self,application)
        f_layout=qtwidgets.QFormLayout()

        self.setFont(self._app.main_font(size=10))

        self.widgets=[]

        def add_row(lab,w):
            f_layout.addRow(lab,w)
            self.widgets.append(widget)
            w.setFont(self._app.main_font(size=10))
            f_layout.labelForField(w).setFont(self._app.main_font(size=10))
            
        
        widget=self.ConfSpinBox(application,"Max threads")
        widget.setMinimum(1)
        add_row("Max threads",widget)

        f_layout.addRow(qtwidgets.QLabel(""))

        widget=self.ConfEncodingComboBox(application,"bitonal_encoder",
                                        ["cjb2","minidjvu"])
        add_row("Bitonal encoder",widget)

        widget=self.ConfEncodingComboBox(application,"color_encoder",
                                        ["csepdjvu","c44","cpaldjvu"])
        add_row("Color encoder",widget)

        for plabel in [ "c44_options",
                        "cjb2_options",
                        "cpaldjvu_options",
                        "csepdjvu_options",
                        "minidjvu_options" ]:
            wlabel=plabel.capitalize().replace("_"," ")
            widget=self.ConfEncodingLineEdit(application,plabel)
            add_row(wlabel,widget)
 
        f_layout.addRow(qtwidgets.QLabel(""))
        widget=self.ConfOcrComboBox(application,"ocr_engine",
                                    ["tesseract","cuneiform","no ocr"])
        add_row("OCR engine",widget)

        for plabel in [ "tesseract_options",
                        "cuneiform_options" ]:
            wlabel=plabel.capitalize().replace("_"," ")
            widget=self.ConfOcrLineEdit(application,plabel)
            add_row(wlabel,widget)
        
        f_widget=qtwidgets.QWidget(self)
        f_widget.setLayout(f_layout)

        self.setWidget(f_widget)

    def set_project(self,project): 
        for widget in self.widgets:
            widget.set_project(project)

class OutlineWidget(qtwidgets.QTreeView):

    class RowDataForm(qtwidgets.QFormLayout):
        def __init__(self,pages,title="",page=None):
            qtwidgets.QFormLayout.__init__(self)
            self.page=qtwidgets.QComboBox()
            for p in pages:
                self.page.addItem(str(p),p)
            if page is not None:
                ind=pages.index(page)
                self.page.setCurrentIndex(ind)

            self.title=qtwidgets.QLineEdit()
            if title: self.title.setText(title)
            self.addRow("title", self.title)
            self.addRow("page", self.page)

        def get_data(self):
            title=self.title.text()
            page=self.page.currentData()
            return title,page

    def __init__(self):
        qtwidgets.QTreeView.__init__(self)
        self._project=None
        self._model=None
        self.setAlternatingRowColors(True)
        self.expandAll()
        self.setSelectionMode(self.SingleSelection)
        self.setSelectionBehavior(self.SelectRows)
        self.setContextMenuPolicy(qtcore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.row_menu_open)

        self.shortcuts = {
            "delete_row": qtwidgets.QShortcut(qtgui.QKeySequence.Delete, self),
            "move_right": qtwidgets.QShortcut(qtgui.QKeySequence(qtcore.Qt.Key_Tab),self),
            "create_row": qtwidgets.QShortcut(qtgui.QKeySequence(qtcore.Qt.Key_A),self),
            "edit_row": qtwidgets.QShortcut(qtgui.QKeySequence(qtcore.Qt.Key_E),self),
        }
        for k in self.shortcuts:
            self.shortcuts[k].setContext(qtcore.Qt.WidgetWithChildrenShortcut)
        self.shortcuts["delete_row"].activated.connect(self.delete_row)
        self.shortcuts["move_right"].activated.connect(self.move_right)
        self.shortcuts["create_row"].activated.connect(self.create_row)
        self.shortcuts["edit_row"].activated.connect(self.edit_row)

    def setModel(self,model):
        self._model=model
        qtwidgets.QTreeView.setModel(self,model)

    def set_project(self,project):
        self._project=project
        #self._model.set_project(project)

    def refresh(self):
        self._model.layoutChanged.emit()

    def delete_row(self,index=None):
        if index is None:
            index=self.selectionModel().currentIndex()
        if not index.isValid(): return
        self._model.removeRow(index.row(),parent=self._model.parent(index))

    def create_row(self,index=None):
        print("CR1")
        if index is None:
            index=self.selectionModel().currentIndex()
        dialog=widgets.FormDialog(self.window(),"Create row",self.RowDataForm(self._project.pages))
        title,page,ok=dialog.get_data()
        if not ok: return
        self._model.create_row(index,title,page)

    def edit_row(self,index=None):
        if index is None:
            index=self.selectionModel().currentIndex()
        if not index.isValid(): return
        obj=index.internalPointer()
        dialog=widgets.FormDialog(self.window(),"Create row",self.RowDataForm(self._project.pages,title=obj.title,page=obj.page))
        title,page,ok=dialog.get_data()
        if not ok: return
        self._model.update_row(index,title,page)

    def move_up(self,index=None):
        if index is None:
            index=self.selectionModel().currentIndex()
        if not index.isValid(): return
        new_index=self._model.move_up(index)
        self.selectionModel().select(new_index,qtcore.QItemSelectionModel.Clear | qtcore.QItemSelectionModel.SelectCurrent | qtcore.QItemSelectionModel.Rows)

    def move_down(self,index=None):
        if index is None:
            index=self.selectionModel().currentIndex()
        if not index.isValid(): return
        new_index=self._model.move_down(index)
        self.selectionModel().select(new_index,qtcore.QItemSelectionModel.Clear | qtcore.QItemSelectionModel.SelectCurrent | qtcore.QItemSelectionModel.Rows)

    def move_left(self,index=None):
        if index is None:
            index=self.selectionModel().currentIndex()
        if not index.isValid(): return
        new_index=self._model.move_left(index)
        self.selectionModel().select(new_index,qtcore.QItemSelectionModel.Clear | qtcore.QItemSelectionModel.SelectCurrent | qtcore.QItemSelectionModel.Rows)

    def move_right(self,index=None):
        if index is None:
            index=self.selectionModel().currentIndex()
        if not index.isValid(): return
        new_index=self._model.move_right(index)
        self.selectionModel().select(new_index,qtcore.QItemSelectionModel.Clear | qtcore.QItemSelectionModel.SelectCurrent | qtcore.QItemSelectionModel.Rows)

    def row_menu_open(self, point):
        # Infos about the node selected.
        index = self.indexAt(point)
        if not index.isValid(): return
        menu=qtwidgets.QMenu(self)

        maction=menu.addAction("add")
        maction.triggered.connect(lambda: self.create_row(index=index))

        maction.setShortcut(qtgui.QKeySequence(qtcore.Qt.Key_A))
        maction.setShortcutContext(qtcore.Qt.WindowShortcut)
        maction.setShortcutVisibleInContextMenu(True)

        maction=menu.addAction("edit")
        maction.triggered.connect(lambda: self.edit_row(index=index))
        maction.setShortcut(qtgui.QKeySequence(qtcore.Qt.Key_E))
        maction.setShortcutContext(qtcore.Qt.WindowShortcut)
        maction.setShortcutVisibleInContextMenu(True)

        menu.addSeparator()
        maction=menu.addAction("delete")
        maction.triggered.connect(lambda: self.delete_row(index=index))
        maction.setShortcut(qtgui.QKeySequence.Delete)
        maction.setShortcutContext(qtcore.Qt.WindowShortcut)
        maction.setShortcutVisibleInContextMenu(True)

        menu.exec_(self.mapToGlobal(point))

class DockOutline(BaseDock):
    dock_title="Outline"

    def __init__(self,application):
        BaseDock.__init__(self,application)
        self.view=OutlineWidget() 
        self.view.setStyleSheet("background:white; border: 1px solid #6289b0")
        self.view.setFont(self._app.main_font(size=10))
        self.setWidget(self.view)

    def set_model(self,model):
        self.view.setModel(model)

    def set_project(self,project): 
        self.view.set_project(project)

    def bar_layout(self):
        t_layout = BaseDock.bar_layout(self)
        
        toolbar=self.DockToolBar(parent=self)

        def add_action(icon,tooltip,callback):
            action=toolbar.addAction(icon,tooltip)
            action.triggered.connect(callback)
            return action
            
        add_action("","add",lambda checked: self.view.create_row())
        add_action("","edit",lambda checked: self.view.edit_row())
        add_action("","delete",lambda checked: self.view.delete_row())
        add_action("","move up",lambda checked: self.view.move_up())
        add_action("","move down",lambda checked: self.view.move_down())
        #add_action("","move left",lambda checked: self.view.move_left())
        add_action("","move right",lambda checked: self.view.move_right())


        t_layout.insertWidget(0,toolbar)

        return t_layout

