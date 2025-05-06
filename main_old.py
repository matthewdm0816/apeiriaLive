import os
import sys
import logging
import re # Keep re for tachie manager or other uses
from typing import List, Dict, Any, Union, Tuple, Optional, Callable # Keep these
import random # For random dialogs and emotions

from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, 
                             QDialog, QPushButton, QMenu, QGraphicsDropShadowEffect) # Added QMenu
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QTimer, QSize, QPoint, QParallelAnimationGroup, QEasingCurve
from PyQt5.QtGui import QMovie, QPixmap, QPainter, QTransform, QColor # Keep QColor for DialogBoxConfig

import keyboard

# Assuming tachie.py, dialog.py, pomodoro.py are in the same directory or Python path
import tachie 
from tachie import TACHIE_MANAGER_CLSMAP, TachieManager # Ensure TachieManager is imported if directly used
from dialog import APEIRIA_DIALOGUES, DialogBox, DialogBoxConfig, create_dialog
from pomodoro import PomodoroTimerDialog, PomodoroConfig

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
        self.drag_position: Optional[QPoint] = None
        self.drag_start_pos: Optional[QPoint] = None
        
        self.dialog_box: Optional[DialogBox] = None
        
        # 对话框
        self.dialog = None
        
        # 折叠动画
        # self.animation = QPropertyAnimation(self, b"geometry")
        # self.animation.setDuration(300)  # 300毫秒
        self.animation_group: Optional[QParallelAnimationGroup] = None
        self.normal_geometry: Optional[QRect] = self.geometry() # Store after initial move
        
        # 表情动画计时器
        self.emotion_timer = QTimer()
        self.emotion_timer.setSingleShot(True)
        self.emotion_timer.timeout.connect(self.reset_emotion)

        # Pomodoro Timer
        self.pomodoro_config = PomodoroConfig()
        self.pomodoro_timer_dialog: Optional[PomodoroTimerDialog] = None

        self.setup_hotkeys()
        
    def update_character_display(self):
        """更新角色显示"""
        if self.current_state == self.NORMAL:
            pixmap = self.tachie_manager.get_composite_image()
        elif self.current_state == self.DRAGGING:
            # 拖动时可以切换到不同的姿势
            original_base = self.tachie_manager.current_base
            original_emotion = self.tachie_manager.current_emotion
            self.tachie_manager.set_base_emotion_combination("豆豆眼拒绝") 
            pixmap = self.tachie_manager.get_composite_image()
            self.tachie_manager.set_base(original_base)
            self.tachie_manager.set_emotion(original_emotion)

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
            if self.current_state != self.COLLAPSED: # Collapsed state handles pixmap separately after animation
                self.character_label.setPixmap(pixmap)
                self.character_label.setFixedSize(pixmap.size()) # Ensure label matches pixmap
            return pixmap.size()
        
        logger.warning("Pixmap was null in update_character_display.")

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
        self.normal_geometry = self.geometry()
        
        # 显示窗口
        self.show()
    
    def set_emotion(self, emotion, duration=3000):
        """设置角色表情，持续指定时间后恢复"""
        logger.info(f"Setting emotion: {emotion} for base {self.tachie_manager.current_base}")
        if self.tachie_manager.set_emotion(emotion):
            self.update_character_display()
            # 设置计时器，恢复默认表情
            if duration > 0:
                self.emotion_timer.start(duration)
        else:
            logger.warning(f"Emotion '{emotion}' not found for current base '{self.tachie_manager.current_base}'.")

    
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
            self.dragging = True # Set dragging flag
            self.drag_start_pos = event.globalPos()
            self.drag_position = self.drag_start_pos - self.frameGeometry().topLeft()
            self.current_state = self.DRAGGING
            self.update_character_display() # Show dragging face
            event.accept()
        elif event.button() == Qt.RightButton:
            # 右键点击显示随机对话
            # self.show_random_dialog()
            self.show_context_menu(event.globalPos())
            event.accept()

    def show_context_menu(self, position: QPoint):
        menu = QMenu(self)

        random_dialog_action = menu.addAction("Say Something")
        random_dialog_action.triggered.connect(self.show_random_dialog)
        
        pomodoro_action_text = "Open Pomodoro Timer"
        if self.pomodoro_timer_dialog and self.pomodoro_timer_dialog.isVisible():
            pomodoro_action_text = "Focus Pomodoro Timer"
        
        pomodoro_action = menu.addAction(pomodoro_action_text)
        pomodoro_action.triggered.connect(self.toggle_pomodoro_timer)

        menu.addSeparator()
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.exit_application)
        menu.exec_(position)

    def toggle_pomodoro_timer(self):
        if not self.pomodoro_timer_dialog:
            self.pomodoro_timer_dialog = PomodoroTimerDialog(self, self.pomodoro_config)
            self.pomodoro_timer_dialog.pomodoro_session_finished.connect(self.on_pomodoro_session_finished)
            # self.pomodoro_timer_dialog.pomodoro_state_changed.connect(self.on_pomodoro_state_changed) # Optional

        if self.pomodoro_timer_dialog.isVisible():
            self.pomodoro_timer_dialog.activateWindow()
            self.pomodoro_timer_dialog.raise_()
        else:
            self.position_aux_dialog(self.pomodoro_timer_dialog)
            self.pomodoro_timer_dialog.show()
        logger.info("Toggled Pomodoro Timer visibility.")

    def on_pomodoro_session_finished(self, finished_state: str):
        logger.info(f"Character notified: Pomodoro session '{finished_state}' finished.")
        message = ""
        emotion_to_set = "普通"
        base_to_set = self.tachie_manager.current_base # Default to current base

        if finished_state == PomodoroTimerDialog.STATE_WORK:
            message = "主人，工作辛苦啦！休息一下吧～"
            if isinstance(self.tachie_manager, tachie.ApeiriaTachieManager):
                base_to_set = self.tachie_manager.get_positive_base() # e.g. "positive"
                emotion_to_set = "高兴" # Or "微笑"
            else: # Generic
                emotion_to_set = "高兴"
        elif finished_state in [PomodoroTimerDialog.STATE_SHORT_BREAK, PomodoroTimerDialog.STATE_LONG_BREAK]:
            message = "休息结束！打起精神来吧，主人！"
            if isinstance(self.tachie_manager, tachie.ApeiriaTachieManager):
                base_to_set = "normal" # Or current
                emotion_to_set = "微笑" # Or "干劲" if exists
            else: # Generic
                emotion_to_set = "微笑"
        
        if message:
            self.show_dialog_message(message, emotion=emotion_to_set, base=base_to_set, duration_ms=7000)
            self.activateWindow() # Bring character window to front
            self.raise_()
    
    def mouseMoveEvent(self, event):
        if self.current_state == self.DRAGGING and event.buttons() == Qt.LeftButton and self.drag_position:
            # Calculate the new top-left position
            new_top_left = event.globalPos() - self.drag_position
            
            # Clamp to screen boundaries
            gw = self.screen_geometry.width()
            gh = self.screen_geometry.height()
            ww = self.width()
            wh = self.height()

            new_x = max(0, min(new_top_left.x(), gw - ww))
            new_y = max(0, min(new_top_left.y(), gh - wh))
            
            corrected_new_pos = QPoint(new_x, new_y)
            delta = corrected_new_pos - self.pos() # Calculate actual delta after clamping
            self.move(corrected_new_pos)
            self.normal_geometry = self.geometry() # Update normal_geometry while dragging

            # Move dialogs if they are visible
            if self.dialog_box and self.dialog_box.isVisible():
                self.dialog_box.move(self.dialog_box.pos() + delta)
                self.position_aux_dialog(self.dialog_box) # Re-validate position
            
            if self.pomodoro_timer_dialog and self.pomodoro_timer_dialog.isVisible():
                self.pomodoro_timer_dialog.move(self.pomodoro_timer_dialog.pos() + delta)
                self.position_aux_dialog(self.pomodoro_timer_dialog) # Re-validate position

            event.accept()
    
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