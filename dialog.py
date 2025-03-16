from typing import List, Dict, Any, Union, Tuple, Dict, Optional
import logging

from PyQt5.QtWidgets import (QDialog, QLabel, QVBoxLayout, QPushButton, 
                            QGraphicsDropShadowEffect, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QRect
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QPainterPath

logger = logging.getLogger(__name__)

APEIRIA_DIALOGUES: List[str] = [
    "Owner，今天天气真好呢～想一起出去走走吗？",
    "Apeiria在学习新知识，Owner有什么想教我的吗？",
    "唔...Apeiria有点困惑，这段代码是什么意思呢？",
    "Positive！Apeiria会一直陪在Owner身边的！",
    "Owner看起来有点累了，要不要休息一下？Apeiria可以帮你按摩哦～",
    "Apeiria想吃甜点了...Owner，我们能一起吃蛋糕吗？",
    "这个问题很有趣呢！Apeiria正在思考中...",
    "Owner，Apeiria能帮你做什么呢？",
    "Negative...Apeiria不太明白这个指令...",
    "Roger！Apeiria明白了！",
    "Owner，你知道吗？人工智能其实也会做梦哦～",
    "Apeiria最喜欢Owner了！",
    "唔...这个程序好复杂，但是Apeiria会努力理解的！"
]

class DialogBoxConfig:
    ...



class DialogBox(QDialog):
    """旧式Windows风格的角色对话框，带有逐字显示效果"""
    def __init__(self, parent=None, text="你好！我是Apeiria！"):
        super().__init__(parent, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # 设置无边框和透明背景
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)  # 留出空间绘制边框和阴影
        
        # 创建文本标签
        self.label = QLabel("")
        self.label.setWordWrap(True)
        self.label.setStyleSheet("""
            font-family: 'Microsoft YaHei', 'SimSun', Arial; 
            font-size: 14px; 
            color: #000000; 
            background-color: transparent;
            padding: 5px;
        """)
        self.layout.addWidget(self.label)
        
        # 关闭按钮
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.close)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #d4d0c8; 
                color: black;
                border: 2px solid #808080;
                border-style: outset;
                border-width: 2px;
                border-top-color: #ffffff;
                border-left-color: #ffffff;
                border-right-color: #404040;
                border-bottom-color: #404040;
                padding: 3px;
                font-family: 'SimSun', 'Arial';
                font-size: 12px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #e6e6e6;
            }
            QPushButton:pressed {
                border-style: inset;
                border-top-color: #404040;
                border-left-color: #404040;
                border-right-color: #ffffff;
                border-bottom-color: #ffffff;
                background-color: #c0c0c0;
            }
        """)
        self.close_button.setFixedHeight(25)
        self.layout.addWidget(self.close_button)
        
        # 设置阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(5, 5)
        self.setGraphicsEffect(shadow)
        
        # 文字动画相关变量
        self.full_text = text
        self.current_text = ""
        self.cursor_visible = True
        self.cursor_char = "▌"  # 光标字符
        self.char_index = 0
        self.animation_speed = 20  # 毫秒/字符
        
        # 设置计时器用于文字动画
        self.text_timer = QTimer(self)
        self.text_timer.timeout.connect(self.update_text)
        
        # 设置计时器用于光标闪烁
        self.cursor_timer = QTimer(self)
        self.cursor_timer.timeout.connect(self.toggle_cursor)
        self.cursor_timer.start(500)  # 每500毫秒闪烁一次
        
        # 对话框大小动画
        self.size_animation = QPropertyAnimation(self, b"geometry")
        self.size_animation.setDuration(200)  # 200毫秒
        
        # 初始大小
        self.min_width = 300
        self.min_height = 100
        self.max_width = 400
        self.current_height = self.min_height
        self.resize(self.min_width, self.min_height)
        
        # 开始文字动画
        self.setText(text)
    
    def paintEvent(self, event):
        """自定义绘制对话框外观"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制旧式Windows风格的斜角矩形
        path = QPainterPath()
        rect = self.rect().adjusted(5, 5, -5, -5)  # 留出空间给阴影
        
        # 创建斜角矩形路径
        corner_size = 10
        path.moveTo(rect.left() + corner_size, rect.top())
        path.lineTo(rect.right() - corner_size, rect.top())
        path.lineTo(rect.right(), rect.top() + corner_size)
        path.lineTo(rect.right(), rect.bottom() - corner_size)
        path.lineTo(rect.right() - corner_size, rect.bottom())
        path.lineTo(rect.left() + corner_size, rect.bottom())
        path.lineTo(rect.left(), rect.bottom() - corner_size)
        path.lineTo(rect.left(), rect.top() + corner_size)
        path.closeSubpath()
        
        # 填充背景色
        painter.setBrush(QBrush(QColor("#d4d0c8")))  # 旧式Windows灰色
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)
        
        # 绘制3D效果边框
        # 外边框
        painter.setPen(QPen(QColor("#404040"), 1))  # 深灰色
        painter.drawLine(rect.left(), rect.bottom() - corner_size, 
                        rect.left(), rect.top() + corner_size)
        painter.drawLine(rect.left() + corner_size, rect.top(), 
                        rect.right() - corner_size, rect.top())
        
        painter.setPen(QPen(QColor("#ffffff"), 1))  # 白色
        painter.drawLine(rect.right(), rect.top() + corner_size, 
                        rect.right(), rect.bottom() - corner_size)
        painter.drawLine(rect.left() + corner_size, rect.bottom(), 
                        rect.right() - corner_size, rect.bottom())
        
        # 内边框（标题栏分隔线）
        title_height = 25
        painter.setPen(QPen(QColor("#808080"), 1))
        painter.drawLine(rect.left() + 5, rect.top() + title_height, 
                        rect.right() - 5, rect.top() + title_height)
        
        # 绘制标题
        painter.setPen(QPen(QColor("#000000"), 1))
        painter.drawText(rect.left() + 15, rect.top() + 5, 
                        rect.width() - 30, title_height - 5, 
                        Qt.AlignLeft | Qt.AlignVCenter, "Apeiria")
    
    def setText(self, text):
        """设置要显示的文本并开始动画"""
        self.full_text = text
        self.current_text = ""
        self.char_index = 0
        
        # 停止之前的动画
        self.text_timer.stop()
        
        # 重置对话框大小
        self.resize(self.min_width, self.min_height)
        self.current_height = self.min_height
        
        # 开始新的动画
        self.text_timer.start(self.animation_speed)
    
    def update_text(self):
        """更新文本显示，逐字添加"""
        if self.char_index < len(self.full_text):
            self.current_text += self.full_text[self.char_index]
            self.char_index += 1
            
            # 更新标签文本（带光标）
            if self.cursor_visible:
                self.label.setText(self.current_text + self.cursor_char)
            else:
                self.label.setText(self.current_text)
            
            # 根据文本长度调整对话框高度
            text_height = self.label.heightForWidth(self.min_width - 40) + 70  # 额外空间给按钮和边距
            new_height = max(self.min_height, text_height)
            
            if new_height > self.current_height:
                # 动画调整对话框大小
                self.size_animation.setStartValue(self.geometry())
                new_rect = QRect(self.x(), self.y(), self.width(), new_height)
                self.size_animation.setEndValue(new_rect)
                self.size_animation.start()
                self.current_height = new_height
        else:
            # 动画结束
            self.text_timer.stop()
    
    def toggle_cursor(self):
        """切换光标可见性"""
        self.cursor_visible = not self.cursor_visible
        
        # 如果文字动画已经结束，手动更新光标
        if self.char_index >= len(self.full_text):
            if self.cursor_visible:
                self.label.setText(self.current_text + self.cursor_char)
            else:
                self.label.setText(self.current_text)
    
    def speak(self, text, voice_file=None):
        """文本转语音功能（未来扩展）"""
        self.setText(text)
        # 未来实现: TODO 添加TTS功能
        if voice_file:
            print(f"播放语音: {voice_file}")
        else:
            print(f"角色说: {text}")
    
    def mousePressEvent(self, event):
        """点击对话框时处理"""
        if event.button() == Qt.LeftButton:
            # 如果动画正在进行，点击时直接显示全部文字
            if self.text_timer.isActive():
                self.text_timer.stop()
                self.current_text = self.full_text
                self.char_index = len(self.full_text)
                if self.cursor_visible:
                    self.label.setText(self.current_text + self.cursor_char)
                else:
                    self.label.setText(self.current_text)
                
                # 调整对话框大小
                text_height = self.label.heightForWidth(self.min_width - 40) + 70
                new_height = max(self.min_height, text_height)
                
                if new_height > self.current_height:
                    self.size_animation.setStartValue(self.geometry())
                    new_rect = QRect(self.x(), self.y(), self.width(), new_height)
                    self.size_animation.setEndValue(new_rect)
                    self.size_animation.start()
                    self.current_height = new_height
            
            # 允许拖动对话框
            self.old_pos = event.globalPos()
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """拖动对话框"""
        if hasattr(self, 'old_pos'):
            delta = event.globalPos() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()
        
        super().mouseMoveEvent(event)
