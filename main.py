import os
import sys
import logging

from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QDialog, QPushButton
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QTimer, QSize, QPoint
from PyQt5.QtCore import QPropertyAnimation, QParallelAnimationGroup, QEasingCurve
from PyQt5.QtGui import QMovie, QPixmap, QPainter, QTransform
import keyboard

import tachie
from tachie import TACHIE_MANAGER_CLSMAP
from dialog import APEIRIA_DIALOGUES, DialogBox

logger = logging.getLogger(__name__)


class HotkeyExitMixin:
    # 在AnimeCharacter类中添加以下方法
    def setup_hotkeys(self):
        """设置全局热键"""
        # 使用Alt+F4作为退出热键
        keyboard.add_hotkey('alt+f4', self.exit_application)
        # 也可以添加自定义热键，例如Ctrl+Shift+X
        keyboard.add_hotkey('ctrl+shift+x', self.exit_application)
        logger.info("热键已设置: Alt+F4 或 Ctrl+Shift+X 退出应用")

    def exit_application(self):
        """退出应用程序"""
        logger.info("退出热键被触发，应用程序正在关闭...")
        QApplication.quit()

class AnimeCharacter(QMainWindow, HotkeyExitMixin):
    def __init__(self, tachie_manager="apeiria", window_size=(300, 500)):
        super().__init__()
        
        # 状态
        self.NORMAL = "normal"
        self.DRAGGING = "dragging"
        self.COLLAPSED = "collapsed"
        self.current_state = self.NORMAL

        self.window_size = window_size # (w, h)
        
        # 窗口设置 - 确保始终置顶
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建立绘管理器
        self.tachie_manager = TACHIE_MANAGER_CLSMAP[tachie_manager](image_size=window_size)
        
        
        # 设置中央窗口部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 布局
        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 角色显示标签
        self.character_label = QLabel()
        layout.addWidget(self.character_label)
        
        # 屏幕边界
        self.screen_geometry = QApplication.desktop().availableGeometry()
        
        # 初始化UI
        self.initialize_ui()
        
        # 拖动相关
        self.dragging = False
        self.drag_position = None
        self.drag_start_pos = None
        
        # 对话框
        self.dialog = None
        
        # 折叠动画
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(300)  # 300毫秒
        
        # 表情动画计时器
        self.emotion_timer = QTimer()
        self.emotion_timer.timeout.connect(self.reset_emotion)

        self.setup_hotkeys()
        
    def update_character_display(self):
        """更新角色显示"""
        if self.current_state == self.NORMAL:
            pixmap = self.tachie_manager.get_composite_image()
        elif self.current_state == self.DRAGGING:
            # 拖动时可以切换到不同的姿势
            old_base = self.tachie_manager.current_base
            self.tachie_manager.set_base_emotion_combination("豆豆眼拒绝")
            pixmap = self.tachie_manager.get_composite_image()
            self.tachie_manager.set_base(old_base)
        elif self.current_state == self.COLLAPSED:
            # 折叠状态：旋转90度并只显示头部
            # head_pixmap = self.tachie_manager.get_head_image()
            
            # 旋转图像90度
            # transform = QTransform().rotate(270)
            # rotated_pixmap = head_pixmap.transformed(transform, Qt.SmoothTransformation)
            
            # pixmap = rotated_pixmap

            pixmap = self.tachie_manager.get_composite_image()

        # 缩放图像到合理大小
        if not pixmap.isNull():
            self.character_label.setPixmap(pixmap)
            self.character_label.setFixedSize(pixmap.size())
            return pixmap.size()
        
        return QSize(*self.window_size) # 返回默认大小

    def initialize_ui(self):
        """初始化UI，设置在右下角"""
        # 更新角色显示并获取缩放后的大小
        pixmap_size = self.update_character_display()
        
        # 设置窗口大小为图像大小
        self.resize(pixmap_size.width(), pixmap_size.height())
        
        # 确保窗口位于右下角
        x_pos = self.screen_geometry.width() - pixmap_size.width()
        y_pos = self.screen_geometry.height() - pixmap_size.height()
        self.move(x_pos, y_pos)
        
        # 显示窗口
        self.show()
    
    def set_emotion(self, emotion, duration=3000):
        """设置角色表情，持续指定时间后恢复"""
        if self.tachie_manager.set_emotion(emotion):
            self.update_character_display()
            
            # 设置计时器，恢复默认表情
            self.emotion_timer.start(duration)
    
    def reset_emotion(self):
        """恢复默认表情"""
        self.emotion_timer.stop()
        self.tachie_manager.set_emotion("普通")
        self.update_character_display()

    def mouseDoubleClickEvent(self, event):
        # 在折叠状态下，双击左键展开
        if self.current_state == self.COLLAPSED and event.button() == Qt.LeftButton:
            self.expand()
        # 在正常状态下，双击左键折叠
        elif self.current_state == self.NORMAL and event.button() == Qt.LeftButton:
            self.collapse_to_right()
        event.accept()
    
    def mousePressEvent(self, event):
        # 在折叠状态下，只处理展开操作
        if self.current_state == self.COLLAPSED:
            if event.button() == Qt.LeftButton:
                self.expand()
                event.accept()
            return  # 忽略其他所有操作
    
        # 正常状态下的处理
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.drag_start_pos = event.globalPos()
            self.current_state = self.DRAGGING
            self.update_character_display()
            event.accept()
        elif event.button() == Qt.RightButton:
            # 右键点击显示随机对话
            self.show_random_dialog()
            event.accept()

    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.dragging:
            # 计算移动的距离
            new_pos = event.globalPos() - self.drag_position
            
            # 保存移动前的位置
            old_pos = self.pos()
            
            # 移动立绘
            self.move(new_pos)
            
            # 如果对话框正在显示，同步移动对话框
            if self.dialog and self.dialog.isVisible():
                # 计算立绘移动的偏移量
                delta_x = self.x() - old_pos.x()
                delta_y = self.y() - old_pos.y()
                
                # 移动对话框
                dialog_new_pos = self.dialog.pos() + QPoint(delta_x, delta_y)
                
                # 确保对话框不会移出屏幕
                if dialog_new_pos.x() < 0:
                    dialog_new_pos.setX(0)
                elif dialog_new_pos.x() + self.dialog.width() > self.screen_geometry.width():
                    dialog_new_pos.setX(self.screen_geometry.width() - self.dialog.width())
                    
                if dialog_new_pos.y() < 0:
                    dialog_new_pos.setY(0)
                elif dialog_new_pos.y() + self.dialog.height() > self.screen_geometry.height():
                    dialog_new_pos.setY(self.screen_geometry.height() - self.dialog.height())
                
                self.dialog.move(dialog_new_pos)
            
            event.accept()
            self.move(event.globalPos() - self.drag_position)
            # event.accept()
    
    def mouseReleaseEvent(self, event):
        # 在折叠状态下，忽略所有释放事件
        if self.current_state == self.COLLAPSED:
            return
        
        if event.button() == Qt.LeftButton:
            was_dragging = self.dragging
            self.dragging = False
            
            if self.current_state == self.DRAGGING:
                self.current_state = self.NORMAL
                self.update_character_display()
            
            # 检查是否靠近屏幕边缘，以便折叠
            # pos = self.pos()
            # if pos.x() < 20:  # 左边缘
            #     self.collapse_to_left()
            # elif pos.x() + self.width() > self.screen_geometry.width() - 20:  # 右边缘
            #     self.collapse_to_right()
            
            # 单击事件（非拖动）
            drag_distance = (event.globalPos() - self.drag_start_pos).manhattanLength()
            if not was_dragging or drag_distance < 5:
                # self.show_dialog()
                pass
            
            event.accept()
    
    def collapse_to_right(self):
        """折叠到屏幕右侧，旋转90度并只显示部分"""
        if self.current_state != self.COLLAPSED:
            logger.info("折叠角色到右侧")
            
            # 保存当前状态以便恢复
            self.normal_geometry = self.geometry()
            
            # 获取原始图像尺寸
            original_pixmap = self.tachie_manager.get_composite_image()
            original_width = original_pixmap.width()
            original_height = original_pixmap.height()
            
            # 估计头部位置（假设在图像的上1/3处）
            head_position = original_height // 3
            
            # 计算折叠后应该显示的宽度（70%在屏幕内，30%在屏幕外）
            visible_percent = 0.5
            collapsed_width = int(original_height * visible_percent)  # 旋转后高度变宽度
            
            # 设置动画组（并行执行）
            self.animation_group = QParallelAnimationGroup()
            
            # 1. 位置和大小动画
            geometry_animation = QPropertyAnimation(self, b"geometry")
            geometry_animation.setDuration(500)  # 500毫秒
            geometry_animation.setStartValue(self.geometry())
            
            # 计算折叠后的位置：右侧，头部居中
            screen_right = self.screen_geometry.width()
            # 计算y坐标，使头部在原来的窗口中间
            middle_y = self.y() + self.height() // 2
            collapsed_y = middle_y - head_position
            
            # 设置结束位置：部分在屏幕外
            end_x = screen_right - collapsed_width
            geometry_animation.setEndValue(QRect(end_x, collapsed_y, original_height, original_width))
            geometry_animation.setEasingCurve(QEasingCurve.OutCubic)
            
            # 添加到动画组
            self.animation_group.addAnimation(geometry_animation)
            
            # 连接动画完成信号
            self.animation_group.finished.connect(self._on_collapse_animation_finished)
            
            # 开始动画
            self.animation_group.start()
            
    def _on_collapse_animation_finished(self):
        """折叠动画完成后的处理"""
        # 更新状态
        self.current_state = self.COLLAPSED
        
        # 更新显示（旋转图像）
        original_pixmap = self.tachie_manager.get_composite_image()
        
        # 旋转图像90度
        transform = QTransform().rotate(270)
        rotated_pixmap = original_pixmap.transformed(transform, Qt.SmoothTransformation)
        
        # 设置旋转后的图像
        self.character_label.setPixmap(rotated_pixmap)
        self.character_label.setFixedSize(rotated_pixmap.size())
        
    def expand(self):
        """从折叠状态展开"""
        if self.current_state == self.COLLAPSED:
            logger.info("展开角色")
            
            # 设置动画组（并行执行）
            self.animation_group = QParallelAnimationGroup()
            
            # 1. 位置和大小动画
            geometry_animation = QPropertyAnimation(self, b"geometry")
            geometry_animation.setDuration(500)  # 500毫秒
            geometry_animation.setStartValue(self.geometry())
            geometry_animation.setEndValue(self.normal_geometry)
            geometry_animation.setEasingCurve(QEasingCurve.OutCubic)
            
            # 添加到动画组
            self.animation_group.addAnimation(geometry_animation)
            
            # 连接动画完成信号
            self.animation_group.finished.connect(self._on_expand_animation_finished)
            
            # 开始动画
            self.animation_group.start()
            
    def _on_expand_animation_finished(self):
        """展开动画完成后的处理"""
        # 更新状态
        self.current_state = self.NORMAL
        
        # 更新显示（恢复原始图像）
        self.update_character_display()

    
    def show_random_dialog(self):
        """显示随机对话"""
        if not self.dialog:
            self.dialog = DialogBox(self)
        
        # 设置随机表情
        import random
        emotions = self.tachie_manager.get_available_emotions()
        if emotions:
            random_emotion = random.choice(emotions)
            self.set_emotion(random_emotion, 5000)  # 5秒后恢复
        
        # 选择随机对话
        random_text = random.choice(APEIRIA_DIALOGUES)
        
        # 定位对话框在角色附近
        # dialog_x = self.x() + self.width()
        # if dialog_x + self.dialog.width() > self.screen_geometry.width():
        #     dialog_x = self.x() - self.dialog.width()
        
        # self.dialog.move(dialog_x, self.y())

        # 定位对话框在角色附近
        self.position_dialog()
        self.dialog.setText(random_text)
        self.dialog.show()
        
        # 未来TTS实现将在这里调用
        # self.dialog.speak(random_text, "voice/random_dialogue.wav")
    
    def show_dialog(self):
        """显示对话框"""
        if not self.dialog:
            self.dialog = DialogBox(self)
        
        # 设置随机表情
        import random
        emotions = self.tachie_manager.get_available_emotions()
        if emotions:
            random_emotion = random.choice(emotions)
            self.set_emotion(random_emotion, 5000)  # 5秒后恢复
        
        # 定位对话框在角色附近
        # dialog_x = self.x() + self.width()
        # if dialog_x + self.dialog.width() > self.screen_geometry.width():
        #     dialog_x = self.x() - self.dialog.width()
        
        # self.dialog.move(dialog_x, self.y())

        # 定位对话框在角色附近
        self.position_dialog()
        self.dialog.setText("你好！我是Apeiria！\n有什么可以帮助你的吗？")
        self.dialog.show()
        
        # 未来TTS实现将在这里调用
        # self.dialog.speak("你好！我是Apeiria！有什么可以帮助你的吗？", "voice/greeting.wav")

    def position_dialog(self):
        """根据立绘位置调整对话框位置"""
        if not self.dialog:
            return
            
        # 默认将对话框放在立绘右侧
        dialog_x = self.x() + self.width()
        dialog_y = self.y()
        
        # 如果右侧放不下，则放在左侧
        if dialog_x + self.dialog.width() > self.screen_geometry.width():
            dialog_x = self.x() - self.dialog.width()
        
        # 如果对话框底部超出屏幕，向上调整
        if dialog_y + self.dialog.height() > self.screen_geometry.height():
            dialog_y = self.screen_geometry.height() - self.dialog.height()

        # 如果顶部超出屏幕，向下调整
        if dialog_y < 0:
            dialog_y = 0
        
        # 如果左侧也放不下（立绘靠近左边缘），则放在立绘上方或下方
        if dialog_x < 0:
            dialog_x = max(0, self.x() + (self.width() - self.dialog.width()) // 2)
            
            # 尝试放在上方
            dialog_y = self.y() - self.dialog.height()
            
            # 如果上方放不下，则放在下方
            if dialog_y < 0:
                dialog_y = self.y() + self.height()
                
                # 如果下方也放不下，则放在可见的位置
                if dialog_y + self.dialog.height() > self.screen_geometry.height():
                    dialog_y = max(0, self.screen_geometry.height() - self.dialog.height())
        
        self.dialog.move(dialog_x, dialog_y)


if __name__ == "__main__":
    # config logging to console
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s - %(name)s - %(levelname)s] %(message)s")

    app = QApplication(sys.argv)
    character = AnimeCharacter()

    # 添加异常处理，确保keyboard库的监听线程能够正常退出
    try:
        sys.exit(app.exec_())
    except SystemExit:
        print("程序正常退出")
    finally:
        # 确保清理keyboard库的资源
        keyboard.unhook_all()