# -*- coding: utf-8 -*-


import PySide2.QtWidgets as qtwidgets
import PySide2.QtCore as qtcore
import PySide2.QtGui as qtgui
import PySide2.QtNetwork as qtnetwork

import os.path
import signal
import socket

class HButtonBar(qtwidgets.QWidget):
    layout=qtwidgets.QHBoxLayout

    def __init__(self,def_list):
        qtwidgets.QWidget.__init__(self)
        b_layout=self.layout()
        for label,callback in def_list:
            button = qtwidgets.QPushButton(label)
            button.clicked.connect(callback)
            b_layout.addWidget(button)
        self.setLayout(b_layout)

class VButtonBar(HButtonBar):
    layout=qtwidgets.QVBoxLayout
        

class OpenFileWidget(qtwidgets.QWidget):

    def __init__(self):
        qtwidgets.QWidget.__init__(self)
        self.field=qtwidgets.QLineEdit()
        button=qtwidgets.QPushButton("Browse...")
        layout = qtwidgets.QHBoxLayout()
        layout.addWidget(self.field,stretch=1)
        layout.addWidget(button,stretch=0)
        self.setLayout(layout)
        button.pressed.connect(self._open)

    def text(self):
        return self.field.text()

    def setText(self,txt):
        self.field.setText(txt)

    def blockTextSignals(self,flag):
        self.field.blockSignals(flag)

    def _open(self): 
        dialog = qtwidgets.QFileDialog(self)
        dialog.setFileMode(qtwidgets.QFileDialog.ExistingFile)
        dialog.setAcceptMode(qtwidgets.QFileDialog.AcceptOpen)
        old=self.field.text()
        if not old:
            dialog.setDirectory(".")
        else:
            dialog.setDirectory(os.path.dirname(old))
            dialog.selectFile(old)
        if dialog.exec_():
            fnames = dialog.selectedFiles()
            self.field.setText(fnames[0])

class SaveFileWidget(OpenFileWidget): 
    def _open(self): 
        dialog = qtwidgets.QFileDialog(self)
        dialog.setFileMode(qtwidgets.QFileDialog.AnyFile)
        dialog.setAcceptMode(qtwidgets.QFileDialog.AcceptSave)
        old=self.field.text()
        if not old:
            dialog.setDirectory(".")
        else:
            dialog.setDirectory(os.path.dirname(old))
            dialog.selectFile(old)
        if dialog.exec_():
            fnames = dialog.selectedFiles()
            self.field.setText(fnames[0])

class OpenDirWidget(OpenFileWidget): 

    def _open(self): 
        dialog = qtwidgets.QFileDialog(self)
        dialog.setFileMode(qtwidgets.QFileDialog.Directory)
        dialog.setAcceptMode(qtwidgets.QFileDialog.AcceptOpen)
        dialog.setOptions(qtwidgets.QFileDialog.ShowDirsOnly)
        old=self.field.text()
        if not old:
            dialog.setDirectory(".")
        else:
            dialog.setDirectory(os.path.dirname(old))
            dialog.selectFile(old)
        if dialog.exec_():
            fnames = dialog.selectedFiles()
            self.field.setText(fnames[0])

class SignalWakeupHandler(qtnetwork.QAbstractSocket):

    def __init__(self, parent=None):
        super().__init__(qtnetwork.QAbstractSocket.UdpSocket, parent)
        self.old_fd = None
        # Create a socket pair
        self.wsock, self.rsock = socket.socketpair(type=socket.SOCK_DGRAM)
        # Let Qt listen on the one end
        self.setSocketDescriptor(self.rsock.fileno())
        # And let Python write on the other end
        self.wsock.setblocking(False)
        self.old_fd = signal.set_wakeup_fd(self.wsock.fileno())
        # First Python code executed gets any exception from
        # the signal handler, so add a dummy handler first
        self.readyRead.connect(lambda : None)
        # Second handler does the real handling
        self.readyRead.connect(self._readSignal)

    def __del__(self):
        # Restore any old handler on deletion
        if self.old_fd is not None and signal and signal.set_wakeup_fd:
            signal.set_wakeup_fd(self.old_fd)

    def _readSignal(self):
        # Read the written byte.
        # Note: readyRead is blocked from occuring again until readData()
        # was called, so call it, even if you don't need the value.
        data = self.readData(1)
        # Emit a Qt signal for convenience
        self.signalReceived.emit(data[0])

    signalReceived = qtcore.Signal(int)

class FormDialog(qtwidgets.QDialog):
    def _font(self,style,size):
        font_db = qtgui.QFontDatabase()
        family="Raleway"
        font=font_db.font(family,style,size)
        return font

    def __init__(self,window,title,form,*args,**kwargs):
        super().__init__(window,*args,**kwargs)
        self.setWindowTitle(title)
        flags = qtwidgets.QDialogButtonBox.Ok | qtwidgets.QDialogButtonBox.Cancel

        button_box = qtwidgets.QDialogButtonBox(flags)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        for w in button_box.findChildren(qtwidgets.QWidget):
            w.setFont(self._font("Medium",10))

        f_widget=qtwidgets.QWidget()
        self._form=form
        f_widget.setLayout(self._form)
        for w in f_widget.findChildren(qtwidgets.QWidget):
            w.setFont(self._font("Medium",10))

        v_layout = qtwidgets.QVBoxLayout()
        v_layout.addWidget(f_widget)
        v_layout.addWidget(button_box)
        self.setLayout(v_layout)

    def get_data(self):
        print("dialog")
        ret=self.exec_()
        data=list(self._form.get_data())
        data.append(ret==self.Accepted)
        return tuple(data)

class AwesomeToolBar(qtwidgets.QToolBar):
    def _font(self,family,style,size):
        font_db = qtgui.QFontDatabase()
        family="Font Awesome 5 "+family
        font=font_db.font(family,style,size)
        return font

    def __init__(self,parent): #icon,tooltip,size=8,style="Solid",family="Free"):
        qtwidgets.QToolBar.__init__(self,parent)

    def addAction(self,icon,tooltip,size=8,style="Solid",family="Free"):
        action=qtwidgets.QToolBar.addAction(self,icon)
        action.setToolTip(tooltip)
        action.setFont(self._font(family,style,size))
        return action

class AddRootProxyModel(qtcore.QIdentityProxyModel): 
    root="==root=="

    def data(self, index, role):
        parent=index.parent()
        if parent.isValid():
            return qtcore.QIdentityProxyModel.data(self,index,role)
        row=index.row()
        if row==0: 
            if role not in [ qtcore.Qt.DisplayRole, qtcore.Qt.EditRole]: 
                ret=qtcore.QIdentityProxyModel.data(self,index,role)
                print(role,ret)
                return ret
            return "----"
        sibling=index.sibling(row-1,index.column())
        return qtcore.QIdentityProxyModel.data(self,sibling,role)

    def flags(self,index):
        if not index.parent().isValid():
            if index.row()==0: 
                return qtcore.Qt.ItemIsEnabled | qtcore.Qt.ItemIsSelectable | qtcore.Qt.ItemNeverHasChildren
        return qtcore.Qt.ItemIsEnabled | qtcore.Qt.ItemIsSelectable
        
    def rowCount(self,index):
        if index.isValid():
            if index.parent().isValid():
                return qtcore.QIdentityProxyModel.rowCount(self,index)
            if index.row()==0: return 0
            return qtcore.QIdentityProxyModel.rowCount(self,index)
        return 1+qtcore.QIdentityProxyModel.rowCount(self)

    def index(self,row,column,parent=qtcore.QModelIndex()):
        if parent.isValid(): 
            return qtcore.QIdentityProxyModel.index(self,row,column,parent)
        if row==0:
            ret=self.createIndex(0,column,self.root)
            return ret
        old=qtcore.QIdentityProxyModel.index(self,row-1,column,parent)
        return self.createIndex(row,column,old.internalPointer())

    def parent(self,index):
        if not index.isValid(): return qtcore.QModelIndex()
        obj=index.internalPointer()
        if obj==self.root: return qtcore.QModelIndex()
        return qtcore.QIdentityProxyModel.parent(self,index)

    def mapToSource(self,proxyIndex):
        new_index=qtcore.QIdentityProxyModel.mapToSource(self,proxyIndex)
        if new_index.internalPointer()==self.root:
            return qtcore.QModelIndex()
        return new_index

    def mapFromSource(self,sourceIndex):
        new_index=qtcore.QIdentityProxyModel.mapFromSource(self,sourceIndex)
        if new_index.parent().isValid(): return new_index
        return self.createIndex(1+new_index.row(),new_index.column(),
                                new_index.internalPointer())

    # def mapFromSource(self, sourceIndex):
    #     if not sourceIndex.isValid(): return qtcore.QModelIndex()
    #     parent=sourceIndex.parent()
    #     if parent.isValid():
    #         return self.createIndex(sourceIndex.row(),
    #                                 sourceIndex.column(),
    #                                 sourceIndex.internalPointer())
    #     return self.createIndex(1+sourceIndex.row(),
    #                             sourceIndex.column(),
    #                             sourceIndex.internalPointer())

    # def mapToSource(self, proxyIndex):
    #     if not proxyIndex.isValid(): return qtcore.QModelIndex()
    #     parent=proxyIndex.parent()
    #     if parent.isValid:
    #         return qtcore.QIdentityProxyModel.mapToSource(self,proxyIndex)
    #     obj=proxyIndex.internalPointer()
    #     if obj==self.root: return qtcore.QModelIndex()
    #     return self.sourceModel().createIndex(proxyIndex.row()-1,
    #                                           proxyIndex.column(),
    #                                           obj)
        
