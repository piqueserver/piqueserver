# Copyright (c) Mathias Kaerlev 2011.

# This file is part of pyspades.

# pyspades is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# pyspades is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with pyspades.  If not, see <http://www.gnu.org/licenses/>.

"""
pyspades - map editor
"""

import sys
sys.path.append('..')

import math
from PySide import QtGui, QtCore
from PySide.QtCore import Qt
from PySide.QtGui import QPainter

from pyspades.load import VXLData, get_color_tuple

colors = {}

class LabeledSpinBox(QtGui.QWidget):
    def __init__(self, text, *arg, **kw):
        super(LabeledSpinBox, self).__init__(*arg, **kw)
        self.layout = QtGui.QHBoxLayout(self)
        self.label = QtGui.QLabel(text)
        self.label.setAlignment(Qt.AlignCenter)
        self.spinbox = QtGui.QSpinBox()
        for item in (self.label, self.spinbox):
            self.layout.addWidget(item)

class LabeledWidget(QtGui.QWidget):
    def __init__(self, text, widget, *arg, **kw):
        super(LabeledWidget, self).__init__(*arg, **kw)
        self.layout = QtGui.QHBoxLayout(self)
        self.label = QtGui.QLabel(text)
        self.label.setAlignment(Qt.AlignCenter)
        self.widget = widget
        for item in (self.label, self.widget):
            self.layout.addWidget(item)

class EditWidget(QtGui.QWidget):
    scale = 1
    old_x = old_y = None
    image = None
    brush_size = 2.0
    def __init__(self, parent):
        super(EditWidget, self).__init__(parent)
        self.map = self.parent().map
        self.set_z(63)
        self.update_scale()
        self.set_color(Qt.black)
        self.eraser = Qt.transparent
    
    def update_scale(self):
        value = 512 * self.scale
        self.resize(value, value)
        
    def paintEvent(self, paintEvent):
        painter = QPainter(self)
        painter.scale(self.scale, self.scale)
        painter.drawRect(0, 0, 511, 511)
        painter.drawImage(0, 0, self.image)
    
    def set_color(self, color):
        self.color = color
    
    def mousePressEvent(self, event):
        self.old_x = self.old_y = None
        button = event.button()
        if button == Qt.LeftButton:
            self.current_color = self.color
        elif button == Qt.RightButton:
            self.current_color = self.eraser
        else:
            self.current_color = None
            return
        self.draw_pencil(event)
    
    def mouseMoveEvent(self, event):
        if self.current_color is None:
            return
        self.draw_pencil(event)
    
    def draw_pencil(self, event):
        value = 512.0 * self.scale
        x = int(event.x() / value * 512.0)
        y = int(event.y() / value * 512.0)
        x = max(0, min(511, x))
        y = max(0, min(511, y))
        if x in xrange(512) and y in xrange(512):
            old_x = self.old_x
            old_y = self.old_y
            color = self.current_color
            map = self.map
            if old_x is None and old_y is None:
                old_x = x
                old_y = y
            z = self.z
            image = self.image
            painter = QPainter(image)
            if self.current_color is self.eraser:
                painter.setCompositionMode(QPainter.CompositionMode_Source)
            pen = QtGui.QPen(color)
            pen.setWidth(self.brush_size)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawLine(old_x, old_y, x, y)
            self.repaint()
        self.old_x = x
        self.old_y = y
    
    def wheelEvent(self, wheelEvent):
        self.scale += (wheelEvent.delta() / 120.0) / 10.0
        self.update_scale()
        self.repaint()
    
    def set_z(self, z):
        map = self.map
        image = self.image
        if image is not None:
            map.set_overview(self.overview, self.z)
        self.z = max(0, min(63, z))
        self.overview = overview = map.get_overview(self.z)
        self.image = image = QtGui.QImage(overview, 512, 512,
            QtGui.QImage.Format_ARGB32)
        self.repaint()
    
    def save_overview(self):
        self.map.set_overview(self.overview, self.z)
    
    def map_updated(self):
        self.image = None
        self.map = self.parent().parent().parent().map
        self.set_z(self.z)

class ScrollArea(QtGui.QScrollArea):
    def wheelEvent(self, wheelEvent):
        self.widget().wheelEvent(wheelEvent)

class Settings(QtGui.QWidget):
    def __init__(self, editor, *arg, **kw):
        self.editor = editor
        super(Settings, self).__init__(*arg, **kw)
        layout = QtGui.QVBoxLayout(self)
        
        self.z_value = LabeledSpinBox('Current Z')
        self.z_value.spinbox.setRange(0, 63)
        self.z_value.spinbox.setValue(editor.z)
        self.z_value.spinbox.valueChanged.connect(self.set_z)
        layout.addWidget(self.z_value)

        self.brush_size = LabeledSpinBox('Brush size')
        self.brush_size.spinbox.setValue(editor.brush_size)
        self.brush_size.spinbox.valueChanged.connect(self.set_brush_size)
        layout.addWidget(self.brush_size)

        self.color_button = QtGui.QPushButton('Set color')
        self.color_button.clicked.connect(self.set_color)
        layout.addWidget(self.color_button)
    
    def set_brush_size(self):
        self.editor.brush_size = self.brush_size.spinbox.value()
    
    def set_z(self):
        self.editor.set_z(self.z_value.spinbox.value())
    
    def set_color(self):
        foo = QtGui.QColorDialog.getColor()
        self.editor.set_color(foo)

class MapEditor(QtGui.QMainWindow):
    def __init__(self, *arg, **kw):
        super(MapEditor, self).__init__(*arg, **kw)

        menu = self.menuBar()
        
        self.file = menu.addMenu('&File')
        
        self.new_action = QtGui.QAction('&New', self,
            triggered = self.new_selected)
        self.file.addAction(self.new_action)
        
        self.load_action = QtGui.QAction('&Load', self,
            triggered = self.load_selected)
        self.file.addAction(self.load_action)
        
        self.save_action = QtGui.QAction('&Save', self, 
            shortcut=QtGui.QKeySequence.Save, triggered = self.save_selected)
        self.file.addAction(self.save_action)
        
        self.map = VXLData()
        
        self.scroll_view = ScrollArea(self)
        self.edit_widget = EditWidget(self)
        self.scroll_view.setWidget(self.edit_widget)
        self.setCentralWidget(self.scroll_view)
        self.scroll_view.setAlignment(Qt.AlignCenter)
        
        self.settings_dock = QtGui.QDockWidget(self)
        self.settings_dock.setWidget(Settings(self.edit_widget))
        self.settings_dock.setWindowTitle('Settings')
        
        for item in (self.settings_dock,):
            self.addDockWidget(Qt.RightDockWidgetArea, item)

        self.setWindowTitle('pyspades map editor')
    
    def new_selected(self):
        self.map = VXLData()
        self.map_updated()
    
    def load_selected(self):
        name = QtGui.QFileDialog.getOpenFileName(self,
            'Select map file', filter = '*.vxl')[0]
        self.map = VXLData(open(name, 'rb'))
        self.map_updated()
    
    def map_updated(self):
        self.edit_widget.map_updated()
    
    def save_selected(self):
        name = QtGui.QFileDialog.getSaveFileName(self,
            'Select map file', filter = '*.vxl')[0]
        self.edit_widget.save_overview()
        open(name, 'wb').write(self.map.generate())

def main():
    app = QtGui.QApplication(sys.argv)
    editor = MapEditor()
    editor.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()