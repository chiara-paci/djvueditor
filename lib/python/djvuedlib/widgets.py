# -*- coding: utf-8 -*-


import PySide2.QtWidgets as qtwidgets
import PySide2.QtCore as qtcore
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
