# -*- coding: utf-8 -*-

import PySide2.QtWidgets as qtwidgets
import PySide2.QtCore as qtcore
import PySide2.QtNetwork as qtnetwork

import os.path
import collections

QSS_TITLES="text-align:center;background-color:#6289b0"
#QSS_TITLES="text-align:center;border:1px solid #89a3d4"

class BaseDock(qtwidgets.QDockWidget):
    def bar_layout(self,title):
        t_layout = qtwidgets.QHBoxLayout()

        title_w=qtwidgets.QLabel(title)
        title_w.setFont(self._app.main_font(style="SemiBold",size=10))
        title_w.setSizePolicy(qtwidgets.QSizePolicy.Expanding,qtwidgets.QSizePolicy.Expanding)
        title_w.setStyleSheet("color:white;%s" % QSS_TITLES)
        title_w.setAlignment(qtcore.Qt.AlignHCenter)

        toolbar=qtwidgets.QToolBar(parent=self)
        toolbar.setSizePolicy(qtwidgets.QSizePolicy.Minimum,qtwidgets.QSizePolicy.Minimum)
        toolbar.setStyleSheet("color:white;%s" % QSS_TITLES)

        if self.isFloating():
            self._pin_action=toolbar.addAction("")
            self._pin_action.setFont(self._app.awesome_font(size=8))
            self._pin_action.setToolTip("unlocked: lock")
        else:
            self._pin_action=toolbar.addAction("")
            self._pin_action.setFont(self._app.awesome_font(size=8))
            self._pin_action.setToolTip("locked: unlock")

        self.status="pinned"

        self._pin_action.triggered.connect(self._pin_action_triggered)

        close_action=toolbar.addAction("")
        close_action.setFont(self._app.awesome_font(size=8))
        close_action.setToolTip("close")
        close_action.triggered.connect(self._close_action_triggered)
        
        t_layout.addWidget(title_w)
        t_layout.addWidget(toolbar)

        t_layout.setMargin(0)

        return t_layout

    def __init__(self,title,application):
        self._app=application
        qtwidgets.QDockWidget.__init__(self,title,self._app.window)

        #self.setFont(self._app.main_font("Bold",14))
        self.setStyleSheet(
            "QDockWidget {color:white;} "
            "QDockWidget::title {%s}" % QSS_TITLES
        )

        t_layout=self.bar_layout(title)

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

class DockScanTailor(BaseDock):
    def __init__(self,application):
        BaseDock.__init__(self,"ScanTailor",application)

        v_layout = qtwidgets.QVBoxLayout()
        self.tif_dir=qtwidgets.QLabel()
        self.tif_dir.setStyleSheet("border-top:none;border-bottom:none")
        self.tif_dir.setFont(self._app.main_font(size=10))

        self.scantailor_fname=qtwidgets.QLabel()
        self.scantailor_fname.setStyleSheet("color:black;border-top:none;border-bottom:none")
        self.scantailor_fname.setFont(self._app.main_font(size=10))
        self.scantailor=qtwidgets.QTreeWidget()
        self.scantailor.setColumnCount(2)
        self.scantailor.setHeaderLabels(["",""])
        #self.scantailor.setHeaderHidden(True)
        self.scantailor.setStyleSheet("background:white; border: 1px solid #6289b0")

        v_layout.addWidget(self.tif_dir)
        v_layout.addWidget(self.scantailor_fname)
        v_layout.addWidget(self.scantailor)
        main_widget = qtwidgets.QWidget()
        main_widget.setLayout(v_layout)
        main_widget.setStyleSheet("padding: 0px")
        main_widget.setStyleSheet("border: 1px solid #6289b0")
        v_layout.setMargin(0)
        self.setWidget(main_widget)

    def set_project(self,project): 
        self.scantailor.clear()
        self.tif_dir.setText(project["Tif directory"])
        self.scantailor_fname.setText(project["Scantailor"]["name"])

        def traverse(children,parent):
            for child in children:
                elem=qtwidgets.QTreeWidgetItem(parent)
                tag=child["name"]
                attrs=", ".join(["%s=%s" % (k,child["attributes"][k]) for k in child["attributes"]])
                elem.setText(0,tag)
                elem.setText(1,attrs)
                if child["children"]:
                    traverse(child["children"],parent=elem)

        traverse(project["Scantailor"]["children"],self.scantailor)

class DockMetadata(BaseDock):

    class MetadataModel(qtcore.QAbstractTableModel):
        def __init__(self, *args, metadata=None, **kwargs):
            qtcore.QAbstractTableModel.__init__(self,*args, **kwargs)
            self.metadata = metadata or []

        def rowCount(self, index):
            return len(self.metadata)

        def columnCount(self,index):
            return 2

        def headerData(self,section,orientation,role):
            if role not in [ qtcore.Qt.DisplayRole, qtcore.Qt.EditRole ]: return None
            if orientation==qtcore.Qt.Orientation.Vertical:
                return section+1
            if section==0: return "key"
            return "value"

        def data(self, index, role):
            if role not in [ qtcore.Qt.DisplayRole, qtcore.Qt.EditRole ]: return None
            return self.metadata[index.row()][index.column()]

        def setData(self,index,value,role):
            if role not in [ qtcore.Qt.DisplayRole, qtcore.Qt.EditRole ]: return False
            self.metadata[index.row()][index.column()]=value
            self.dataChanged.emit(index, index)
            return True

        def delete_rows(self,indexes):
            rows=list(set([ idx.row() for idx in indexes ]))
            self.metadata.delete_items(rows)

        def add_row(self):
            self.metadata.add_empty_item()

        def flags(self,index):
            return qtcore.Qt.ItemIsEditable | qtcore.QAbstractTableModel.flags(self,index)

    def __init__(self,application):
        BaseDock.__init__(self,"Metadata",application)
        self.view=qtwidgets.QTableView() 
        self.model=self.MetadataModel()
        self.view.setModel(self.model)
        #self.view.verticalHeader().setVisible(False)
        self.view.setStyleSheet("background:white; border: 1px solid #6289b0")
        self.setWidget(self.view)

    def set_project(self,project): 
        self.model.metadata=project["Metadata"]
        self.model.layoutChanged.emit()

    def _add_action_triggered(self):
        self.model.add_row()
        self.model.layoutChanged.emit()
        
        print("add")

    def _delete_action_triggered(self):
        indexes = self.view.selectedIndexes()
        self.model.delete_rows(indexes)
        self.model.layoutChanged.emit()

        print("delete",indexes)

    def bar_layout(self,title):
        t_layout = BaseDock.bar_layout(self,title)

        toolbar=qtwidgets.QToolBar(parent=self)
        toolbar.setSizePolicy(qtwidgets.QSizePolicy.Minimum,qtwidgets.QSizePolicy.Minimum)
        toolbar.setStyleSheet("color:white;%s" % QSS_TITLES)

        add_action=toolbar.addAction("")
        add_action.setFont(self._app.awesome_font(size=8))
        add_action.setToolTip("add")
        add_action.triggered.connect(self._add_action_triggered)

        del_action=toolbar.addAction("")
        del_action.setFont(self._app.awesome_font(size=8))
        del_action.setToolTip("delete")
        del_action.triggered.connect(self._delete_action_triggered)
        
        t_layout.insertWidget(0,toolbar)

        return t_layout
