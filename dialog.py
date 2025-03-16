from typing import List, Dict, Any, Union, Tuple, Dict, Optional
import logging

from PyQt5.QtWidgets import (QDialog, QLabel, QVBoxLayout, QPushButton, 
                            QGraphicsDropShadowEffect, QSizePolicy, QWidget)
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
    """对话框配置类，用于集中管理DialogBox的所有配置参数"""
    def __init__(self):
        # 基本尺寸配置
        self.min_width = 300
        self.min_height = 100
        self.max_width = 400
        self.padding = 15
        self.corner_size = 10  # 斜角大小
        
        # 颜色配置
        self.background_color = "#d4d0c8"  # 旧式Windows灰色
        self.border_dark_color = "#404040"  # 深灰色边框
        self.border_light_color = "#ffffff"  # 白色边框
        self.border_medium_color = "#808080"  # 中灰色
        self.text_color = "#000000"
        self.title_color = "#000000"
        
        # 阴影配置
        self.shadow_enabled = True
        self.shadow_blur_radius = 15
        self.shadow_color = QColor(0, 0, 0, 180)
        self.shadow_offset_x = 5
        self.shadow_offset_y = 5
        
        # 按钮样式
        self.button_style = """
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
        """
        
        # 文本样式
        self.text_style = """
            font-family: 'Microsoft YaHei', 'SimSun', Arial; 
            font-size: 14px; 
            color: #000000; 
            background-color: transparent;
            padding: 5px;
            QLabel {
                background: transparent;
            }
        """
        
        # 动画配置
        self.text_animation_speed = 30  # 毫秒/字符
        self.cursor_blink_interval = 750  # 光标闪烁间隔(毫秒)
        self.size_animation_duration = 100  # 大小变化动画持续时间(毫秒)
        
        # 光标配置
        self.cursor_char = "▌"  # 光标字符
        self.cursor_enabled = True
        
        # 标题配置
        self.title = "Apeiria"
        self.title_height = 30
        self.title_font = "Microsoft YaHei"
        self.title_font_size = 10

        # 内容区域配置
        self.content_top_margin = 35  # 内容区域顶部边距，确保不与标题重叠

        # 关闭按钮配置
        self.close_button_height = 25
        
        # 行为配置
        self.draggable = True
        self.click_to_complete_text = True
        self.close_button_text = "关闭"


class DialogBox(QDialog):
    """可配置的旧式Windows风格对话框，带有逐字显示效果"""
    def __init__(self, parent=None, text="你好！我是Apeiria！", config=None):
        super().__init__(parent, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # 使用默认配置或传入的配置
        self.config = config if config else DialogBoxConfig()
        
        # 设置无边框和透明背景
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建主布局 - 使用绝对定位
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        # 创建一个容器widget来包含文本和按钮
        self.container = QWidget(self)
        self.container.setObjectName("container")
        self.container.setStyleSheet("background: transparent;")
        
        # 设置容器为绝对定位
        self.container.setGeometry(
            self.config.padding, 
            self.config.title_height + 10,  # 固定在分隔线下方10px
            self.config.min_width - 2 * self.config.padding, 
            self.config.min_height - self.config.title_height - 10
        )
        
        # 容器内使用垂直布局
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建文本标签
        self.label = QLabel("")
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.RichText)
        self.label.setStyleSheet(self.config.text_style)
        # 设置文本标签不裁剪内容
        self.label.setAttribute(Qt.WA_TranslucentBackground)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        container_layout.addWidget(self.label, 1)  # 1表示可以拉伸
        
        # 关闭按钮
        self.close_button = QPushButton(self.config.close_button_text)
        self.close_button.clicked.connect(self.close)
        self.close_button.setStyleSheet(self.config.button_style)
        self.close_button.setFixedHeight(self.config.close_button_height)
        container_layout.addWidget(self.close_button)
        
        # 设置阴影效果
        if self.config.shadow_enabled:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(self.config.shadow_blur_radius)
            shadow.setColor(self.config.shadow_color)
            shadow.setOffset(self.config.shadow_offset_x, self.config.shadow_offset_y)
            self.setGraphicsEffect(shadow)
        
        # 文字动画相关变量
        self.full_text = text
        self.current_text = ""
        self.cursor_visible = True
        self.char_index = 0
        
        # 设置计时器用于文字动画
        self.text_timer = QTimer(self)
        self.text_timer.timeout.connect(self.update_text)
        
        # 设置计时器用于光标闪烁
        if self.config.cursor_enabled:
            self.cursor_timer = QTimer(self)
            self.cursor_timer.timeout.connect(self.toggle_cursor)
            self.cursor_timer.start(self.config.cursor_blink_interval)
        
        # 对话框大小动画
        self.size_animation = QPropertyAnimation(self, b"geometry")
        self.size_animation.setDuration(self.config.size_animation_duration)
        
        # 初始大小 - 增加高度以适应标题栏
        # self.current_height = self.config.min_height + self.config.title_height
        # current height shall add one line of text
        self.current_height = self.config.min_height + self.config.title_height
        self.resize(self.config.min_width, self.current_height)
        
        # 开始文字动画
        self.setText(text)
    
    def resizeEvent(self, event):
        """窗口大小改变时调整容器大小"""
        super().resizeEvent(event)
        # 调整容器大小以适应窗口
        self.container.setGeometry(
            self.config.padding, 
            self.config.title_height + 10,  # 固定在分隔线下方10px
            self.width() - 2 * self.config.padding, 
            self.height() - self.config.title_height - self.config.padding - 10
        )
    
    def paintEvent(self, event):
        """自定义绘制对话框外观"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制旧式Windows风格的斜角矩形
        path = QPainterPath()
        rect = self.rect().adjusted(5, 5, -5, -5)  # 留出空间给阴影
        
        # 创建斜角矩形路径
        corner = self.config.corner_size
        path.moveTo(rect.left() + corner, rect.top())
        path.lineTo(rect.right() - corner, rect.top())
        path.lineTo(rect.right(), rect.top() + corner)
        path.lineTo(rect.right(), rect.bottom() - corner)
        path.lineTo(rect.right() - corner, rect.bottom())
        path.lineTo(rect.left() + corner, rect.bottom())
        path.lineTo(rect.left(), rect.bottom() - corner)
        path.lineTo(rect.left(), rect.top() + corner)
        path.closeSubpath()
        
        # 填充背景色
        painter.setBrush(QBrush(QColor(self.config.background_color)))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)
        
        # 绘制3D效果边框
        # 外边框
        painter.setPen(QPen(QColor(self.config.border_dark_color), 1))
        painter.drawLine(rect.left(), rect.bottom() - corner, 
                        rect.left(), rect.top() + corner)
        painter.drawLine(rect.left() + corner, rect.top(), 
                        rect.right() - corner, rect.top())
        
        painter.setPen(QPen(QColor(self.config.border_light_color), 1))
        painter.drawLine(rect.right(), rect.top() + corner, 
                        rect.right(), rect.bottom() - corner)
        painter.drawLine(rect.left() + corner, rect.bottom(), 
                        rect.right() - corner, rect.bottom())
        
        # 内边框（标题栏分隔线）
        painter.setPen(QPen(QColor(self.config.border_medium_color), 1))
        painter.drawLine(rect.left() + 5, rect.top() + self.config.title_height, 
                        rect.right() - 5, rect.top() + self.config.title_height)
        
        # 绘制标题
        painter.setPen(QPen(QColor(self.config.title_color), 1))
        font = painter.font()
        font.setFamily(self.config.title_font)
        font.setPointSize(self.config.title_font_size)
        painter.setFont(font)
        painter.drawText(rect.left() + 15, rect.top() + 5, 
                        rect.width() - 30, self.config.title_height - 5, 
                        Qt.AlignLeft | Qt.AlignVCenter, self.config.title)
    
    def setText(self, text):
        """设置要显示的文本并开始动画"""
        self.full_text = text
        self.current_text = ""
        self.char_index = 0
        
        # 停止之前的动画
        self.text_timer.stop()
        
        # 重置对话框大小 - 考虑标题栏高度
        initial_height = self.config.min_height + self.config.title_height
        self.resize(self.config.min_width, initial_height)
        self.current_height = initial_height
        
        # 开始新的动画
        self.text_timer.start(self.config.text_animation_speed)

    def update_text(self):
        """更新文本显示，逐字添加"""
        if self.char_index < len(self.full_text):
            self.current_text += self.full_text[self.char_index]
            self.char_index += 1
            
            # 更新标签文本（带光标）
            self.label.setText(self.get_text_with_cursor())
            
            # 根据文本长度调整对话框高度
            self.resize_dialog()
        else:
            # 动画结束
            self.text_timer.stop()

    def resize_dialog(self):
        """调整对话框大小以适应文本"""
        # 计算文本所需高度 - 始终考虑光标字符的宽度
        text_for_height_calc = self.current_text
        
        # 如果启用了光标，在计算高度时始终添加光标字符
        # 这样可以避免光标闪烁导致高度变化
        if self.config.cursor_enabled:
            text_for_height_calc += self.config.cursor_char
        
        # 创建临时QLabel来计算确切高度，避免闪烁问题
        temp_label = QLabel()
        temp_label.setWordWrap(True)
        temp_label.setStyleSheet(self.config.text_style)
        temp_label.setText(text_for_height_calc)
        temp_label.setFixedWidth(self.width() - 2 * self.config.padding - 10)
        
        # 获取实际需要的高度
        text_height = temp_label.sizeHint().height()
        
        # 计算对话框总高度
        new_height = text_height + self.config.title_height + self.close_button.height() + 50
        new_height = max(self.config.min_height + self.config.title_height + 10, new_height)
        
        if new_height > self.current_height:
            # 动画调整对话框大小
            self.size_animation.setStartValue(self.geometry())
            new_rect = QRect(self.x(), self.y(), self.width(), new_height)
            self.size_animation.setEndValue(new_rect)
            self.size_animation.start()
            self.current_height = new_height
    
    def toggle_cursor(self):
        """切换光标可见性"""
        if not self.config.cursor_enabled:
            return
            
        self.cursor_visible = not self.cursor_visible
        
        # 如果文字动画已经结束，手动更新光标
        if self.char_index >= len(self.full_text):
            self.label.setText(self.get_text_with_cursor())
    
    def get_text_with_cursor(self):
        """获取当前文本和光标字符"""
        if self.config.cursor_enabled:
            if self.cursor_visible:
                return self.current_text + self.config.cursor_char
            else:
                invisible_cursor = f"<span style='color:rgba(0,0,0,0);'>{self.config.cursor_char}</span>"
                return self.current_text + invisible_cursor
        else:
            return self.current_text
    
    def speak(self, text, voice_file=None):
        """文本转语音功能（未来扩展）"""
        self.setText(text)
        # 未来实现: 添加TTS功能
        if voice_file:
            print(f"播放语音: {voice_file}")
        else:
            print(f"角色说: {text}")
    
    def mousePressEvent(self, event):
        """点击对话框时处理"""
        if event.button() == Qt.LeftButton:
            # 如果动画正在进行，点击时直接显示全部文字
            if self.config.click_to_complete_text and self.text_timer.isActive():
                self.text_timer.stop()
                self.current_text = self.full_text
                self.char_index = len(self.full_text)
                
                if self.config.cursor_enabled:
                    if self.cursor_visible:
                        self.label.setText(self.current_text + self.config.cursor_char)
                    else:
                        self.label.setText(self.current_text)
                else:
                    self.label.setText(self.current_text)
                
                # 调整对话框大小
                self.resize_dialog()

            # 允许拖动对话框
            if self.config.draggable:
                self.old_pos = event.globalPos()
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """拖动对话框"""
        if self.config.draggable and hasattr(self, 'old_pos'):
            delta = event.globalPos() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()
        
        super().mouseMoveEvent(event)
    
    # 解决setLayout(None)问题的方法
    def clearLayout(self):
        """清除布局中的所有部件"""
        if self.layout is not None:
            while self.layout.count():
                item = self.layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)


# 使用示例
def create_dialog(parent=None, text="你好！我是Apeiria！", style="windows_classic"):
    """创建预设样式的对话框"""
    config = DialogBoxConfig()
    
    if style == "windows_classic":
        # 默认配置已经是Windows经典样式
        pass
    elif style == "windows_xp":
        # Windows XP风格
        config.background_color = "#ECE9D8"
        config.border_dark_color = "#0054E3"
        config.border_light_color = "#B9D1EA"
        config.border_medium_color = "#7DA2CE"
        config.title_color = "#FFFFFF"
        config.button_style = """
            QPushButton {
                background-color: #ECE9D8; 
                color: black;
                border: 2px solid #7DA2CE;
                border-style: outset;
                border-width: 2px;
                border-top-color: #FFFFFF;
                border-left-color: #FFFFFF;
                border-right-color: #0054E3;
                border-bottom-color: #0054E3;
                padding: 3px;
                font-family: 'Tahoma', 'Arial';
                font-size: 12px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #F2F1E8;
            }
            QPushButton:pressed {
                border-style: inset;
                border-top-color: #0054E3;
                border-left-color: #0054E3;
                border-right-color: #FFFFFF;
                border-bottom-color: #FFFFFF;
                background-color: #DCD8C0;
            }
        """
    elif style == "modern":
        # 现代风格
        config.background_color = "#FFFFFF"
        config.border_dark_color = "#CCCCCC"
        config.border_light_color = "#EEEEEE"
        config.border_medium_color = "#DDDDDD"
        config.title_color = "#333333"
        config.shadow_blur_radius = 20
        config.shadow_color = QColor(0, 0, 0, 100)
        config.corner_size = 15
        config.button_style = """
            QPushButton {
                background-color: #4285F4; 
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px;
                font-family: 'Segoe UI', 'Arial';
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5294FF;
            }
            QPushButton:pressed {
                background-color: #3275E4;
            }
        """
        config.text_style = """
            font-family: 'Segoe UI', 'Microsoft YaHei', Arial; 
            font-size: 14px; 
            color: #333333; 
            background-color: transparent;
            padding: 8px;
        """
    elif style == "dark":
        # 暗色主题
        config.background_color = "#2D2D30"
        config.border_dark_color = "#1E1E1E"
        config.border_light_color = "#3F3F46"
        config.border_medium_color = "#333337"
        config.title_color = "#FFFFFF"
        config.text_color = "#FFFFFF"
        config.shadow_blur_radius = 25
        config.shadow_color = QColor(0, 0, 0, 200)
        config.button_style = """
            QPushButton {
                background-color: #007ACC; 
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px;
                font-family: 'Segoe UI', 'Arial';
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1C8ADB;
            }
            QPushButton:pressed {
                background-color: #006BB3;
            }
        """
        config.text_style = """
            font-family: 'Segoe UI', 'Microsoft YaHei', Arial; 
            font-size: 14px; 
            color: #FFFFFF; 
            background-color: transparent;
            padding: 8px;
        """
        config.cursor_char = "█"

    elif style == "love":
        config = DialogBoxConfig()
        config.background_color = "#FFE4E1"  # 粉色背景
        config.cursor_char = "❤"  # 心形光标
    
    return DialogBox(parent, text, config)
