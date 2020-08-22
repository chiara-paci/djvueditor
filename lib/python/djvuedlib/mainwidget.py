# -*- coding: utf-8 -*-

import os.path
import re

import PySide2.QtWidgets as qtwidgets
import PySide2.QtCore as qtcore
import PySide2.QtGui as qtgui

from . import widgets
from . import hiddentext

class ImageWidget(qtwidgets.QWidget):
    class LayerWidget(qtwidgets.QLabel):
        def __init__(self,size,margin_size):
            self._pixmap_size=size
            self._margin_size=margin_size
            pixmap=qtgui.QPixmap(self._pixmap_size+2*self._margin_size)
            pixmap.fill(qtcore.Qt.transparent)
            qtwidgets.QLabel.__init__(self)
            self.setPixmap(pixmap)
            self.setScaledContents(True)
            self.setSizePolicy(qtwidgets.QSizePolicy.Ignored,qtwidgets.QSizePolicy.Ignored)

    class BackgroundWidget(LayerWidget):
        def setPixmap(self,inner_pixmap):
            pixmap=qtgui.QPixmap(self._pixmap_size+2*self._margin_size)
            pixmap.fill(qtgui.QColor(255,255,255,255))
            
            painter = qtgui.QPainter()
            painter.begin(pixmap)
            X=self._margin_size.width()
            Y=self._margin_size.height()
            H=self._pixmap_size.height()
            W=self._pixmap_size.width()

            painter.drawPixmap(X,Y,inner_pixmap)

            pen=qtgui.QPen()
            pen.setWidth(10)
            pen.setCapStyle(qtcore.Qt.SquareCap)
            pen.setJoinStyle(qtcore.Qt.MiterJoin)
            pen.setStyle(qtcore.Qt.SolidLine)
            pen.setColor(qtgui.QColor(0,0,0,255))
            painter.setPen(pen)
            painter.drawRect(X,Y,W,H)

            painter.end() 
            super().setPixmap(pixmap)

    class HighlightWidget(LayerWidget):
        def highlight(self,rects):
            pixmap=qtgui.QPixmap(self._pixmap_size+2*self._margin_size)
            pixmap.fill(qtcore.Qt.transparent)
            painter = qtgui.QPainter()
            painter.begin(pixmap)
            H=self._pixmap_size.height()
            X0=self._margin_size.width()
            Y0=self._margin_size.height()

            pen=qtgui.QPen()
            pen.setWidth(10)
            pen.setCapStyle(qtcore.Qt.RoundCap)
            pen.setJoinStyle(qtcore.Qt.RoundJoin)
            for (x,y,w,h),bgcolor,fgcolor in rects:
                if bgcolor is not None:
                    painter.fillRect(x+X0,H-y-h+Y0,w,h,qtgui.QColor(*bgcolor)) 
                if fgcolor is not None:
                    pen.setColor(qtgui.QColor(*fgcolor))
                    painter.setPen(pen)
                    painter.drawRect(x+X0,H-y-h+Y0,w,h) 
            painter.end() 
            self.setPixmap(pixmap)

    class GridWidget(LayerWidget):
        def visible(self,visible):
            pixmap=qtgui.QPixmap(self._pixmap_size+2*self._margin_size)
            pixmap.fill(qtcore.Qt.transparent)
            if not visible:
                self.setPixmap(pixmap)
                return
            painter = qtgui.QPainter()
            painter.begin(pixmap)
            H=self._pixmap_size.height()
            W=self._pixmap_size.width()
            X0=self._margin_size.width()
            Y0=self._margin_size.height()

            pen=qtgui.QPen()
            pen.setWidth(5)
            pen.setCapStyle(qtcore.Qt.RoundCap)
            pen.setJoinStyle(qtcore.Qt.RoundJoin)
            pen.setStyle(qtcore.Qt.DotLine)

            minor_color=qtgui.QColor(100,255,255,100)
            major_color=qtgui.QColor(100,255,255,150)

            for color,step in [ (minor_color,100),(major_color,500) ]:
                pen.setColor(color)
                painter.setPen(pen)
                for x in range(0,W,step):
                    painter.drawLine(x+X0,Y0/2,x+X0,H+1.5*Y0)
                for y in range(0,H,step):
                    painter.drawLine(X0/2,H-y+Y0,W+1.5*X0,H-y+Y0)

            painter.setFont(self.font())
            tflags=qtcore.Qt.AlignHCenter | qtcore.Qt.AlignBottom
            bflags=qtcore.Qt.AlignHCenter | qtcore.Qt.AlignTop
            for x in range(0,W,500):
                painter.drawText(x+X0-250,0,500,Y0/2,tflags,str(x))
                painter.drawText(x+X0-250,H+1.5*Y0,500,Y0/2,bflags,str(x))

            painter.rotate(-90)
            tflags=qtcore.Qt.AlignHCenter | qtcore.Qt.AlignBottom
            bflags=qtcore.Qt.AlignHCenter | qtcore.Qt.AlignTop
            for x in range(0,H,500):
                painter.drawText(-(H-x+Y0)-250,0,500,X0/2,tflags,str(x))
                painter.drawText(-(H-x+Y0)-250,W+1.5*X0,500,X0/2,bflags,str(x))

            painter.resetTransform()
            
            pen=qtgui.QPen()
            pen.setWidth(10)
            pen.setCapStyle(qtcore.Qt.SquareCap)
            pen.setJoinStyle(qtcore.Qt.MiterJoin)
            pen.setStyle(qtcore.Qt.SolidLine)
            pen.setColor(qtgui.QColor(0,0,0,255))
            painter.setPen(pen)
            painter.drawRect(X0,Y0,W,H)

            painter.end() 
            self.setPixmap(pixmap)


    class RulersWidget(LayerWidget):
        firstPointClicked = qtcore.Signal(int,int)
        secondPointClicked = qtcore.Signal(int,int)

        def __init__(self,size,margin_size):
            super().__init__(size,margin_size)
            self.setMouseTracking(True)
            self._first=True
            self._marks=[]

        def mousePressEvent(self,event):
            x=event.x()
            y=event.y()
            H=self._pixmap_size.height()
            W=self._pixmap_size.width()
            X0=self._margin_size.width()
            Y0=self._margin_size.height()
            Htot=(2*self._margin_size+self._pixmap_size).height()
            Wtot=(2*self._margin_size+self._pixmap_size).width()

            sz=self.size()
            h=sz.height()
            w=sz.width()

            X=int(round(x*Wtot/w))
            Y=int(round(y*Htot/h))

            if X<X0: return
            if X>X0+W: return
            if Y<Y0: return
            if Y>Y0+H: return

            if event.button() == qtcore.Qt.RightButton:
                self._marks=[]
                return

            self._marks.append( (X,Y) )

            if self._first:
                self.firstPointClicked.emit(X-X0,H-Y+Y0)
            else:
                self.secondPointClicked.emit(X-X0,H-Y+Y0)
            self._first=not self._first
            
        def mouseMoveEvent(self,event):
            x=event.x()
            y=event.y()
            H=self._pixmap_size.height()
            W=self._pixmap_size.width()
            X0=self._margin_size.width()
            Y0=self._margin_size.height()
            Htot=(2*self._margin_size+self._pixmap_size).height()
            Wtot=(2*self._margin_size+self._pixmap_size).width()

            sz=self.size()
            h=sz.height()
            w=sz.width()

            X=int(round(x*Wtot/w))
            Y=int(round(y*Htot/h))

            if X<X0: return
            if X>X0+W: return
            if Y<Y0: return
            if Y>Y0+H: return

            pixmap=qtgui.QPixmap(self._pixmap_size+2*self._margin_size)
            pixmap.fill(qtcore.Qt.transparent)
            
            painter = qtgui.QPainter()
            painter.begin(pixmap)

            pen=qtgui.QPen()
            pen.setWidth(5)
            pen.setCapStyle(qtcore.Qt.RoundCap)
            pen.setJoinStyle(qtcore.Qt.RoundJoin)

            font=self.font()
            font_db=qtgui.QFontDatabase()
            sz=font.pointSize()
            SZ=int(round(sz*Htot/h))
            font=font_db.font(font.family(),font.styleName(),SZ)

            painter.setFont(font)

            color=qtgui.QColor(0,0,255,255)
            pen.setColor(color)
            painter.setPen(pen)

            for x,y in self._marks:
                self._draw_mark(painter,x,y,X0,Y0,H,W,SZ)
                

            color=qtgui.QColor(255,0,0,255)
            pen.setColor(color)
            painter.setPen(pen)
            self._draw_mark(painter,X,Y,X0,Y0,H,W,SZ,back=False)
            painter.end() 
            self.setPixmap(pixmap)


        def _draw_mark(self,painter,X,Y,X0,Y0,H,W,SZ,back=True):
            flags=qtcore.Qt.AlignHCenter | qtcore.Qt.AlignVCenter

            YSZ=2*SZ
            XSZ=4*YSZ
            Xt=X-XSZ if X-X0>=XSZ else X
            Yt=Y-YSZ if Y-Y0>=YSZ else Y

            painter.drawLine(X,Y0,X,H+Y0)
            painter.drawLine(X0,Y,W+X0,Y)
            if back:
                painter.fillRect(Xt,Yt,XSZ,YSZ,qtgui.QColor(255,255,255,255))
                painter.drawRect(Xt,Yt,XSZ,YSZ)
            painter.drawText(Xt,Yt,XSZ,YSZ,flags,"(%d,%d)" % (X-X0,H-Y+Y0) )

            

    def __init__(self,path):
        qtwidgets.QWidget.__init__(self)
        self._path=path

        v_layout=qtwidgets.QVBoxLayout()

        self._factor_label=qtwidgets.QLabel()

        pixmap=qtgui.QPixmap(self._path)
        self._pixmap_size=pixmap.size()
        self._margin_size=qtcore.QSize(100,100)

        self._g_widget=qtwidgets.QWidget()
        g_layout=qtwidgets.QGridLayout()
        g_layout.setVerticalSpacing(0)
        g_layout.setHorizontalSpacing(0)
        g_layout.setContentsMargins(0,0,0,0)

        self._background=self.BackgroundWidget(self._pixmap_size,self._margin_size)
        self._background.setPixmap(pixmap)
        self._highlight=self.HighlightWidget(self._pixmap_size,self._margin_size)
        self._grid=self.GridWidget(self._pixmap_size,self._margin_size)
        self._rulers=self.RulersWidget(self._pixmap_size,self._margin_size)

        g_layout.addWidget(self._background,0,0,qtcore.Qt.AlignLeft | qtcore.Qt.AlignTop)
        g_layout.addWidget(self._highlight,0,0,qtcore.Qt.AlignLeft | qtcore.Qt.AlignTop)
        g_layout.addWidget(self._grid,0,0,qtcore.Qt.AlignLeft | qtcore.Qt.AlignTop)
        g_layout.addWidget(self._rulers,0,0,qtcore.Qt.AlignLeft | qtcore.Qt.AlignTop)

        self._g_widget.setLayout(g_layout)

        self._scroll=qtwidgets.QScrollArea()
        self._scroll.setWidget(self._g_widget)
        self._scroll.setVerticalScrollBarPolicy(qtcore.Qt.ScrollBarAlwaysOn) #Qt.ScrollBarAsNeeded
        self._scroll.setHorizontalScrollBarPolicy(qtcore.Qt.ScrollBarAlwaysOn)

        self._factor=1
        self.fit()

        h_layout=qtwidgets.QHBoxLayout()
        h_widget=qtwidgets.QWidget()
        h_widget.setLayout(h_layout)

        self._first_x_label=qtwidgets.QLabel()
        self._first_y_label=qtwidgets.QLabel()
        self._first_c_label=qtwidgets.QLabel()
        self._second_x_label=qtwidgets.QLabel()
        self._second_y_label=qtwidgets.QLabel()
        self._second_c_label=qtwidgets.QLabel()
        self._second_p_label=qtwidgets.QLabel()
        h_layout.addWidget(self._first_x_label,stretch=0)
        h_layout.addWidget(self._first_c_label,stretch=0)
        h_layout.addWidget(self._first_y_label,stretch=0)
        h_layout.addWidget(self._second_p_label,stretch=0)
        h_layout.addWidget(self._second_x_label,stretch=0)
        h_layout.addWidget(self._second_c_label,stretch=0)
        h_layout.addWidget(self._second_y_label,stretch=0)

        h_layout.addWidget(self._factor_label,stretch=1)

        h_layout.setMargin(0)

        v_layout.addWidget(h_widget,stretch=0)
        v_layout.addWidget(self._scroll,stretch=1)
        v_layout.setSpacing(0)

        self.setLayout(v_layout)

        self.setStyleSheet("border: 1px solid #c0c0c0")
        self._background.setStyleSheet("background: white;border: none;")

        self._factor_label.setStyleSheet("background: #f0f0f0; border-bottom: #d0d0d0")
        self._factor_label.setMargin(0)
        self._factor_label.setAlignment(qtcore.Qt.AlignRight)
        h_widget.setStyleSheet("background: #f0f0f0; border: none")

        self._scroll.setStyleSheet("border-top: #d0d0d0")

        self._rulers.firstPointClicked.connect(self._first_point_clicked)
        self._rulers.secondPointClicked.connect(self._second_point_clicked)

    def _first_point_clicked(self,x,y):
        self._first_x_label.setText(str(x))
        self._first_y_label.setText(str(y))
        self._first_c_label.setText(",")

    def _second_point_clicked(self,x,y):
        self._second_x_label.setText(str(x))
        self._second_y_label.setText(str(y))
        self._second_c_label.setText(" , ")
        self._second_p_label.setText(" – ")

    def get_points(self):
        x1=self._first_x_label.text()
        y1=self._first_y_label.text()
        x2=self._second_x_label.text()
        y2=self._second_y_label.text()

        first= (int(x1),int(y1)) if x1 else None
        second= (int(x2),int(y2)) if x2 else None

        return first,second

    def resizeEvent(self,event):
        qtwidgets.QWidget.resizeEvent(self,event)
        self.fit()

    def setFont(self,font):
        self._grid.setFont(font)
        self._rulers.setFont(font)
        super().setFont(font)
       
    def zoom_out(self):
        self._scale(0.9*self._factor)

    def zoom_in(self): 
        self._scale(1.1*self._factor)

    def show_grid(self,show):
        self._grid.visible(show)

    def highlight_rule(self,rule):
        self._highlight.highlight(rule.highlight_rects())

    def fit(self):
        max_size=self._scroll.viewport().size()

        m_w=max_size.width()
        m_h=max_size.height()
        p_w=self._pixmap_size.width()
        p_h=self._pixmap_size.height()

        if m_w/m_h < p_w/p_h: 
            factor=m_w/p_w
        else:
            factor=m_h/p_h
        self._scale(factor)

    def _scale(self,factor):
        self._factor=factor
        self._factor_label.setText("%0.0f %%" % (100*self._factor))

        self._g_widget.resize(factor * self._pixmap_size)
        self._background.resize(factor * self._pixmap_size)
        self._highlight.resize(factor * self._pixmap_size)
        self._grid.resize(factor * self._pixmap_size)
        self._rulers.resize(factor * self._pixmap_size)

        def adjust_scroll_bar(scroll_bar,factor):
            scroll_bar.setValue(int(factor * scroll_bar.value() + ((factor - 1) * scroll_bar.pageStep()/2)))

        adjust_scroll_bar(self._scroll.horizontalScrollBar(), factor)
        adjust_scroll_bar(self._scroll.verticalScrollBar(), factor)

class OcrWidget(qtwidgets.QTreeView):
    class OcrModel(qtcore.QAbstractItemModel):

        def __init__(self,page,*args,**kwargs):
            self._page=page
            qtcore.QAbstractItemModel.__init__(self,*args,**kwargs)
            self._columns=["level","xmin","ymin","xmax","ymax","content"]
            #self._rules=self._page.text_structure.rules

        def headerData(self,section,orientation,role):
            if role == qtcore.Qt.TextAlignmentRole:
                if section in [1,2,3,4]:
                    return qtcore.Qt.AlignRight
                return None
            if role not in [ qtcore.Qt.DisplayRole, qtcore.Qt.EditRole ]: 
                return qtcore.QAbstractItemModel.headerData(self,section,orientation,role)
            if orientation==qtcore.Qt.Orientation.Vertical:
                return qtcore.QAbstractItemModel.headerData(self,section,orientation,role)
            return self._columns[section]

        def columnCount(self,index):
            return 6

        def rowCount(self, index = qtcore.QModelIndex()):
            if index.isValid():  # internal nodes
                obj = index.internalPointer()
            else:
                obj=None
            return self._page.count_children_text_rule(obj)

        def index(self,row,column,parent=qtcore.QModelIndex()): 
            if not parent.isValid(): 
                parent_obj=None
            else:
                parent_obj = parent.internalPointer()
            obj=self._page.get_text_rule(parent_obj,row)
            if not obj: return qtcore.QModelIndex()
            return self.createIndex(row, column, obj)

        def parent(self, index):
            if not index.isValid():
                return qtcore.QModelIndex()
            child=index.internalPointer()
            if child.parent is None: return qtcore.QModelIndex()
            row=self._page.index_text_rule(child.parent)
            return self.createIndex(row,0,child.parent)

        def data(self, index, role):
            if not index.isValid(): return None
            if role not in [ qtcore.Qt.DisplayRole, qtcore.Qt.EditRole, 
                             qtcore.Qt.TextAlignmentRole ]: 
                return None
            obj=index.internalPointer()
            col=index.column()
            if role == qtcore.Qt.TextAlignmentRole:
                if col in [1,2,3,4]:
                    return qtcore.Qt.AlignRight
                return None
            if col==0: return obj.level
            if col==1: return obj.xmin
            if col==2: return obj.ymin
            if col==3: return obj.xmax
            if col==4: return obj.ymax

            return obj.content

        def flags(self,index):
            col=index.column()
            if col!=5:
                return qtcore.Qt.ItemIsEditable | qtcore.QAbstractItemModel.flags(self,index)
            obj=index.internalPointer()
            if obj.children:
                return qtcore.QAbstractItemModel.flags(self,index)
            return qtcore.Qt.ItemIsEditable | qtcore.QAbstractItemModel.flags(self,index)

        def setData(self,index,value,role):
            if role not in [ qtcore.Qt.DisplayRole, qtcore.Qt.EditRole ]: return False
            col=index.column()
            obj=index.internalPointer()
            if col==0:
                obj.level=value
                self.dataChanged.emit(index, index)
                return True
            if col==5:
                if obj.children: return False
                obj.text=value
                self.dataChanged.emit(index, index)
                return True
            try:
                if col==1: obj.xmin=int(value)
                if col==2: obj.ymin=int(value)
                if col==3: obj.xmax=int(value)
                if col==4: obj.ymax=int(value)
            except ValueError as e:
                return False
            self.dataChanged.emit(index, index)
            return True

        def insertRows(self,row,count,parent=qtcore.QModelIndex()):
            self.beginInsertRows(parent,row,row+count-1)
            if not parent.isValid():
                parent_obj=None
            else:
                parent_obj=parent.internalPointer()
            self._page.insert_text_rules(parent_obj,row,count)
            self.endInsertRows()            
            self.layoutChanged.emit()
            return True

        def duplicateRow(self,index):
            self._page.duplicate_text_rule(index.internalPointer())
            self.layoutChanged.emit()
            return True

        def create_rule(self,parent,level,xmin,ymin,xmax,ymax,text):
            self._page.create_text_rule(parent.internalPointer(),level,
                                        xmin,ymin,xmax,ymax,text)
            self.dataChanged.emit(parent, parent)
            self.layoutChanged.emit()
            return True

        def merge_above_rule(self,index):
            self._page.merge_above_text_rule(index.internalPointer())
            self.dataChanged.emit(index, index)
            self.layoutChanged.emit()
            return True
            
        def merge_below_rule(self,index):
            self._page.merge_below_text_rule(index.internalPointer())
            self.dataChanged.emit(index, index)
            self.layoutChanged.emit()
            return True
            
        def removeRows(self,row,count,parent=qtcore.QModelIndex()):
            self.beginRemoveRows(parent,row,row+count-1)
            if not parent.isValid():
                parent_obj=None
            else:
                parent_obj=parent.internalPointer()
            self._page.remove_text_rules(parent_obj,row,count)
            self.endRemoveRows()            
            self.layoutChanged.emit()
            return True

        def upper_rule(self,index):
            obj=index.internalPointer()
            if obj.children: return False
            obj.text=obj.text.upper()
            self.dataChanged.emit(index, index)
            return True

        def lower_rule(self,index):
            obj=index.internalPointer()
            if obj.children: return False
            obj.text=obj.text.lower()
            self.dataChanged.emit(index, index)
            return True

        def capitalize_rule(self,index):
            obj=index.internalPointer()
            if obj.children: return False
            obj.text=obj.text.capitalize()
            self.dataChanged.emit(index, index)
            return True

        def _accentize(self,txt):
            if txt[-1] not in "aeiouèéAEIOUÈÉ": return txt
            if txt[-1]=="a": return txt[:-1]+"à"
            if txt[-1]=="i": return txt[:-1]+"ì"
            if txt[-1]=="o": return txt[:-1]+"ò"
            if txt[-1]=="u": return txt[:-1]+"ù"
            if txt[-1]=="è": return txt[:-1]+"é"
            if txt[-1]=="é": return txt[:-1]+"è"
            if txt[-1]=="A": return txt[:-1]+"À"
            if txt[-1]=="I": return txt[:-1]+"Ì"
            if txt[-1]=="O": return txt[:-1]+"Ò"
            if txt[-1]=="U": return txt[:-1]+"Ù"
            if txt[-1]=="È": return txt[:-1]+"É"
            if txt[-1]=="É": return txt[:-1]+"È"
            if txt=="e": return "è"
            if txt=="E": return "È"
            if txt.lower()=="ce":
                if txt[-1]=="e": return txt[:-1]+"'è"
                if txt[-1]=="E": return txt[:-1]+"'È"
            if txt.lower().endswith("che"):
                if txt[-1]=="e": return txt[:-1]+"é"
                if txt[-1]=="E": return txt[:-1]+"É"
            if txt[-1]=="e": return txt[:-1]+"è"
            if txt[-1]=="E": return txt[:-1]+"È"

        def accentize_rule(self,index):
            obj=index.internalPointer()
            if obj.children: return False
            obj.text=self._accentize(obj.text)
            self.dataChanged.emit(index, index)
            return True

        def crop_to_children(self,index):
            obj=index.internalPointer()
            obj.crop_to_children()
            self.dataChanged.emit(index, index)

        def split_rule(self,index,splitted):
            obj=index.internalPointer()
            self._page.split_rule(obj,splitted)
            self.dataChanged.emit(index, index)
            self.layoutChanged.emit()

        def shift_down_rule(self,index,val):
            obj=index.internalPointer()
            self._page.shift_down_text_rule(obj,val)
            self.dataChanged.emit(index, index)
            self.layoutChanged.emit()

        def shift_up_rule(self,index,val):
            obj=index.internalPointer()
            self._page.shift_up_text_rule(obj,val)
            self.dataChanged.emit(index, index)
            self.layoutChanged.emit()

        def shift_right_rule(self,index,val):
            obj=index.internalPointer()
            self._page.shift_right_text_rule(obj,val)
            self.dataChanged.emit(index, index)
            self.layoutChanged.emit()

        def shift_left_rule(self,index,val):
            obj=index.internalPointer()
            self._page.shift_left_text_rule(obj,val)
            self.dataChanged.emit(index, index)
            self.layoutChanged.emit()            

        def move_up(self,index):
            obj=index.internalPointer()
            self._page.move_up(obj)
            self.layoutChanged.emit()
            row=self._page.index_text_rule(obj)
            return self.createIndex(row,0,obj)

        def move_down(self,index):
            obj=index.internalPointer()
            self._page.move_down(obj)
            self.layoutChanged.emit()
            row=self._page.index_text_rule(obj)
            return self.createIndex(row,0,obj)

        def move_left(self,index):
            obj=index.internalPointer()
            self._page.move_left(obj)
            self.layoutChanged.emit()
            row=self._page.index_text_rule(obj)
            return self.createIndex(row,0,obj)

        def move_right(self,index):
            obj=index.internalPointer()
            self._page.move_right(obj)
            self.layoutChanged.emit()
            row=self._page.index_text_rule(obj)
            return self.createIndex(row,0,obj)

    
    class ImportAreaForm(qtwidgets.QFormLayout):
        def __init__(self,levels):
            qtwidgets.QFormLayout.__init__(self)

            self.level=qtwidgets.QComboBox()
            for v in levels:
                self.level.addItem(v)
            self.text=qtwidgets.QLineEdit()

            self.addRow("level", self.level)
            self.addRow("text", self.text)

        def get_data(self):
            text=self.text.text()
            level=self.level.currentText()
            return [level,text]

    class ImportAreaDialog(qtwidgets.QDialog):
        def __init__(self,window,levels,*args,**kwargs):
            super().__init__(window,*args,**kwargs)
            self.setWindowTitle("Import area")
        
            flags = qtwidgets.QDialogButtonBox.Ok | qtwidgets.QDialogButtonBox.Cancel
        
            button_box = qtwidgets.QDialogButtonBox(flags)
            button_box.accepted.connect(self.accept)
            button_box.rejected.connect(self.reject)

            self.level=qtwidgets.QComboBox()
            for v in levels:
                self.level.addItem(v)
            self.text=qtwidgets.QLineEdit()

            f_layout=qtwidgets.QFormLayout()
            f_layout.addRow("level", self.level)
            f_layout.addRow("text", self.text)
            f_widget=qtwidgets.QWidget(self)
            f_widget.setLayout(f_layout)

            v_layout = qtwidgets.QVBoxLayout()
            v_layout.addWidget(f_widget)
            v_layout.addWidget(button_box)
            self.setLayout(v_layout)

        def get_data(self):
            ret=self.exec_()
            text=self.text.text()
            level=self.level.currentText()
            return level,text,ret==self.Accepted


    def __init__(self,page,select_callback):
        self._page=page
        self._select_callback=select_callback
        qtwidgets.QTreeView.__init__(self)
        self._model=self.OcrModel(page)
        self.setModel(self._model)
        self.setAlternatingRowColors(True)
        self.expandAll()
        self.setSelectionMode(self.SingleSelection)
        self.setSelectionBehavior(self.SelectRows)

        self._model.dataChanged.connect(self._data_changed)
        self.selectionModel().selectionChanged.connect(self._selection_changed)

        self.setContextMenuPolicy(qtcore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.rule_menu_open)

        self.setDragEnabled(True)
        self.acceptDrops()
        self.setDragDropMode(self.InternalMove)
        self.setDropIndicatorShown(True)

        self.shortcuts = {
            "delete_rows": qtwidgets.QShortcut(qtgui.QKeySequence.Delete, self),
            "crop_to_children": qtwidgets.QShortcut(qtgui.QKeySequence(qtcore.Qt.Key_C),
                                                    self),
            "save": qtwidgets.QShortcut(qtgui.QKeySequence(qtcore.Qt.Key_S),self),
            "move_right": qtwidgets.QShortcut(qtgui.QKeySequence(qtcore.Qt.Key_Tab),self),
            "import_area": qtwidgets.QShortcut(qtgui.QKeySequence(qtcore.Qt.Key_A),self),
        }
        self.shortcuts["delete_rows"].activated.connect(self._delete_selected_rule)
        self.shortcuts["crop_to_children"].activated.connect(self._crop_to_children_selected_rule)
        self.shortcuts["move_right"].activated.connect(self.move_right)

    def refresh(self):
        self._model.layoutChanged.emit()

    def _delete_selected_rule(self):
        index=self.selectionModel().currentIndex()
        if not index.isValid(): return
        self._model.removeRow(index.row(),parent=self._model.parent(index))

    def _crop_to_children_selected_rule(self):
        index=self.selectionModel().currentIndex()
        if not index.isValid(): return
        self._model.crop_to_children(index)

    def import_rule(self,xmin,ymin,xmax,ymax):
        index=self.selectionModel().currentIndex()
        if not index.isValid(): return
        obj=index.internalPointer()
        levels=obj.sub_rule_levels()
        if not levels: return
        #dialog=self.ImportAreaDialog(self.window(),levels)
        dialog=widgets.FormDialog(self.window(),"Import area",
                                  self.ImportAreaForm(levels))
        level,text,ok=dialog.get_data()
        if not ok: return
        self._model.create_rule(index,level,xmin,ymin,xmax,ymax,text)

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

    def rule_menu_open(self, point):
        # Infos about the node selected.
        index = self.indexAt(point)
        if not index.isValid(): return
        menu=qtwidgets.QMenu(self)
        maction=menu.addAction("add")
        maction.triggered.connect(lambda: self._model.insertRow(0,parent=index))
        menu.addSeparator()
        maction=menu.addAction("duplicate")
        maction.triggered.connect(lambda: self._model.duplicateRow(index))
        maction=menu.addAction("split")
        maction.triggered.connect(lambda: self._split_rule(index))
        maction=menu.addAction("merge above")
        maction.triggered.connect(lambda: self._model.merge_above_rule(index))
        maction=menu.addAction("merge below")
        maction.triggered.connect(lambda: self._model.merge_below_rule(index))
        maction=menu.addAction("crop to children")
        maction.triggered.connect(lambda: self._model.crop_to_children(index))
        maction.setShortcut(qtgui.QKeySequence(qtcore.Qt.Key_C))
        maction.setShortcutContext(qtcore.Qt.WindowShortcut)
        maction.setShortcutVisibleInContextMenu(True)
        menu.addSeparator()

        maction=menu.addAction("shift area up")
        maction.triggered.connect(lambda: self._shift_up_rule(index))
        maction=menu.addAction("shift area down")
        maction.triggered.connect(lambda: self._shift_down_rule(index))
        maction=menu.addAction("shift area left")
        maction.triggered.connect(lambda: self._shift_left_rule(index))
        maction=menu.addAction("shift area right")
        maction.triggered.connect(lambda: self._shift_right_rule(index))

        menu.addSeparator()

        maction=menu.addAction("lower")
        maction.triggered.connect(lambda: self._model.lower_rule(index))
        maction=menu.addAction("upper")
        maction.triggered.connect(lambda: self._model.upper_rule(index))
        maction=menu.addAction("capitalize")
        maction.triggered.connect(lambda: self._model.capitalize_rule(index))
        maction=menu.addAction("accentize")
        maction.triggered.connect(lambda: self._model.accentize_rule(index))

        menu.addSeparator()
        maction=menu.addAction("delete")
        maction.setShortcut(qtgui.QKeySequence.Delete)
        maction.setShortcutContext(qtcore.Qt.WindowShortcut)
        maction.setShortcutVisibleInContextMenu(True)

        maction.triggered.connect(lambda: self._model.removeRow(index.row(),parent=self._model.parent(index)))
        menu.exec_(self.mapToGlobal(point))

    def _split_rule(self,index):
        obj=index.internalPointer()
        newtext,ok=qtwidgets.QInputDialog.getText(self,"split rule",
                                                  "Separate words by space",
                                                  text=obj.content)
        if not ok: return
        self._model.split_rule(index,newtext.split())

    def _shift_down_rule(self,index):
        val,ok=qtwidgets.QInputDialog.getInt(self,"shift down","Amount",value=100)
        if not ok: return
        self._model.shift_down_rule(index,val)

    def _shift_up_rule(self,index):
        val,ok=qtwidgets.QInputDialog.getInt(self,"shift up","Amount",value=100)
        if not ok: return
        self._model.shift_up_rule(index,val)

    def _shift_left_rule(self,index):
        val,ok=qtwidgets.QInputDialog.getInt(self,"shift left","Amount",value=100)
        if not ok: return
        self._model.shift_left_rule(index,val)

    def _shift_right_rule(self,index):
        val,ok=qtwidgets.QInputDialog.getInt(self,"shift right","Amount",value=100)
        if not ok: return
        self._model.shift_right_rule(index,val)        
        
    def _select(self,index=None):
        if index is None:
            index=self.selectionModel().currentIndex()
        if not index.isValid(): return
        rule=index.internalPointer()
        self._select_callback(rule)

    def _data_changed(self,top_left,bottom_right,roles=[]):
        self._select(top_left)

    def _selection_changed(self,selected,deselected):
        indexes=selected.indexes()
        if not indexes: return self._select()
        index=indexes[0]
        self._select(index)

class PageWidget(qtwidgets.QSplitter):
    labelChanged = qtcore.Signal(object)

    class PageToolBar(qtwidgets.QToolBar):

        def _add_action(self,icon,tooltip,callback,style="Solid"):
            action=self.addAction(icon)
            action.setToolTip(tooltip)
            action.setFont(self._app.awesome_font(size=10,style=style))
            action.triggered.connect(callback)
            return action

        def __init__(self,main,*args,**kwargs):
            self._app=main._app
            self._main=main
            qtwidgets.QToolBar.__init__(self,*args,parent=main,**kwargs)
            self.setSizePolicy(qtwidgets.QSizePolicy.Minimum,qtwidgets.QSizePolicy.Minimum)

            self._add_action("","zoom out",self._main._image.zoom_out)
            self._add_action("","zoom in",self._main._image.zoom_in)
            self._add_action("","fit area",self._main._image.fit)
            action=self.addAction("")
            action.setToolTip("show/hide grid")
            action.setFont(self._app.awesome_font(size=10))
            action.setCheckable(True)
            action.toggled.connect(self._main._image.show_grid)

            self._add_action("","import area",self._main._import_area)

            self.addSeparator()
            #self._add_action("","redo ocr",self._main._ocr,style="Regular")
            self._add_action("","reload text",self._main._reload_text,style="Regular")
            self._add_action("","save text",self._main._save_text,style="Regular")

            self.addSeparator()
            self._add_action("","move up",lambda checked: self._main._ocr_widget.move_up())
            self._add_action("","move down",lambda checked: self._main._ocr_widget.move_down())
            #self._add_action("","move left",lambda checked: self._main._ocr_widget.move_left())
            self._add_action("","move right",lambda checked: self._main._ocr_widget.move_right())

            
    class TitleLineEdit(qtwidgets.QLineEdit):
        section="Pages"

        def __init__(self,application,page):
            qtwidgets.QLineEdit.__init__(self)
            self._app=application
            self._page=page
            self.setText(self._page.title)
            self.textChanged.connect(self._changed)
            self.setFont(self._app.main_font(size=10))

        def _changed(self):
            val=self.text()
            self._page.title=val
            if self._app.project is not None:
                self._app.project[self.section][self._page.path]=val
            self._app.models["page_numbering"].layoutChanged.emit()

    def __init__(self,app,page):
        self._app=app
        self._page=page
        qtwidgets.QSplitter.__init__(self)

        ### Left
        self._image=ImageWidget(self._page.path)
        self._image.setFont(self._app.main_font(size=12))
        
        self.addWidget(self._image)

        ### Right

        # bottom
        tab=qtwidgets.QTabWidget()
        self._ocr_area=qtwidgets.QTextEdit()
        if self._page.text is not None:
            self._ocr_area.setPlainText(self._page.text)
        self._ocr_widget=OcrWidget(self._page,self._image.highlight_rule)
        self._ocr_widget.setFont(self._app.main_font(size=10))
        self._ocr_area.setFont(self._app.main_font(size=10))

        self._ocr_widget.shortcuts["save"].activated.connect(self._save_text)
        self._ocr_widget.shortcuts["import_area"].activated.connect(self._import_area)


        tab.addTab(self._ocr_widget,"tree")
        tab.addTab(self._ocr_area,"txt")

        # top
        h_layout=qtwidgets.QHBoxLayout()
        h_widget=qtwidgets.QWidget()
        h_widget.setLayout(h_layout)
        self._title_widget=self.TitleLineEdit(self._app,self._page)
        h_layout.addWidget(self._title_widget)

        self._title_widget.textChanged.connect(lambda: self.labelChanged.emit(self))

        #h_layout.addWidget(toolbar,stretch=0)
        h_layout.addStretch(stretch=1)

        for t in [ page.format,
                   "%sx%s" % (page.width,page.height),
                   "%d-bit" % page.depth,
                   "%d dpi" % page.dpi ]:
            lab=qtwidgets.QLabel(t)
            lab.setFont(self._app.main_font(size=10))
            h_layout.addWidget(lab,stretch=0)
        
        v_layout=qtwidgets.QVBoxLayout()
        v_layout.addWidget(h_widget,stretch=0)

        toolbar=self.PageToolBar(self)
        v_layout.addWidget(toolbar,stretch=0)
        v_layout.addWidget(tab,stretch=1)


        right_widget=qtwidgets.QWidget()
        right_widget.setLayout(v_layout)
        self.addWidget(right_widget)

        ### Signals
        #self._ocr_widget.selectionModel().selectionChanged.connect(self._ocr_widget_selection_changed)
        #self._ocr_widget.model().dataChanged.connect(self._ocr_widget_data_changed)

    def _ocr(self): pass

    def update_page_number(self):
        self._title_widget.setText(self._page.title)

    def _save_text(self): 
        self._page.save_text_structure()
        self._ocr_area.setPlainText(self._page.text)

    def _reload_text(self): 
        self._page.reload_text()
        self._ocr_widget.refresh()
        self._ocr_area.setPlainText(self._page.text)

    @property
    def label(self):
        return str(self._page)
        # label=os.path.basename(self._page.path)
        # if self._page.title is not None:
        #     label="[%s] %s" % (self._page.title,label)
        # return label

    def _import_area(self):
        first,second=self._image.get_points()
        if first is None: return
        if second is None: return
        xmin=min(first[0],second[0])
        xmax=max(first[0],second[0])
        ymin=min(first[1],second[1])
        ymax=max(first[1],second[1])
        self._ocr_widget.import_rule(xmin,ymin,xmax,ymax)

class ProjectWidget(qtwidgets.QWidget):

    def __init__(self,app):
        self._app=app
        qtwidgets.QWidget.__init__(self)
        self.setFont(self._app.main_font(size=10))

        v_layout = qtwidgets.QVBoxLayout()

        buttons=widgets.HButtonBar([ 
            ("Apply OCR",self._apply_ocr),
            ("Create Djvu",self._djvubind),
        ])
        v_layout.addWidget(buttons,stretch=0)

        self.cover_front=widgets.OpenFileWidget()
        self.cover_back=widgets.OpenFileWidget()
        f_layout=qtwidgets.QFormLayout()
        f_layout.addRow("cover_front", self.cover_front)
        f_layout.addRow("cover_back", self.cover_back)
        f_widget=qtwidgets.QWidget(self)
        f_widget.setLayout(f_layout)
        v_layout.addWidget(f_widget,stretch=0)

        self.tab=qtwidgets.QTabWidget()
        v_layout.addWidget(self.tab,stretch=1)

        self.setLayout(v_layout)

        self.cover_front.field.textChanged.connect(self._cover_front_changed)
        self.cover_back.field.textChanged.connect(self._cover_back_changed)

        self._app.models["page_numbering"].pageNumberChanged.connect(self._update_page_numbers)

    def _update_page_numbers(self):
        for w in self.tab.findChildren(PageWidget):
            w.update_page_number()

    def _cover_front_changed(self):
        val=self.cover_front.text()
        self._app.project["Cover front"]=val

    def _cover_back_changed(self):
        val=self.cover_back.text()
        self._app.project["Cover back"]=val

    def _page_label_changed(self,widget):
        ind=self.tab.indexOf(widget)
        self.tab.setTabText(ind,widget.label)

    def set_project(self,project): 
        self.tab.clear() # GC non cancella le pagine, le rimuove e basta
        for page in self._app.project.book.pages:
            widget=PageWidget(self._app,page)
            self.tab.addTab(widget,widget.label)
            widget.labelChanged.connect(self._page_label_changed)
        
        #widget=CoverWidget()
        #self.tab.insertTab(0,widget,widget.label)

        self.cover_front.field.textChanged.disconnect(self._cover_front_changed)
        if "Cover front" in self._app.project:
            self.cover_front.setText(self._app.project["Cover front"])
        else:
            self.cover_front.setText("")
        self.cover_front.field.textChanged.connect(self._cover_front_changed)

        self.cover_back.field.textChanged.disconnect(self._cover_back_changed)
        if "Cover back" in self._app.project:
            self.cover_back.setText(self._app.project["Cover back"])
        else:
            self.cover_back.setText("")
        self.cover_back.field.textChanged.connect(self._cover_back_changed)


    def _apply_ocr(self):
        self._app.project.apply_ocr()
        
    def _djvubind(self): 
        dialog = qtwidgets.QFileDialog(self._app.window)
        dialog.setFileMode(qtwidgets.QFileDialog.AnyFile)
        dialog.setAcceptMode(qtwidgets.QFileDialog.AcceptSave)
        dialog.setDirectory(".")
        if not dialog.exec_(): return
        fnames = dialog.selectedFiles()
        djvu_name = fnames[0]
        if not djvu_name.endswith(".djvu"):
            djvu_name+=".djvu"
        djvu_name=os.path.abspath(djvu_name)
        self._app.project.djvubind(djvu_name)
