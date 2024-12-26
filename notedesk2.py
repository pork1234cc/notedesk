import sys
import os
import json
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QVBoxLayout, QHBoxLayout, QPushButton, 
    QWidget, QLineEdit, QFrame, QLabel, QScrollArea, QDialog, QToolBar, QColorDialog, 
    QMenu, QMessageBox, QSlider, QFileDialog
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QByteArray, QMimeData, QUrl
from PyQt5.QtGui import (
    QIcon, QFont, QTextCharFormat, QColor, QDrag, QCursor, QPixmap, QTextDocument, QTextImageFormat
)

class NoteData:
    """便签数据管理类"""
    def __init__(self):
        self.data_dir = os.path.join(os.path.expanduser('~'), 'NoteDesk')
        self.data_file = os.path.join(self.data_dir, 'notes.json')
        self.images_dir = os.path.join(self.data_dir, 'images')  # 添加图片目录
        self.ensure_data_dir()
        self.notes = self.load_notes()
        self.next_id = self.calculate_next_id()

    def calculate_next_id(self):
        # 计算下一个可用的ID
        return max([note['id'] for note in self.notes], default=-1) + 1

    def ensure_data_dir(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        if not os.path.exists(self.images_dir):  # 创建图片目录
            os.makedirs(self.images_dir)

    def load_notes(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    notes = json.load(f)
                    # 确保每个便签都有必要的字段
                    for note in notes:
                        if 'is_deleted' not in note:
                            note['is_deleted'] = False
                        if 'is_pinned' not in note:
                            note['is_pinned'] = False
                    return notes
            except Exception as e:
                print(f"Error loading notes: {e}")
                return []
        return []

    def get_active_notes(self):
        return [note for note in self.notes if not note.get('is_deleted', False)]

    def save_notes(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.notes, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving notes: {e}")
            return False

    def add_note(self, title, content, timestamp):
        note = {
            'id': self.next_id,
            'title': title,
            'content': content,
            'timestamp': timestamp,
            'is_pinned': False,
            'is_deleted': False,
            'create_time': datetime.now().timestamp()
        }
        self.notes.append(note)
        self.next_id += 1
        self.save_notes()
        return note

    def update_note(self, note_id, title, content):
        for note in self.notes:
            if note['id'] == note_id and not note.get('is_deleted', False):
                note['title'] = title
                note['content'] = content
                note['timestamp'] = datetime.now().strftime("%H:%M")
                return self.save_notes()
        return False

    def search_notes(self, query):
        query = query.lower()
        return [note for note in self.notes 
                if not note.get('is_deleted', False) and
                (query in note['title'].lower() or 
                 query in note['content'].lower())]

    def delete_note(self, note_id):
        for note in self.notes:
            if note['id'] == note_id:
                note['is_deleted'] = True
                return self.save_notes()
        return False

    def update_note_pin_status(self, note_id, is_pinned):
        for note in self.notes:
            if note['id'] == note_id and not note.get('is_deleted', False):
                note['is_pinned'] = is_pinned
                note['pin_time'] = datetime.now().timestamp() if is_pinned else None
                return self.save_notes()
        return False

    def get_notes_ordered(self):
        # 获取未删除的便签
        active_notes = [note for note in self.notes if not note.get('is_deleted', False)]
        
        # 分离置顶和非置顶便签
        pinned_notes = [note for note in active_notes if note.get('is_pinned', False)]
        unpinned_notes = [note for note in active_notes if not note.get('is_pinned', False)]
        
        # 置顶便签按置顶时间排序（新的在最前面）
        pinned_notes.sort(key=lambda x: x.get('pin_time', 0), reverse=True)
        # 非置顶便签按创建时间排序（新的在最前面）
        unpinned_notes.sort(key=lambda x: x.get('create_time', 0), reverse=True)
        
        # 返回排序后的便签列表（置顶的在最前）
        return pinned_notes + unpinned_notes

    def reorder_notes(self, source_id, target_id):
        # 只处理未删除的便签
        active_notes = [note for note in self.notes if not note.get('is_deleted', False)]
        source_note = None
        source_index = -1
        target_index = -1
        
        for i, note in enumerate(active_notes):
            if note['id'] == source_id:
                source_note = note
                source_index = i
            elif note['id'] == target_id:
                target_index = i
                
        if source_note and source_index != -1 and target_index != -1:
            active_notes.pop(source_index)
            active_notes.insert(target_index, source_note)
            # 更新主列表中的顺序
            self.notes = [note for note in self.notes if note.get('is_deleted', False)] + active_notes
            self.save_notes()

    def update_note_color(self, note_id, color):
        try:
            for note in self.notes:
                if note['id'] == note_id and not note.get('is_deleted', False):
                    note['background_color'] = color
                    with open(self.data_file, 'w', encoding='utf-8') as f:
                        json.dump(self.notes, f, ensure_ascii=False, indent=2)
                    print(f"Successfully saved color {color} for note {note_id}")
                    return True
            return False
        except Exception as e:
            print(f"Error saving note color: {e}")
            return False

class NoteEditDialog(QDialog):
    def __init__(self, title, content, parent=None):
        super().__init__(parent)
        # 设置最小尺寸
        self.setMinimumSize(250, 450)
        # 设置窗口样式，允许调整大小
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setCursor(Qt.ArrowCursor)
        
        # 初始化拖拽相关变量
        self.dragging = False
        self.resizing = False
        self.drag_position = None
        self.resize_edge = None
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 顶部标题栏
        title_bar = QWidget()
        title_bar.setStyleSheet("""
            QWidget {
                background-color: #f8f8f8;
                border-bottom: 1px solid #ddd;
            }
            QPushButton {
                border: none;
                padding: 8px 12px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e81123;
                color: white;
            }
        """)
        title_bar.setFixedHeight(40)
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 0, 0)
        
        # 标题文本
        title_label = QLabel("久久便签")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        title_layout.addWidget(title_label)
        
        # 关闭按钮
        close_button = QPushButton("×")
        close_button.setFixedSize(40, 40)
        close_button.clicked.connect(self.reject)
        close_button.setCursor(Qt.ArrowCursor)
        title_layout.addWidget(close_button)
        
        main_layout.addWidget(title_bar)
        
        # 内容区域布局
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)
        
        # 标题编辑
        self.title_edit = QLineEdit(title)
        self.title_edit.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                font-size: 14px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
        """)
        self.title_edit.setPlaceholderText("输入标题...")
        content_layout.addWidget(self.title_edit)
        
        # 文本编辑区
        self.editor = QTextEdit()
        self.editor.setHtml(content)
        self.editor.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                background-color: white;
            }
        """)
        # 存储图片路径映射
        self.image_paths = {}
        # 连接双击事件
        self.editor.mouseDoubleClickEvent = self.handle_double_click
        content_layout.addWidget(self.editor)
        
        # 底部工具栏
        toolbar = QToolBar()
        toolbar.setStyleSheet("""
            QToolBar {
                background: #f8f8f8;
                border-top: 1px solid #ddd;
                padding: 5px;
            }
            QPushButton {
                border: none;
                padding: 5px 10px;
                margin: 0 2px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        
        # 添加编辑功能按钮
        bold_btn = QPushButton("B")
        bold_btn.setFont(QFont("Arial", 10, QFont.Bold))
        bold_btn.clicked.connect(self.toggle_bold)
        bold_btn.setCursor(Qt.ArrowCursor)
        
        italic_btn = QPushButton("I")
        italic_btn.setFont(QFont("Arial", 10))
        italic_btn.setStyleSheet("font-style: italic;")
        italic_btn.clicked.connect(self.toggle_italic)
        italic_btn.setCursor(Qt.ArrowCursor)
        
        underline_btn = QPushButton("U")
        underline_btn.setFont(QFont("Arial", 10))
        underline_btn.setStyleSheet("text-decoration: underline;")
        underline_btn.clicked.connect(self.toggle_underline)
        underline_btn.setCursor(Qt.ArrowCursor)
        
        color_btn = QPushButton("颜色")
        color_btn.clicked.connect(self.change_color)
        color_btn.setCursor(Qt.ArrowCursor)
        
        # 添加图片按钮
        image_btn = QPushButton("图片")
        image_btn.clicked.connect(self.insert_image)
        image_btn.setCursor(Qt.ArrowCursor)
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.accept)
        save_btn.setCursor(Qt.ArrowCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        
        toolbar.addWidget(bold_btn)
        toolbar.addWidget(italic_btn)
        toolbar.addWidget(underline_btn)
        toolbar.addWidget(color_btn)
        toolbar.addWidget(image_btn)  # 添加图片按钮到工具栏
        toolbar.addWidget(save_btn)
        
        content_layout.addWidget(toolbar)
        
        # 将内容布局添加到主布局
        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget)
        
        self.setLayout(main_layout)
        
    def insert_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        if file_name:
            # 生成唯一的图片文件名
            image_name = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{os.path.splitext(file_name)[1]}"
            # 构建目标路径
            target_path = os.path.join(self.parent().note_data.images_dir, image_name)
            
            try:
                # 复制图片到应用数据目录
                pixmap = QPixmap(file_name)
                pixmap.save(target_path)
                
                # 创建缩略图
                scaled_pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                # 将图片插入到文本编辑器中
                cursor = self.editor.textCursor()
                cursor.insertHtml(f'<div style="text-align: center;">')
                
                # 创建图片格式
                image_format = QTextImageFormat()
                image_format.setName(target_path)  # 使用新的路径
                image_format.setWidth(scaled_pixmap.width())
                image_format.setHeight(scaled_pixmap.height())
                
                # 将图片资源添加到文档
                self.editor.document().addResource(
                    QTextDocument.ImageResource,
                    QUrl(f"file://{target_path}"),
                    scaled_pixmap.toImage()
                )
                
                # 插入图片
                cursor.insertImage(image_format)
                cursor.insertHtml('</div><br>')
                
            except Exception as e:
                QMessageBox.warning(self, "错误", f"保存图片时出错：{str(e)}")

    def handle_double_click(self, event):
        cursor = self.editor.cursorForPosition(event.pos())
        char_format = cursor.charFormat()
        
        if char_format.isImageFormat():
            # 获取图片路径
            image_path = char_format.toImageFormat().name()
            
            # 检查图片路径是否存在
            if os.path.exists(image_path):
                # 创建图片查看器窗口
                viewer = ImageViewer(image_path)
                viewer.exec_()
            else:
                QMessageBox.warning(self, "错误", "找不到图片文件，可能已被删除或移动")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 检查是否在窗口边缘（调整大小区域）
            edge_size = 5
            pos = event.pos()
            rect = self.rect()
            
            # 检查是否在边缘
            at_left = pos.x() <= edge_size
            at_right = pos.x() >= rect.width() - edge_size
            at_top = pos.y() <= edge_size
            at_bottom = pos.y() >= rect.height() - edge_size
            
            if at_left or at_right or at_top or at_bottom:
                self.resizing = True
                self.resize_start_pos = event.globalPos()
                self.resize_start_geometry = self.geometry()
                
                # 确定调整方向
                if at_left:
                    self.resize_edge = 'left'
                elif at_right:
                    self.resize_edge = 'right'
                elif at_top:
                    self.resize_edge = 'top'
                elif at_bottom:
                    self.resize_edge = 'bottom'
            else:
                # 如果不在边缘，则为拖动窗口
                self.dragging = True
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.resizing and event.buttons() == Qt.LeftButton:
            # 调整窗口大小
            diff = event.globalPos() - self.resize_start_pos
            new_geometry = self.resize_start_geometry
            
            if self.resize_edge == 'left':
                new_width = new_geometry.width() - diff.x()
                if new_width >= self.minimumWidth():
                    new_geometry.setLeft(new_geometry.left() + diff.x())
            elif self.resize_edge == 'right':
                new_width = new_geometry.width() + (event.globalPos().x() - self.resize_start_pos.x())
                if new_width >= self.minimumWidth():
                    new_geometry.setWidth(new_width)
            elif self.resize_edge == 'top':
                new_height = new_geometry.height() - diff.y()
                if new_height >= self.minimumHeight():
                    new_geometry.setTop(new_geometry.top() + diff.y())
            elif self.resize_edge == 'bottom':
                new_height = new_geometry.height() + (event.globalPos().y() - self.resize_start_pos.y())
                if new_height >= self.minimumHeight():
                    new_geometry.setHeight(new_height)
            
            self.setGeometry(new_geometry)
            self.resize_start_pos = event.globalPos()
            
        elif self.dragging and event.buttons() == Qt.LeftButton:
            # 移动窗口
            self.move(event.globalPos() - self.drag_position)

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.resizing = False
        self.resize_edge = None
        self.setCursor(Qt.ArrowCursor)

    def enterEvent(self, event):
        self.updateCursor(event.pos())

    def leaveEvent(self, event):
        self.setCursor(Qt.ArrowCursor)

    def updateCursor(self, pos):
        edge_size = 5
        rect = self.rect()
        
        # 根据鼠标位置设置光标形状
        if pos.x() <= edge_size or pos.x() >= rect.width() - edge_size:
            self.setCursor(Qt.SizeHorCursor)
        elif pos.y() <= edge_size or pos.y() >= rect.height() - edge_size:
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def toggle_bold(self):
        fmt = self.editor.currentCharFormat()
        fmt.setFontWeight(QFont.Bold if fmt.fontWeight() != QFont.Bold else QFont.Normal)
        self.editor.mergeCurrentCharFormat(fmt)

    def toggle_italic(self):
        fmt = self.editor.currentCharFormat()
        fmt.setFontItalic(not fmt.fontItalic())
        self.editor.mergeCurrentCharFormat(fmt)

    def toggle_underline(self):
        fmt = self.editor.currentCharFormat()
        fmt.setFontUnderline(not fmt.fontUnderline())
        self.editor.mergeCurrentCharFormat(fmt)

    def change_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            fmt = self.editor.currentCharFormat()
            fmt.setForeground(color)
            self.editor.mergeCurrentCharFormat(fmt)

    def get_content(self):
        return self.editor.toHtml()

    def get_title(self):
        return self.title_edit.text()

class NoteCard(QFrame):
    note_clicked = pyqtSignal(int, str, str)  # id, title, content
    note_deleted = pyqtSignal(int)  # 添加删除信号
    note_pinned = pyqtSignal(int, bool)  # 添加置顶信号

    def __init__(self, note_id, title, content, timestamp, parent=None):
        super().__init__(parent)
        self.note_id = note_id
        self.title = title
        self.content = content
        self.is_pinned = False
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        self.setCursor(Qt.ArrowCursor)
        
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 顶部布局（包含置顶图标、标题和时间）
        top_layout = QHBoxLayout()
        
        # 置顶图标
        self.pin_label = QLabel("📌")  # 使用UTF-8编码的图标
        self.pin_label.setStyleSheet("color: #666;")
        self.pin_label.hide()
        top_layout.addWidget(self.pin_label)
        
        # 标题
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))
        top_layout.addWidget(self.title_label)
        
        # 添加弹性空间
        top_layout.addStretch()
        
        # 时间戳
        time_label = QLabel(timestamp)
        time_label.setStyleSheet("color: gray; font-size: 10px;")
        top_layout.addWidget(time_label)
        
        layout.addLayout(top_layout)
        
        # 内容限制高度
        self.content_label = QLabel(content)
        self.content_label.setWordWrap(True)
        self.content_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 11px;
                padding: 5px 0;
            }
        """)
        # 设置固定高度
        self.content_label.setFixedHeight(40)
        layout.addWidget(self.content_label)
        
        self.setLayout(layout)
        
        # 设��便签卡片的固定高度
        self.setFixedHeight(100)
        
        # 设置基本样式
        self.setStyleSheet("""
            NoteCard {
                background-color: #e8f4f8;
                border-radius: 10px;
                margin: 5px;
                padding: 10px;
            }
            NoteCard:hover {
                background-color: #d8edf5;
            }
        """)

    def mouseDoubleClickEvent(self, event):
        self.note_clicked.emit(self.note_id, self.title, self.content)

    def show_context_menu(self, position):
        menu = QMenu(self)
        
        edit_action = menu.addAction("编辑")
        delete_action = menu.addAction("删除")
        pin_action = menu.addAction("取消置顶" if self.is_pinned else "置顶")
        
        action = menu.exec_(self.mapToGlobal(position))
        
        if action == edit_action:
            self.note_clicked.emit(self.note_id, self.title, self.content)
        elif action == delete_action:
            reply = QMessageBox.question(self, '确认删除', 
                                       '确定要删除这个便签吗？',
                                       QMessageBox.Yes | QMessageBox.No,
                                       QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.note_deleted.emit(self.note_id)
        elif action == pin_action:
            self.is_pinned = not self.is_pinned
            self.pin_label.setVisible(self.is_pinned)
            self.note_pinned.emit(self.note_id, self.is_pinned)

class StickyNoteApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.note_data = NoteData()
        self.is_window_pinned = False
        self.window_opacity = 1.0
        self.initUI()
        self.load_saved_notes()
        self.setCursor(Qt.ArrowCursor)
        
    def initUI(self):
        self.setWindowTitle('久久便签-by 微信779059811')
        # 调整窗口宽度确保内容完全显示
        self.setGeometry(100, 100, 350, 600)
        self.setMinimumWidth(320)
        self.setStyleSheet("""
            QMainWindow {
                background-color: pink;
            }
            QPushButton {
                border: none;
                padding: 5px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 15px;
                background-color: #f5f5f5;
            }
            QSlider {
                margin: 0 10px;
            }
            QSlider::groove:horizontal {
                height: 3px;
                background: #ddd;
            }
            QSlider::handle:horizontal {
                background: #999;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QScrollArea {
                border: none;
            }
            QScrollBar:horizontal {
                height: 0px;
            }
        """)
        
        # 主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 顶部工具栏
        toolbar = QWidget()
        toolbar.setStyleSheet("""
            QWidget {
                background-color: #f8f8f8;
                border-bottom: 1px solid #ddd;
            }
            QPushButton {
                font-size: 16px;
                padding: 5px 15px;
                margin: 0 2px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:checked {
                background-color: #e0e0e0;
                color: #333;
            }
        """)
        
        # 添加按钮
        add_button = QPushButton("+")
        add_button.setFont(QFont("Arial", 20))
        add_button.clicked.connect(self.add_new_note)
        add_button.setCursor(Qt.ArrowCursor)
        
        # 窗口置顶按钮
        self.pin_window_button = QPushButton("📌")  # 使用UTF-8编码的图标
        self.pin_window_button.setCheckable(True)
        self.pin_window_button.setToolTip("窗口置顶")
        self.pin_window_button.clicked.connect(self.toggle_window_pin)
        self.pin_window_button.setCursor(Qt.ArrowCursor)
        
        # 透明度调节按钮和滑块
        opacity_widget = QWidget()
        opacity_layout = QHBoxLayout(opacity_widget)
        opacity_layout.setContentsMargins(0, 0, 0, 0)
        opacity_layout.setSpacing(5)
        
        opacity_button = QPushButton("👁")  # 使用UTF-8编码的图标
        opacity_button.setToolTip("调节透明度")
        opacity_button.setCursor(Qt.ArrowCursor)
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(20)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setFixedWidth(100)
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        self.opacity_slider.hide()  # 初始隐藏滑块
        
        opacity_button.clicked.connect(lambda: self.opacity_slider.setVisible(not self.opacity_slider.isVisible()))
        
        opacity_layout.addWidget(opacity_button)
        opacity_layout.addWidget(self.opacity_slider)
        
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        
        toolbar_layout.addWidget(add_button)
        toolbar_layout.addWidget(self.pin_window_button)
        toolbar_layout.addWidget(opacity_widget)
        toolbar_layout.addStretch()
        
        main_layout.addWidget(toolbar)
        
        # 搜索框
        search_widget = QWidget()
        search_layout = QHBoxLayout(search_widget)
        search_layout.setContentsMargins(10, 5, 10, 5)
        
        search_box = QLineEdit()
        search_box.setPlaceholderText("搜索...")
        search_box.textChanged.connect(self.search_notes)
        search_layout.addWidget(search_box)
        
        main_layout.addWidget(search_widget)
        
        # 便签列表区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        # 创建个容器widget来包含所有内容
        self.container_widget = QWidget()
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setAlignment(Qt.AlignTop)
        
        # 便签列表容器
        notes_widget = QWidget()
        self.notes_layout = QVBoxLayout(notes_widget)
        self.notes_layout.setAlignment(Qt.AlignTop)
        self.notes_layout.setSpacing(10)
        self.container_layout.addWidget(notes_widget)
        
        # 添加空状态提示标签
        self.empty_label = QLabel('点击上方"+"创建便签')
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("""
            QLabel {
                color: #999;
                font-size: 16px;
                padding: 20px;
            }
        """)
        # 初始时将空状态标签隐藏
        self.empty_label.hide()
        
        # 创建一个占位的弹性空间，用于将空状态标签居中
        self.container_layout.addStretch(1)
        self.container_layout.addWidget(self.empty_label, 0, Qt.AlignCenter)
        self.container_layout.addStretch(1)
        
        scroll.setWidget(self.container_widget)
        main_layout.addWidget(scroll)
         
                
    def load_saved_notes(self):
        for note in self.note_data.notes:
            self.add_note(
                note['title'],
                note['content'],
                note['timestamp'],
                note['id'],
                note.get('is_pinned', False)
            )
    
    def add_note(self, title, content, timestamp, note_id=None, is_pinned=False):
        if note_id is None:
            note = self.note_data.add_note(title, content, timestamp)
            note_id = note['id']
            is_pinned = note.get('is_pinned', False)
        else:
            note = next((n for n in self.note_data.notes if n['id'] == note_id), None)
            if note:
                is_pinned = note.get('is_pinned', False)
            else:
                is_pinned = False
        
        note_card = NoteCard(note_id, title, content, timestamp)
        note_card.is_pinned = is_pinned
        note_card.pin_label.setVisible(is_pinned)
        note_card.note_clicked.connect(self.edit_note)
        note_card.note_deleted.connect(self.delete_note)
        note_card.note_pinned.connect(self.toggle_pin_note)
        
        self.notes_layout.insertWidget(0, note_card)
        self.update_empty_state()
        self.reorder_notes()
    
    def add_new_note(self):
        timestamp = datetime.now().strftime("%H:%M")
        dialog = NoteEditDialog("输入标题：", "", self)
        
        # 计算新窗口位置
        main_window_pos = self.geometry()
        screen_width = QApplication.desktop().screenGeometry().width()
        
        # 检查主窗口在屏幕的哪一侧
        window_center_x = main_window_pos.x() + main_window_pos.width() / 2
        is_on_right_half = window_center_x > screen_width / 2
        
        # 根据主窗口位置决定新窗口出现在左侧还是右侧
        if is_on_right_half:
            # 主窗口在右半边，新窗口放左边
            dialog_x = main_window_pos.x() - dialog.width() - 1
        else:
            # 主窗口在左半边，新窗口放右边
            dialog_x = main_window_pos.x() + main_window_pos.width() + 1
        
        # 顶部对齐
        dialog_y = main_window_pos.y()
        
        # 确保窗口不会超出屏幕边界
        screen_rect = QApplication.desktop().screenGeometry()
        dialog_x = max(10, min(dialog_x, screen_rect.width() - dialog.width() - 10))
        dialog_y = max(10, min(dialog_y, screen_rect.height() - dialog.height() - 10))
        
        dialog.move(int(dialog_x), int(dialog_y))
        
        if dialog.exec_() == QDialog.Accepted:
            title = dialog.get_title()
            content = dialog.get_content()
            if title or content:  # 只当标题或内容不为空时才建便签
                self.add_note(title, content, timestamp)
    
    def edit_note(self, note_id, title, content):
        dialog = NoteEditDialog(title, content, self)
        
        # 计算新窗口位置
        main_window_pos = self.geometry()
        screen_width = QApplication.desktop().screenGeometry().width()
        
        # 检查主窗口在屏幕的哪一侧
        window_center_x = main_window_pos.x() + main_window_pos.width() / 2
        is_on_right_half = window_center_x > screen_width / 2
        
        # 根据主窗口位置决定新窗口出现在左侧还是右侧
        if is_on_right_half:
            # 主窗口在右半边，新窗口放左边
            dialog_x = main_window_pos.x() - dialog.width() - 1
        else:
            # 主窗口在左半边，新窗口放右边
            dialog_x = main_window_pos.x() + main_window_pos.width() + 1
        
        # 顶部对齐
        dialog_y = main_window_pos.y()
        
        # 确保窗口不会超出屏幕边界
        screen_rect = QApplication.desktop().screenGeometry()
        dialog_x = max(10, min(dialog_x, screen_rect.width() - dialog.width() - 10))
        dialog_y = max(10, min(dialog_y, screen_rect.height() - dialog.height() - 10))
        
        dialog.move(int(dialog_x), int(dialog_y))
        
        if dialog.exec_() == QDialog.Accepted:
            new_title = dialog.get_title()
            new_content = dialog.get_content()
            
            # 更新数据存储
            if self.note_data.update_note(note_id, new_title, new_content):
                # 更新UI
                for i in range(self.notes_layout.count()):
                    widget = self.notes_layout.itemAt(i).widget()
                    if isinstance(widget, NoteCard) and widget.note_id == note_id:
                        widget.title = new_title
                        widget.content = new_content
                        widget.title_label.setText(new_title)
                        widget.content_label.setText(new_content)
                        break
    
    def search_notes(self, text):
        if not text:
            # 显示所有便签
            for i in range(self.notes_layout.count()):
                self.notes_layout.itemAt(i).widget().show()
            return
        
        # 搜索并只显示匹配的便签
        results = self.note_data.search_notes(text)
        result_ids = [note['id'] for note in results]
        
        for i in range(self.notes_layout.count()):
            widget = self.notes_layout.itemAt(i).widget()
            if isinstance(widget, NoteCard):
                widget.setVisible(widget.note_id in result_ids)

    def delete_note(self, note_id):
        self.note_data.delete_note(note_id)
        # 从UI中移除便签
        for i in range(self.notes_layout.count()):
            widget = self.notes_layout.itemAt(i).widget()
            if isinstance(widget, NoteCard) and widget.note_id == note_id:
                widget.deleteLater()
                break
        self.update_empty_state()

    def toggle_pin_note(self, note_id, is_pinned):
        if self.note_data.update_note_pin_status(note_id, is_pinned):
            self.reorder_notes()

    def reorder_notes(self):
        # 获取排序后的便签数据
        ordered_notes = self.note_data.get_notes_ordered()
        
        # 临时存储所有便签卡片
        current_cards = {}
        cards_to_remove = []
        
        # 收集所有便签卡片
        for i in range(self.notes_layout.count()):
            widget = self.notes_layout.itemAt(i).widget()
            if isinstance(widget, NoteCard):
                current_cards[widget.note_id] = widget
                cards_to_remove.append(widget)
        
        # 从布局中移除所有便签卡片
        for card in cards_to_remove:
            self.notes_layout.removeWidget(card)
            card.setParent(None)
        
        # 按新顺序重新添加便签卡片（从后往前添加，这样最新的会在最上面）
        for note in reversed(ordered_notes):
            note_id = note['id']
            if note_id in current_cards:
                card = current_cards[note_id]
                card.is_pinned = note.get('is_pinned', False)
                card.pin_label.setVisible(card.is_pinned)
                self.notes_layout.insertWidget(0, card)  # 插入到最顶端
        
        # 新空状态显示
        self.update_empty_state()
        
        # 强制更新布局
        self.container_layout.update()
        self.notes_layout.update()

    def handle_note_reorder(self, source_id, target_id):
        self.note_data.reorder_notes(source_id, target_id)
        self.reorder_notes()

    def update_empty_state(self):
        # 检查是否有便签
        has_notes = False
        for i in range(self.notes_layout.count()):
            widget = self.notes_layout.itemAt(i).widget()
            if isinstance(widget, NoteCard):
                has_notes = True
                break
        
        # 显示或隐藏空状态提示和弹性空间
        self.empty_label.setVisible(not has_notes)
        
        # 更新布局中的弹性空间
        if has_notes:
            # 有便签时，移除弹性空间，让便签紧凑排列
            self.container_layout.setStretch(0, 1)  # 便签区域占满
            self.container_layout.setStretch(1, 0)  # 上部弹性空间
            self.container_layout.setStretch(2, 0)  # 空状态标签
            self.container_layout.setStretch(3, 0)  # 下部弹性空间
        else:
            # 没有便签时，加弹性空间使空状态标签居中
            self.container_layout.setStretch(0, 0)  # 便签区域
            self.container_layout.setStretch(1, 1)  # 上部弹性空间
            self.container_layout.setStretch(2, 0)  # 空状态标签
            self.container_layout.setStretch(3, 1)  # 下部弹性空间

    def toggle_window_pin(self):
        self.is_window_pinned = not self.is_window_pinned
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self.is_window_pinned)
        self.show()  # 需要重新显示窗口以应用更改
        self.pin_window_button.setChecked(self.is_window_pinned)

    def change_opacity(self, value):
        self.window_opacity = value / 100
        self.setWindowOpacity(self.window_opacity)

class ImageViewer(QDialog):
    def __init__(self, image_path):
        super().__init__()
        self.setWindowTitle("图片查看")
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        
        layout = QVBoxLayout()
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        # 加载原始图片
        label = QLabel()
        pixmap = QPixmap(image_path)
        
        # 获取屏幕尺寸
        screen = QApplication.desktop().screenGeometry()
        max_width = screen.width() * 0.8
        max_height = screen.height() * 0.8
        
        # 如果图片超过屏幕80%的大小，则等比例缩放
        if pixmap.width() > max_width or pixmap.height() > max_height:
            pixmap = pixmap.scaled(int(max_width), int(max_height), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        label.setPixmap(pixmap)
        scroll.setWidget(label)
        
        layout.addWidget(scroll)
        
        # 添加关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 设置窗口大小
        self.resize(min(pixmap.width() + 40, int(max_width)),
                   min(pixmap.height() + 80, int(max_height)))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = StickyNoteApp()
    ex.show()
    sys.exit(app.exec_())
