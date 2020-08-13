# -*- coding: utf-8 -*-


import PySide2.QtWidgets as qtwidgets
import PySide2.QtCore as qtcore
import PySide2.QtNetwork as qtnetwork

import os.path
import signal
import socket

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

# QSS_TITLES="text-align:center;background-color:#6289b0"
# #QSS_TITLES="text-align:center;border:1px solid #89a3d4"

# class BaseDock(qtwidgets.QDockWidget):
#     def __init__(self,title,application):
#         self._app=application
#         qtwidgets.QDockWidget.__init__(self,title,self._app.window)

#         #self.setFont(self._app.main_font("Bold",14))
#         self.setStyleSheet(
#             "QDockWidget {color:white;} "
#             "QDockWidget::title {%s}" % QSS_TITLES
#         )
        
#         t_layout = qtwidgets.QHBoxLayout()


#         title_w=qtwidgets.QLabel(title)
#         title_w.setFont(self._app.main_font(style="SemiBold",size=10))
#         title_w.setSizePolicy(qtwidgets.QSizePolicy.Expanding,qtwidgets.QSizePolicy.Expanding)
#         title_w.setStyleSheet("color:white;%s" % QSS_TITLES)
#         title_w.setAlignment(qtcore.Qt.AlignHCenter)

#         toolbar=qtwidgets.QToolBar(parent=self)
#         toolbar.setSizePolicy(qtwidgets.QSizePolicy.Minimum,qtwidgets.QSizePolicy.Minimum)
#         toolbar.setStyleSheet("color:white;%s" % QSS_TITLES)


#         if self.isFloating():
#             self._pin_action=toolbar.addAction("")
#             self._pin_action.setFont(self._app.awesome_font(size=8))
#             self._pin_action.setToolTip("unlocked: lock")
#         else:
#             self._pin_action=toolbar.addAction("")
#             self._pin_action.setFont(self._app.awesome_font(size=8))
#             self._pin_action.setToolTip("locked: unlock")

#         self.status="pinned"

#         self._pin_action.triggered.connect(self._pin_action_triggered)

#         close_action=toolbar.addAction("")
#         close_action.setFont(self._app.awesome_font(size=8))
#         close_action.setToolTip("close")
#         close_action.triggered.connect(self._close_action_triggered)
        
#         t_layout.addWidget(title_w)
#         t_layout.addWidget(toolbar)

#         t_layout.setMargin(0)

#         bar_widget = qtwidgets.QWidget()
#         bar_widget.setLayout(t_layout)
#         bar_widget.setStyleSheet("padding:0;color:white;%s" % QSS_TITLES)

#         self.setTitleBarWidget(bar_widget)

#         self.topLevelChanged.connect(self._toplevel_changed)

#     def _toplevel_changed(self,floating):
#         if floating:
#             self._pin_action.setText("")
#             self._pin_action.setToolTip("unlocked: lock")
#             return
#         self._pin_action.setText("")
#         self._pin_action.setToolTip("locked: unlock")

#     def _pin_action_triggered(self): 
#         if self.isFloating():
#             self.setFloating(False)
#         else:
#             self.setFloating(True)
 
#     def _close_action_triggered(self): 
#         self.hide()

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
