# Copyright (c) Mathias Kaerlev 2011-2012.

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

import struct
import sys
import os
sys.path.append('../../')

import math
import subprocess
from PySide import QtGui, QtCore
from PySide.QtCore import Qt
from PySide.QtGui import QPainter
from PySide.QtGui import QMessageBox
from PySide.QtGui import QImage

from pyspades.vxl import VXLData, get_color_tuple

WATER_COLOR = (64, 108, 129)
TRANSPARENT = QtGui.qRgba(0, 0, 0, 0)
TRANSPARENT_PACKED = struct.pack('I', TRANSPARENT)
FUCHSIA = QtGui.qRgba(255, 0, 255, 255)
FUCHSIA_PACKED = struct.pack('I', FUCHSIA)
IMAGE_SAVE_FILTER = 'Portable Network Graphics (*.png);;Windows Bitmap (*.bmp);;\
Joint Photographic Experts Group (*.jpg);;Joint Photographic Experts Group (*.jpeg);;\
Portable Pixmap (*.ppm);;Tagged Image File Format (*.tiff);;X11 Bitmap (*.xbm);;X11 Pixmap (*.xpm)'
IMAGE_OPEN_FILTER = 'All Formats (*.bmp *.gif *.jpg *.jpeg *.png *.pbm *.pgm *.ppm *.tiff *.xbm *.xpm);;' + \
    IMAGE_SAVE_FILTER
DEFAULT_PATH = '../../feature_server/maps'
DEFAULT_FILENAME = 'Untitled.vxl'
WATER_PEN = QtGui.QColor(*WATER_COLOR)

def translate_color(image, dest, src):
    for y in xrange(0, image.height()):
        line = image.scanLine(y)
        for x in xrange(0, image.width()):
            s = x * 4
            if line[s:s + 4] == src:
                line[s:s + 4] = dest

def interpret_colorkey(image):
    translate_color(image, TRANSPARENT_PACKED, FUCHSIA_PACKED)

def make_colorkey(image):
    new_image = image.copy(0, 0, image.width(), image.height())
    translate_color(new_image, FUCHSIA_PACKED, TRANSPARENT_PACKED)
    return new_image

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

class MapImage(QImage):
    dirty = False
    
    def __init__(self, data, *arg, **kw):
        self.data = data
        super(MapImage, self).__init__(data, *arg, **kw)
    
    def clear(self):
        self.dirty = True
        self.fill(0)
    
    def set_image(self, image):
        self.dirty = True
        self.fill(0)
        painter = QPainter(self)
        painter.drawImage(0, 0, image)

class EditWidget(QtGui.QWidget):
    scale = 1
    old_x = old_y = None
    image = None
    brush_size = 2.0
    settings = None
    freeze_image = None
    current_color = None
    x = y = 0
    z = None
    color_sampling = False
    
    def __init__(self, parent):
        self.main = parent
        super(EditWidget, self).__init__(parent)
        self.tool = Brush(self)
        self.update_scale()
        self.set_color(Qt.black)
        self.eraser = Qt.transparent
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
    
    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        if not self.color_sampling and modifiers & Qt.ShiftModifier:
            self.color_sampling = True
            self.main.app.setOverrideCursor(QtGui.QCursor(Qt.CrossCursor))
        if key == Qt.Key_Q or key == Qt.Key_Up:
            z = 0 if modifiers == Qt.AltModifier else self.z - 1 
            self.set_z(z)
        elif key == Qt.Key_A or key == Qt.Key_Down:
            z = 63 if modifiers == Qt.AltModifier else self.z + 1 
            self.set_z(z)
        elif key == Qt.Key_F:
            self.toggle_freeze()
        elif key in xrange(Qt.Key_1, Qt.Key_9 + 1):
            self.brush_size = key - Qt.Key_0
        elif key == Qt.Key_Plus:
            self.brush_size += 1
        elif key == Qt.Key_Minus:
            self.brush_size -= 1
        else:
            return super(EditWidget, self).keyPressEvent(event)
        self.brush_size = max(1, self.brush_size)
        self.settings.update_values()
    
    def set_brush_size(self, value):
        self.brush_size = max(1, value)
        self.settings.update_values()
    
    def keyReleaseEvent(self, event):
        modifiers = event.modifiers()
        if self.color_sampling and not modifiers & Qt.ShiftModifier:
            self.color_sampling = False
            self.main.app.restoreOverrideCursor()
    
    def toggle_freeze(self):
        if self.freeze_image is None:
            self.freeze_image = self.image
        else:
            self.freeze_image = None
            self.repaint()
    
    def update_scale(self):
        value = 512 * self.scale
        self.resize(value, value)
    
    def paintEvent(self, paintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.scale(self.scale, self.scale)
        painter.drawRect(0, 0, 511, 511)
        painter.drawImage(0, 0, self.image)
        if self.freeze_image is not None and self.freeze_image is not self.image:
            painter.setOpacity(0.3)
            painter.drawImage(0, 0, self.freeze_image)
    
    def set_color(self, color):
        self.color = color
    
    def mousePressEvent(self, event):
        self.old_x = self.old_y = None
        button = event.button()
        self.update_mouse_position(event)
        if button == Qt.LeftButton:
            if self.color_sampling:
                color = QtGui.QColor(self.image.pixel(self.x, self.y))
                self.set_color(color)
                return
            self.current_color = self.color
        elif button == Qt.RightButton:
            self.current_color = self.eraser
        else:
            self.current_color = None
            super(EditWidget, self).mousePressEvent(event)
            return
        self.draw_tool(event)
    
    def mouseMoveEvent(self, event):
        self.update_mouse_position(event)
        if self.current_color is not None:
            self.draw_tool(event)
        else:
            super(EditWidget, self).mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        self.current_color = None
    
    def update_mouse_position(self, event):
        value = 512.0 * self.scale
        x = int(event.x() / value * 512.0)
        y = int(event.y() / value * 512.0)
        x = max(0, min(511, x))
        y = max(0, min(511, y))
        self.x = x
        self.y = y
    
    def draw_tool(self, event):
        x = self.x
        y = self.y
        if x in xrange(512) and y in xrange(512):
            old_x = self.old_x or x
            old_y = self.old_y or y
            self.main.set_dirty()
            self.image.dirty = True
            painter = QPainter(self.image)
            self.tool.draw(painter, old_x, old_y, x, y)
            self.repaint()
        self.old_x = x
        self.old_y = y
    
    def wheelEvent(self, wheelEvent):
        if self.main.app.keyboardModifiers() & Qt.ControlModifier:
            self.set_brush_size(self.brush_size + wheelEvent.delta() / 120.0)
        else:
            delta = abs(wheelEvent.delta()) / 120.0 + 0.25
            if wheelEvent.delta() < 0.0:
                delta = 1.0 / delta
            self.scale *= delta
            self.update_scale()
            self.repaint()
    
    def clear(self):
        self.image.clear()
        self.repaint()
    
    def set_z(self, z):
        new_z = max(0, min(63, z))
        if self.z == new_z:
            return
        self.z = new_z
        self.image = self.main.layers[self.z]
        self.repaint()
        if self.settings is not None:
            self.settings.update_values()
    
    def set_image(self, image):
        self.image.set_image(image)
        self.repaint()
    
    def layers_updated(self):
        self.image = self.main.layers[self.z]
        self.repaint()
    
    def map_updated(self, map):
        self.freeze_image = None
        self.map = map
        self.set_z(63)
        self.layers_updated()
    
class ScrollArea(QtGui.QScrollArea):
    old_x = old_y = None
    settings = None
    
    def __init__(self, *arg, **kw):
        super(ScrollArea, self).__init__(*arg, **kw)
        self.setFocusPolicy(Qt.StrongFocus)
    
    def keyPressEvent(self, event):
        self.widget().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        self.widget().keyReleaseEvent(event)
    
    def wheelEvent(self, wheelEvent):
        self.widget().wheelEvent(wheelEvent)
    
    def mousePressEvent(self, event):
        self.old_x = self.start_x = event.x()
        self.old_y = self.start_y = event.y()
    
    def mouseMoveEvent(self, event):
        button = event.buttons()
        x = event.x()
        y = event.y()
        if button == Qt.MiddleButton:
            dx = -(x - self.old_x)
            dy = -(y - self.old_y)
            vertical_bar = self.verticalScrollBar()
            horizontal_bar = self.horizontalScrollBar()
            vertical_bar.setValue(vertical_bar.value() + dy)
            horizontal_bar.setValue(horizontal_bar.value() + dx)
            self.repaint()
        self.old_x = x
        self.old_y = y

class Tool(object):
    def __init__(self, editor):
        self.editor = editor
        self.initialize()
    
    def initialize(self):
        pass
    
    def draw(self, painter):
        pass

class Brush(Tool):
    def draw(self, painter, old_x, old_y, x, y):
        editor = self.editor
        color = editor.current_color
        if color is editor.eraser:
            painter.setCompositionMode(QPainter.CompositionMode_Source)
        pen = QtGui.QPen(color)
        pen.setWidth(editor.brush_size)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        if x == old_x and y == old_y:
            painter.drawPoint(x, y)
        else:
            painter.drawLine(old_x, old_y, x, y)

class Texture(Tool):
    image = None
    
    def initialize(self):
        name = QtGui.QFileDialog.getOpenFileName(self.editor,
            'Select texture file', filter = IMAGE_OPEN_FILTER)[0]
        if not name:
            return
        self.image = QImage(name)
    
    def draw(self, painter, old_x, old_y, x, y):
        if self.image is None:
            return
        painter.drawImage(
            x - self.image.width() / 2.0, 
            y - self.image.height() / 2.0, 
            self.image)

TOOLS = {
    'Brush' : Brush,
    'Texture' : Texture
}

class Settings(QtGui.QWidget):
    def __init__(self, parent, *arg, **kw):
        self.editor = parent.edit_widget
        self.scroll_view = parent.scroll_view
        for widget in (self.editor, self.scroll_view):
            widget.settings = self
        super(Settings, self).__init__(*arg, **kw)
        layout = QtGui.QVBoxLayout(self)
        
        self.tool = LabeledWidget('Tool', QtGui.QListWidget())
        self.tool.widget.addItems(TOOLS.keys())
        self.tool.widget.setCurrentRow(0)
        self.tool.widget.itemClicked.connect(self.tool_changed)
        
        layout.addWidget(self.tool)
        
        self.z_value = LabeledSpinBox('Current Z')
        self.z_value.spinbox.setRange(0, 63)
        self.z_value.spinbox.valueChanged.connect(self.set_z)
        layout.addWidget(self.z_value)

        self.brush_size = LabeledSpinBox('Brush size')
        self.brush_size.spinbox.valueChanged.connect(self.set_brush_size)
        self.brush_size.spinbox.setRange(0, 999)
        layout.addWidget(self.brush_size)
        
        self.freeze_button = QtGui.QPushButton('Toggle freeze')
        self.freeze_button.clicked.connect(self.freeze_image)
        layout.addWidget(self.freeze_button)
        
        self.color_button = QtGui.QPushButton('Set color')
        self.color_button.clicked.connect(self.set_color)
        layout.addWidget(self.color_button)
        
        self.update_values()
    
    def tool_changed(self, value):
        self.editor.tool = TOOLS[value.text()](self.editor)
    
    def set_brush_size(self):
        self.editor.brush_size = self.brush_size.spinbox.value()
    
    def set_z(self):
        self.editor.set_z(63 - self.z_value.spinbox.value())
    
    def freeze_image(self):
        self.editor.toggle_freeze()
    
    def set_color(self):
        color = QtGui.QColorDialog.getColor(
            Qt.white, self, 'Select a color',
            QtGui.QColorDialog.ShowAlphaChannel
        )
        self.editor.set_color(color)
    
    def update_values(self):
        editor = self.editor
        self.z_value.spinbox.setValue(63 - editor.z)
        self.brush_size.spinbox.setValue(editor.brush_size)
    
    def keyPressEvent(self, event):
        self.editor.keyPressEvent(event)

    def keyReleaseEvent(self, event):
        self.editor.keyReleaseEvent(event)

def progress_dialog(parent, minn, maxn, text, can_abort = True):
    progress = QtGui.QProgressDialog(parent)
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimum(minn)
    progress.setMaximum(maxn)
    progress.setLabelText(text)
    if can_abort:
        progress.setCancelButtonText('Abort')
    else:
        progress.setCancelButton(None)
    progress.show()
    return progress

class MapEditor(QtGui.QMainWindow):
    path = None
    filename = None
    voxed_filename = None
    layers = None
    dirty = False
    
    def __init__(self, app, *arg, **kw):
        super(MapEditor, self).__init__(*arg, **kw)
        
        self.app = app
        self.app.setApplicationName('pyspades map editor')
        self.setWindowTitle('pyspades map editor')
        self.clipboard = app.clipboard()
        
        menu = self.menuBar()
        
        self.file = menu.addMenu('&File')
        
        self.new_action = QtGui.QAction('&New', self,
            shortcut = QtGui.QKeySequence('Ctrl+N'), 
            triggered = self.new_selected)
        self.file.addAction(self.new_action)
        
        self.open_action = QtGui.QAction('&Open...', self,
            shortcut = QtGui.QKeySequence('Ctrl+O'), 
            triggered = self.open_selected)
        self.file.addAction(self.open_action)
        
        self.file.addSeparator()
        
        self.save_action = QtGui.QAction('&Save', self, 
            shortcut = QtGui.QKeySequence.Save, triggered = self.save_selected)
        self.save_action.setEnabled(False)
        self.file.addAction(self.save_action)
        
        self.save_as_action = QtGui.QAction('Save &As...', self, 
            shortcut = QtGui.QKeySequence('Ctrl+Shift+S'), 
            triggered = self.save_as_selected)
        self.file.addAction(self.save_as_action)
        
        self.file.addSeparator()
        
        self.import_menu = self.file.addMenu('&Import')
        
        self.import_image_sequence_menu = QtGui.QAction('Image &sequence...', self, 
            triggered = self.import_image_sequence)
        self.import_menu.addAction(self.import_image_sequence_menu)
        
        self.export = self.file.addMenu('&Export')
        
        self.color_map = QtGui.QAction('&Colormap...', self, 
            triggered = self.export_color_map)
        self.export.addAction(self.color_map)
        
        self.height_map = QtGui.QAction('&Heightmap...', self, 
            triggered = self.export_height_map)
        self.export.addAction(self.height_map)
        
        self.export_image_sequence_menu = QtGui.QAction('Image &sequence...', self, 
            triggered = self.export_image_sequence)
        self.export.addAction(self.export_image_sequence_menu)
        
        self.file.addSeparator()
        
        self.voxed_action = QtGui.QAction('Open in &VOXED', 
            self, shortcut = QtGui.QKeySequence('F5'), triggered = self.open_voxed)
        self.file.addAction(self.voxed_action)
        
        self.file.addSeparator()
        
        self.quit_action = QtGui.QAction('E&xit', 
            self, shortcut = QtGui.QKeySequence('Ctrl+Q'), 
            triggered = self.quit)
        self.file.addAction(self.quit_action)
        
        self.edit = menu.addMenu('&Edit')
        
        self.copy_action = QtGui.QAction('C&opy', self,
            shortcut = QtGui.QKeySequence.Copy, triggered = self.copy_selected)
        self.edit.addAction(self.copy_action)
        
        self.paste_action = QtGui.QAction('P&aste', self,
            shortcut = QtGui.QKeySequence.Paste, 
            triggered = self.paste_selected)
        self.edit.addAction(self.paste_action)
        
        self.copy_action_external = QtGui.QAction('&Copy External', self,
            shortcut = QtGui.QKeySequence('Ctrl+Shift+C'),
            triggered = self.copy_external_selected)
        self.edit.addAction(self.copy_action_external)
        
        self.paste_action_external = QtGui.QAction('&Paste External', self,
            shortcut = QtGui.QKeySequence('Ctrl+Shift+V'), 
            triggered = self.paste_external_selected)
        self.edit.addAction(self.paste_action_external)
        
        self.clear_action = QtGui.QAction('Cl&ear', self,
            shortcut = QtGui.QKeySequence.Delete, 
            triggered = self.clear_selected)
        self.edit.addAction(self.clear_action)
        
        self.transform = menu.addMenu('&Transform')
        
        self.shift_up_action = QtGui.QAction('Shift layers &upward', self,
            shortcut = QtGui.QKeySequence('Ctrl+Shift+Q'),
            triggered = self.shift_up)
        self.transform.addAction(self.shift_up_action)
        
        self.shift_down_action = QtGui.QAction('Shift layers &downward', self,
            shortcut = QtGui.QKeySequence('Ctrl+Shift+A'),
            triggered = self.shift_down)
        self.transform.addAction(self.shift_down_action)
        
        self.transform.addSeparator()
        
        self.mirror_horizontal_action = QtGui.QAction('Mirror &horizontal', self,
            triggered = self.mirror_horizontal)
        self.transform.addAction(self.mirror_horizontal_action)
        
        self.mirror_vertical_action = QtGui.QAction('Mirror &vertical', self,
            triggered = self.mirror_vertical)
        self.transform.addAction(self.mirror_vertical_action)
        
        self.mirror_both_action = QtGui.QAction('Mirror &both', self,
            triggered = self.mirror_both)
        self.transform.addAction(self.mirror_both_action)
        
        self.mirror_z_action = QtGui.QAction('Mirror &Z', self,
            triggered = self.mirror_z)
        self.transform.addAction(self.mirror_z_action)
        
        self.transform.addSeparator()
        
        self.rotate_90_CW_action = QtGui.QAction('Rotate &90\xb0 CW', self,
            triggered = self.rotate_90_CW)
        self.transform.addAction(self.rotate_90_CW_action)
        
        self.rotate_90_CCW_action = QtGui.QAction('Rotate 9&0\xb0 CCW', self,
            triggered = self.rotate_90_CCW)
        self.transform.addAction(self.rotate_90_CCW_action)
        
        self.rotate_180_action = QtGui.QAction('Rotate &180\xb0', self,
            triggered = self.rotate_180)
        self.transform.addAction(self.rotate_180_action)
        
        self.heightmap = menu.addMenu('&Heightmap')
        
        self.additive_heightmap_action = QtGui.QAction('&Additive...', self,
            triggered = self.generate_heightmap)
        self.heightmap.addAction(self.additive_heightmap_action)
        
        self.subtractive_heightmap_action = QtGui.QAction('&Subtractive...', self,
            triggered = self.subtractive_heightmap)
        self.heightmap.addAction(self.subtractive_heightmap_action)
        
        self.scroll_view = ScrollArea(self)
        self.edit_widget = EditWidget(self)
        self.scroll_view.setWidget(self.edit_widget)
        self.setCentralWidget(self.scroll_view)
        self.scroll_view.setAlignment(Qt.AlignCenter)
        
        self.apply_default()
        self.path = DEFAULT_PATH
        self.filename = None
        
        self.settings_dock = QtGui.QDockWidget(self)
        self.settings_dock.setWidget(Settings(self))
        self.settings_dock.setWindowTitle('Settings')
        
        for item in (self.settings_dock,):
            self.addDockWidget(Qt.RightDockWidgetArea, item)
    
    def set_dirty(self, value = True):
        if self.dirty == value:
            return
        self.dirty = value
        self.save_action.setEnabled(value)
    
    def new_selected(self):
        msgBox = QMessageBox()
        msgBox.setText("Do you want to discard your changes?")
        msgBox.setStandardButtons(QMessageBox.Discard | QMessageBox.Cancel)
        msgBox.setDefaultButton(QMessageBox.Cancel)
        ret = msgBox.exec_()
        if ret == QMessageBox.Cancel:
            return
        self.filename = None
        self.apply_default()
    
    def open_selected(self):
        name = QtGui.QFileDialog.getOpenFileName(self,
            'Open', self.path, filter = '*.vxl')[0]
        if not name:
            return
        self.filename = name
        self.map = VXLData(open(name, 'rb'))
        self.slice_map()
        self.edit_widget.map_updated(self.map)
    
    def apply_default(self):
        self.map = VXLData()
        self.slice_map(show_dialog = False)
        bottom_layer = self.layers[63]
        bottom_layer.fill(WATER_PEN.rgba())
        bottom_layer.dirty = True
        self.set_dirty(False)
        self.edit_widget.map_updated(self.map)
    
    def slice_map(self, show_dialog = True):
        self.layers = []
        if show_dialog:
            progress = progress_dialog(self.edit_widget, 0, 63, 'Slicing...', can_abort = False)
        for z in xrange(0, 64):
            if show_dialog:
                progress.setValue(z)
            self.layers.append(MapImage(self.map.get_overview(z), 512, 512,
                QImage.Format_ARGB32))
    
    def save_selected(self):
        if self.filename is None:
            return self.save_as_selected()
        name = os.path.join(self.path, self.filename)
        self.save(name)
        return name
    
    def save_as_selected(self):
        path = os.path.join(self.path, self.filename or DEFAULT_FILENAME)
        name = QtGui.QFileDialog.getSaveFileName(self,
            'Save As', path, filter = '*.vxl')[0]
        if not name:
            return
        self.path, self.filename = os.path.split(name)
        self.save(name)
        return name
    
    def save(self, filename):
        for z in xrange(0, 64):
            layer = self.layers[z]
            if layer.dirty:
                self.map.set_overview(layer.data, z)
                layer.dirty = False
        open(filename, 'wb').write(self.map.generate())
        self.set_dirty(False)
    
    def open_voxed(self):
        name = self.save_selected()
        if not name:
            return
        if self.voxed_filename is None:
            default_path = 'C:\\Ace of Spades\\voxed.exe'
            if os.path.exists(default_path):
                self.voxed_filename = default_path
            else:
                exename = QtGui.QFileDialog.getOpenFileName(self,
                    'Select VOXED.EXE', filter = '*.exe')[0]
                if not exename:
                    return
                self.voxed_filename = exename
        subprocess.call([self.voxed_filename, name])
    
    def import_image_sequence(self):
        name = QtGui.QFileDialog.getOpenFileName(self,
            'Import image sequence (select any file from the sequence)', filter = IMAGE_OPEN_FILTER)[0]
        if not name:
            return
        root, ext = os.path.splitext(name)
        head, tail = os.path.split(root)
        path = os.path.join(root, head, tail[:-2])
        old_z = self.edit_widget.z
        progress = progress_dialog(self.edit_widget, 0, 63, 'Importing images...')
        for z in xrange(0, 64):
            if progress.wasCanceled():
                break
            progress.setValue(z)
            image = QImage(path + format(z, '02d') + ext)
            if not image:
                continue
            interpret_colorkey(image)
            self.layers[63 - z].set_image(image)
        self.edit_widget.repaint()
    
    def export_color_map(self):
        name = QtGui.QFileDialog.getSaveFileName(self,
            'Export Colormap', filter = IMAGE_SAVE_FILTER)[0]
        if not name:
            return
        color_image = QImage(512, 512, QImage.Format_ARGB32)
        color_lines = []
        height_found = []
        for y in xrange(0, 512):
            color_lines.append(color_image.scanLine(y))
            height_found.append([])
            for x in xrange(0, 512):
                height_found[y].append(False)
        progress = progress_dialog(self.edit_widget, 0, 63, 'Exporting Colormap...')
        for z in xrange(0, 64):
            if progress.wasCanceled():
                break
            progress.setValue(z)
            image = self.layers[z]
            for y in xrange(0, 512):
                image_line = image.scanLine(y)
                color_line = color_lines[y]
                for x in xrange(0, 512):
                    if height_found[y][x] is False:
                        s = x * 4
                        image_pixel = image_line[s:s + 4]
                        if image_pixel != TRANSPARENT_PACKED:
                            height_found[y][x] = True
                            color_line[s:s + 4] = image_pixel
        color_image.save(name)
    
    def export_height_map(self):
        name = QtGui.QFileDialog.getSaveFileName(self,
            'Export Heightmap', filter = IMAGE_SAVE_FILTER)[0]
        if not name:
            return
        height_packed = []
        for z in xrange(0, 64):
            height = (63 - z) * 4
            height_packed.append(struct.pack('I', QtGui.qRgba(height, height, height, 255)))
        height_image = QImage(512, 512, QImage.Format_ARGB32)
        height_lines = []
        height_found = []
        for y in xrange(0, 512):
            height_lines.append(height_image.scanLine(y))
            height_found.append([])
            for x in xrange(0, 512):
                height_found[y].append(False)
        progress = progress_dialog(self.edit_widget, 0, 63, 'Exporting Heightmap...')
        for z in xrange(0, 64):
            if progress.wasCanceled():
                break
            progress.setValue(z)
            packed_value = height_packed[z]
            image = self.layers[z]
            for y in xrange(0, 512):
                image_line = image.scanLine(y)
                height_line = height_lines[y]
                for x in xrange(0, 512):
                    if height_found[y][x] is False:
                        s = x * 4
                        if image_line[s:s + 4] != TRANSPARENT_PACKED:
                            height_found[y][x] = True
                            height_line[s:s + 4] = packed_value
        height_image.save(name)
    
    def export_image_sequence(self):
        name = QtGui.QFileDialog.getSaveFileName(self,
            'Export image sequence (select base filename)', filter = IMAGE_SAVE_FILTER)[0]
        if not name:
            return
        root, ext = os.path.splitext(name)
        progress = progress_dialog(self.edit_widget, 0, 63, 'Exporting images...')
        for z in xrange(0, 64):
            if progress.wasCanceled():
                break
            progress.setValue(z)
            image = self.layers[63 - z]
            new_image = make_colorkey(image)
            new_image.save(root + format(z, '02d') + ext)
    
    def copy_selected(self):
        self.clipboard.setImage(self.edit_widget.image)
    
    def paste_selected(self):
        image = self.clipboard.image()
        if not image:
            return
        self.edit_widget.set_image(image)
        self.set_dirty()
    
    def copy_external_selected(self):
        image = self.edit_widget.image
        new_image = make_colorkey(image)
        self.clipboard.setImage(new_image)
    
    def paste_external_selected(self):
        image = self.clipboard.image()
        if not image:
            return
        image = image.convertToFormat(QImage.Format_ARGB32)
        interpret_colorkey(image)
        self.edit_widget.set_image(image)
        self.set_dirty()
    
    def mirror(self, hor, ver):
        progress = progress_dialog(self.edit_widget, 0, 63, 'Mirroring...')
        for z in xrange(0, 64):
            if progress.wasCanceled():
                break
            progress.setValue(z)
            layer = self.layers[z]
            layer.set_image(layer.mirrored(hor, ver))
        self.edit_widget.repaint()
        self.set_dirty()
    
    def mirror_horizontal(self):
        self.mirror(True, False)
    
    def mirror_vertical(self):
        self.mirror(False, True)
    
    def mirror_both(self):
        self.mirror(True, True)
    
    def mirror_z(self):
        self.layers.reverse()
        for layer in self.layers:
            layer.dirty = True
        self.edit_widget.layers_updated()
        self.set_dirty()
    
    def rotate(self, angle):
        progress = progress_dialog(self.edit_widget, 0, 63, 'Rotating...')
        transform = QtGui.QTransform()
        transform.rotate(angle)
        for z in xrange(0, 64):
            if progress.wasCanceled():
                break
            progress.setValue(z)
            layer = self.layers[z]
            layer.set_image(layer.transformed(transform))
        self.edit_widget.repaint()
        self.set_dirty()
    
    def rotate_90_CW(self):
        self.rotate(90)

    def rotate_90_CCW(self):
        self.rotate(-90)
    
    def rotate_180(self):
        self.rotate(180)
    
    def cycle_layers(self, n):
        self.layers = self.layers[n:] + self.layers[:n]
        for layer in self.layers:
            layer.dirty = True
        self.edit_widget.layers_updated()
        self.set_dirty()
    
    def shift_up(self):
        self.cycle_layers(-1)
    
    def shift_down(self):
        self.cycle_layers(1)
    
    def clear_selected(self):
        self.edit_widget.clear()
        self.set_dirty()
    
    def get_height(self, color):
        return int(math.floor((float(QtGui.qRed(color)) + float(QtGui.qGreen(color)) + 
                    float(QtGui.qBlue(color)))/12.0))
    
    def generate_heightmap(self, delete = False):
        h_name = QtGui.QFileDialog.getOpenFileName(self,
            'Select heightmap file', filter = IMAGE_OPEN_FILTER)[0]
        if not h_name:
            return
        h_image = QImage(h_name)
        if not delete:
            c_name = QtGui.QFileDialog.getOpenFileName(self,
                'Select colormap file', filter = IMAGE_OPEN_FILTER)[0]
            if not c_name:
                return
            c_image = QImage(c_name)
        height_values = []
        color_lines = []
        for y in xrange(0, 512):
            height_values.append([])
            height_line = h_image.scanLine(y)
            if not delete:
                color_lines.append(c_image.scanLine(y))
            for x in xrange(0,512):
                height_values[y].append(self.get_height(struct.unpack('I', height_line[x * 4:x * 4 + 4])[0]))
        progress = progress_dialog(self.edit_widget, 0, 63, 'Generating from heightmap...')
        for z in xrange(0, 64):
            if progress.wasCanceled():
                break
            progress.setValue(z)
            if z == 0 and delete:
                continue
            image = self.layers[63 - z]
            for y in xrange(0, 512):
                image_line = image.scanLine(y)
                if not delete:
                    color_line = color_lines[y]
                for x in xrange(0, 512):
                    if z <= height_values[y][x]:
                        s = x * 4
                        if not delete:
                            image_line[s:s + 4] = color_line[s:s + 4]
                        else:
                            image_line[s:s + 4] = TRANSPARENT_PACKED
    
    def subtractive_heightmap(self):
        return self.generate_heightmap(True)
    
    def quit(self):
        if self.dirty:
            text = ('Save changes to ' + (self.filename or DEFAULT_FILENAME) +
                ' before closing?')
            reply = QMessageBox.warning(self, self.app.applicationName(), text,
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                if not self.save_selected():
                    return
            elif reply == QMessageBox.Cancel:
                return
        self.app.exit()

def main():
    app = QtGui.QApplication(sys.argv)
    editor = MapEditor(app)
    editor.show()
    editor.showMaximized()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()