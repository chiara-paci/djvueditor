import PySide2.QtWidgets as qtwidgets
import PySide2.QtCore as qtcore
import PySide2.QtGui as qtgui
import os.path

from .application import DjvuEditorGui

def setup(base_dir):
    font_dir=os.path.join(base_dir,"share","fonts")
    raleway=os.path.join(font_dir,"Raleway-VariableFont_wght.ttf")
    print(raleway)
    #font_id = qtgui.QFontDatabase.addApplicationFont(raleway)
    #print("F",font_id)
