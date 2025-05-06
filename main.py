# main.py
import os
import sys
import logging
import re 
import random 
from typing import List, Dict, Any, Union, Tuple, Optional, Callable 

from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, 
                             QDialog, QPushButton, QMenu, QGraphicsDropShadowEffect) 
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QTimer, QSize, QPoint, QParallelAnimationGroup, QEasingCurve
from PyQt5.QtGui import QMovie, QPixmap, QPainter, QTransform, QColor 

import keyboard

import tachie 
from tachie import TACHIE_MANAGER_CLSMAP, TachieManager, ApeiriaTachieManager # Ensure ApeiriaTachieManager is imported
from dialog import APEIRIA_DIALOGUES, DialogBox, DialogBoxConfig, create_dialog
from pomodoro import PomodoroTimerDialog, PomodoroConfig

logger = logging.getLogger(__name__)

# --- HotkeyExitMixin class (remains the same) ---
class HotkeyExitMixin:
    def setup_hotkeys(self):
        try:
            keyboard.add_hotkey('alt+f4', self.exit_application)
            keyboard.add_hotkey('ctrl+shift+x', self.exit_application)
            logger.info("热键已设置: Alt+F4 或 Ctrl+Shift+X 退出应用")
        except Exception as e:
            logger.error(f"设置热键失败: {e}. 可能需要管理员权限或检查是否有其他程序占用了热键。")

    def exit_application(self):
        logger.info("退出热键被触发，应用程序正在关闭...")
        QApplication.quit()


class AnimeCharacter(QMainWindow, HotkeyExitMixin):
    def __init__(self, tachie_manager_name="apeiria", window_size=(300, 500)):
        super().__init__()
        self.NORMAL = "normal"
        self.DRAGGING = "dragging"
        self.COLLAPSED = "collapsed"
        self.current_state = self.NORMAL

        self.window_size = window_size
        
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.tachie_manager_name = tachie_manager_name
        manager_base_dir = os.path.join("images", self.tachie_manager_name)

        try:
            self.tachie_manager: TachieManager = TACHIE_MANAGER_CLSMAP[self.tachie_manager_name](
                base_dir=manager_base_dir, 
                image_size=window_size
            )
        except KeyError:
            logger.error(f"立绘管理器 '{self.tachie_manager_name}' 未找到。将使用 'base' 作为备选。")
            self.tachie_manager_name = "base" 
            manager_base_dir = os.path.join("images", self.tachie_manager_name)
            self.tachie_manager = TACHIE_MANAGER_CLSMAP[self.tachie_manager_name](
                base_dir=manager_base_dir, 
                image_size=window_size
            )
        except Exception as e:
            logger.error(f"初始化立绘管理器 '{self.tachie_manager_name}' 失败: {e}", exc_info=True)
            raise

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget); layout.setContentsMargins(0,0,0,0)
        self.character_label = QLabel(); layout.addWidget(self.character_label)
        self.screen_geometry = QApplication.desktop().availableGeometry()
        self.initialize_ui()
        
        self.dragging = False
        self.drag_position: Optional[QPoint] = None
        self.drag_start_pos: Optional[QPoint] = None
        self.was_simple_click = False # Flag to track simple click for mouseReleaseEvent
        
        self.dialog_box: Optional[DialogBox] = None
        
        self.animation_group: Optional[QParallelAnimationGroup] = None
        self.normal_geometry: Optional[QRect] = self.geometry() 
        
        self.emotion_timer = QTimer(); self.emotion_timer.setSingleShot(True)
        self.emotion_timer.timeout.connect(self.reset_emotion)

        self.pomodoro_config = PomodoroConfig()
        self.pomodoro_timer_dialog: Optional[PomodoroTimerDialog] = None

        self.setup_hotkeys()

    # ... (update_character_display, initialize_ui, set_emotion, reset_emotion as before, ensure robust) ...
    def update_character_display(self):
        pixmap: Optional[QPixmap] = None
        # Store current base/emotion to restore if changed for specific state display
        original_base = self.tachie_manager.current_base
        original_emotion = self.tachie_manager.current_emotion
        
        try:
            if self.current_state == self.NORMAL:
                pixmap = self.tachie_manager.get_composite_image()
            elif self.current_state == self.DRAGGING:
                # ApeiriaTachieManager has "豆豆眼拒绝" as ("negative", "ジト目")
                if isinstance(self.tachie_manager, ApeiriaTachieManager): # Use specific manager
                    self.tachie_manager.set_base_emotion_combination("豆豆眼拒绝")
                else: # Fallback for generic manager
                    self.tachie_manager.set_base("negative") # Assuming negative base exists
                    self.tachie_manager.set_emotion("ジト目") # Assuming ジト目 emotion exists
                pixmap = self.tachie_manager.get_composite_image()
                # Restore original state for internal consistency if other methods read it
                self.tachie_manager.set_base(original_base)
                self.tachie_manager.set_emotion(original_emotion)
            elif self.current_state == self.COLLAPSED:
                # For collapsed state, the image itself isn't changed here,
                # but its rotation is handled in _on_collapse_animation_finished
                pixmap = self.tachie_manager.get_composite_image()

            if pixmap and not pixmap.isNull():
                if self.current_state != self.COLLAPSED: 
                    self.character_label.setPixmap(pixmap)
                    # Ensure label size matches pixmap to prevent cropping/empty space
                    self.character_label.setFixedSize(pixmap.size()) 
                return pixmap.size()
            else:
                logger.warning(f"获取图像为空，状态: {self.current_state}. 立绘管理器: {self.tachie_manager_name}")
        
        except Exception as e:
            logger.error(f"更新角色显示时出错，状态 {self.current_state}: {e}", exc_info=True)
            # Attempt a graceful fallback to default normal state
            try:
                self.tachie_manager.set_base("normal")
                self.tachie_manager.set_emotion("普通")
                pixmap = self.tachie_manager.get_composite_image()
                if pixmap and not pixmap.isNull():
                    self.character_label.setPixmap(pixmap)
                    self.character_label.setFixedSize(pixmap.size())
                    return pixmap.size()
            except Exception as fallback_e:
                logger.error(f"角色显示回退至默认状态亦失败: {fallback_e}")

        # Final fallback if all else fails
        self.character_label.clear() # Clear any potentially broken image
        self.character_label.setFixedSize(QSize(*self.window_size))
        logger.error(f"无法加载任何角色图像，已设置为空白区域。")
        return QSize(*self.window_size)


    def initialize_ui(self):
        pixmap_size = self.update_character_display()
        self.resize(pixmap_size) 
        x_pos = self.screen_geometry.width() - pixmap_size.width()
        y_pos = self.screen_geometry.height() - pixmap_size.height()
        self.move(x_pos, y_pos)
        self.normal_geometry = self.geometry()
        self.show()

    def set_emotion(self, emotion_name: str, duration_ms: int = 3000):
        current_base = self.tachie_manager.current_base
        logger.info(f"尝试设置表情: {emotion_name} (当前姿势: {current_base})")
        if self.tachie_manager.set_emotion(emotion_name): # set_emotion should check if valid for current base
            self.update_character_display()
            if duration_ms > 0:
                self.emotion_timer.start(duration_ms)
        else:
            logger.warning(f"表情 '{emotion_name}' 对当前姿势 '{current_base}' 无效或不存在。")
    
    def reset_emotion(self):
        self.emotion_timer.stop()
        default_emotion = "普通" 
        # Only reset if not already default, and if default emotion is valid for current base
        if self.tachie_manager.current_emotion != default_emotion:
            logger.info(f"重置表情为 '{default_emotion}'。")
            if self.tachie_manager.set_emotion(default_emotion):
                 self.update_character_display()
            else: # Should not happen if "普通" is always available per base
                 logger.warning(f"无法重置为默认表情 '{default_emotion}' (姿势: {self.tachie_manager.current_base})")


    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.was_simple_click = False # Double click is not a simple click
            if self.current_state == self.COLLAPSED:
                self.expand()
            elif self.current_state == self.NORMAL:
                self.collapse_to_right()
        event.accept()
    
    def mousePressEvent(self, event):
        self.was_simple_click = False # Reset flag
        if self.current_state == self.COLLAPSED:
            if event.button() == Qt.LeftButton:
                self.expand() # Allow expand on single click when collapsed
            event.accept()
            return
    
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start_pos = event.globalPos()
            self.drag_position = self.drag_start_pos - self.frameGeometry().topLeft()
            self.was_simple_click = True 
            event.accept()
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.globalPos())
            event.accept()

    def show_context_menu(self, position: QPoint):
        menu = QMenu(self)

        random_dialog_action = menu.addAction("说点什么 (Say Something)") # Updated to Chinese
        random_dialog_action.triggered.connect(self.show_random_dialog)
        
        pomodoro_action_text = "打开番茄钟 (Open Pomodoro)"
        if self.pomodoro_timer_dialog and self.pomodoro_timer_dialog.isVisible():
            pomodoro_action_text = "聚焦番茄钟 (Focus Pomodoro)"
        
        pomodoro_action = menu.addAction(pomodoro_action_text)
        pomodoro_action.triggered.connect(self.toggle_pomodoro_timer)

        # Placeholder for future settings for the character itself
        # settings_action = menu.addAction("角色设置 (Character Settings)")
        # settings_action.triggered.connect(self.open_character_settings) # Implement this if needed

        menu.addSeparator()
        exit_action = menu.addAction("退出 (Exit)")
        exit_action.triggered.connect(self.exit_application)
        menu.exec_(position)


    def mouseMoveEvent(self, event: Any):
        if event.buttons() == Qt.LeftButton and self.dragging and self.drag_start_pos and self.drag_position:
            # Check if movement exceeds drag threshold to differentiate from click
            if (event.globalPos() - self.drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                self.was_simple_click = False # It's a drag
                if self.current_state != self.DRAGGING: # Transition to dragging state only on actual drag
                    self.current_state = self.DRAGGING
                    self.update_character_display() # Show dragging face

            if self.current_state == self.DRAGGING: # Only move if in dragging state
                new_top_left = event.globalPos() - self.drag_position
                gw = self.screen_geometry.width(); gh = self.screen_geometry.height()
                ww = self.width(); wh = self.height()
                new_x = max(0, min(new_top_left.x(), gw - ww))
                new_y = max(0, min(new_top_left.y(), gh - wh))
                
                corrected_new_pos = QPoint(new_x, new_y)
                delta = corrected_new_pos - self.pos()
                self.move(corrected_new_pos)
                self.normal_geometry = self.geometry()

                if self.dialog_box and self.dialog_box.isVisible():
                    self.dialog_box.move(self.dialog_box.pos() + delta)
                    self.position_aux_dialog(self.dialog_box)
                
                if self.pomodoro_timer_dialog and self.pomodoro_timer_dialog.isVisible():
                    self.pomodoro_timer_dialog.move(self.pomodoro_timer_dialog.pos() + delta)
                    self.position_aux_dialog(self.pomodoro_timer_dialog)
            event.accept()
    
    def mouseReleaseEvent(self, event: Any):
        if self.current_state == self.COLLAPSED:
            event.accept()
            return
        
        if event.button() == Qt.LeftButton:
            if self.current_state == self.DRAGGING : # If we were actually dragging
                self.current_state = self.NORMAL
                self.update_character_display() # Revert to normal face
            
            if self.was_simple_click and self.current_state == self.NORMAL: # Check the flag
                logger.info("左键单击立绘，显示随机对话。")
                self.show_random_dialog()
            
            self.dragging = False
            self.was_simple_click = False
            self.drag_start_pos = None
            event.accept()


    def toggle_pomodoro_timer(self):
        if not self.pomodoro_timer_dialog:
            self.pomodoro_timer_dialog = PomodoroTimerDialog(self, self.pomodoro_config)
            self.pomodoro_timer_dialog.pomodoro_session_finished.connect(self.on_pomodoro_session_finished)
            self.pomodoro_timer_dialog.pomodoro_confirmation_required.connect(self.on_pomodoro_confirmation_required)
            self.pomodoro_timer_dialog.pomodoro_snooze_activated.connect(self.on_pomodoro_snooze_activated)

        if self.pomodoro_timer_dialog.isVisible():
            self.pomodoro_timer_dialog.activateWindow()
            self.pomodoro_timer_dialog.raise_()
        else:
            # --- MODIFIED SECTION for Pomodoro spawn location ---
            char_rect = self.geometry()
            screen_rect = self.screen_geometry
            pom_dw = self.pomodoro_timer_dialog.width()
            pom_dh = self.pomodoro_timer_dialog.height()

            # Default position: to the right of the character
            target_x = char_rect.right() + 10
            target_y = char_rect.top()

            # If chat dialog exists and is visible, position Pomodoro below it
            if self.dialog_box and self.dialog_box.isVisible():
                chat_rect = self.dialog_box.geometry()
                # Try to align Pomodoro left with chat dialog or character
                target_x = chat_rect.left() # Align with chat dialog's left
                target_y = chat_rect.bottom() + 5 # Position below chat dialog

                # Ensure it doesn't go off screen bottom
                if target_y + pom_dh > screen_rect.bottom():
                    # Try above chat dialog instead
                    target_y = chat_rect.top() - pom_dh - 5
                    if target_y < screen_rect.top(): # If above also fails, place beside character
                        target_x = char_rect.right() + 10
                        target_y = char_rect.top()


            # Screen boundary checks (common for both cases)
            # If right side (or current target_x) is off-screen, try left of character
            if target_x + pom_dw > screen_rect.right():
                target_x = char_rect.left() - pom_dw - 10
            
            # If left side is also off-screen
            if target_x < screen_rect.left():
                # Center horizontally relative to character, or at screen edge
                target_x = char_rect.left() + (char_rect.width() - pom_dw) // 2
                target_x = max(screen_rect.left(), min(target_x, screen_rect.right() - pom_dw))

            # Vertical clamping (if not already handled by "below chat" logic)
            if not (self.dialog_box and self.dialog_box.isVisible()): # Only apply general Y clamping if not positioned relative to chat
                if target_y + pom_dh > screen_rect.bottom():
                    target_y = screen_rect.bottom() - pom_dh
                if target_y < screen_rect.top():
                    target_y = screen_rect.top()
            else: # If positioned relative to chat, re-clamp Y if it went off screen due to chat's position
                target_y = max(screen_rect.top(), min(target_y, screen_rect.bottom() - pom_dh))


            self.pomodoro_timer_dialog.move(int(target_x), int(target_y))
            # --- END OF MODIFIED SECTION ---
            self.pomodoro_timer_dialog.show()
        logger.info("番茄钟计时器可见性已切换。")

    def on_pomodoro_session_finished(self, finished_state: str):
        logger.info(f"角色提示：番茄钟环节 '{finished_state}' 已计时完成。")
        apeiria_manager = isinstance(self.tachie_manager, ApeiriaTachieManager)
        
        emotion_to_set = "宽心" 
        if apeiria_manager and "脸红" in self.tachie_manager.get_available_emotions("positive"): # Check if "脸红" is valid for "positive" base
            emotion_to_set = random.choice(["宽心", "脸红"])
        base_to_set = self.tachie_manager.get_positive_base() if apeiria_manager else "positive" # Assume positive base exists

        if finished_state == PomodoroTimerDialog.STATE_WORK:
            dialog_options = [
                "主人，刚刚那段时间真是超级专注呢！太了不起了！✧٩(ˊωˋ*)و✧",
                "一段工作顺利完成！感觉是不是充满了成就感呀，主人？(〃∀〃)",
                "太棒啦！又攻克了一个任务小节！主人请准备迎接休息的犒劳吧～"
            ]
            self.show_dialog_message(random.choice(dialog_options), emotion=emotion_to_set, base=base_to_set, duration_ms=7000)
            self.activateWindow(); self.raise_()

    def on_pomodoro_confirmation_required(self, next_session_type_to_confirm: str):
        logger.info(f"角色提示：番茄钟需要确认为 '{next_session_type_to_confirm}' 开始。")
        message = ""; emotion_to_set = "普通"; base_to_set = "normal"
        apeiria_manager = isinstance(self.tachie_manager, ApeiriaTachieManager)

        if next_session_type_to_confirm == "work":
            dialog_options = [
                "主人，休息得心满意足了吗？新的挑战正等待着我们去征服哦！",
                "元气满满！Apeiria已经为主人调好了最佳工作状态，我们开始吧！",
                "休息时间到此结束～ 主人，是时候回到战场继续发光发热啦！"
            ]
            message = random.choice(dialog_options)
            base_to_set = "normal"
            emotion_choices = ["普通", "惊讶-好奇"]
            if "闭眼" in self.tachie_manager.get_available_emotions(base_to_set): emotion_choices.append("闭眼")
            emotion_to_set = random.choice(emotion_choices)
        
        elif next_session_type_to_confirm == "short_break":
            dialog_options = ["工作暂告一段落，主人是现在就享受应得的短休息，还是…？", "辛苦啦主人！短暂地放松一下眼睛和大脑吧！", "刚刚的工作很棒哦！现在是轻松一刻～"]
            message = random.choice(dialog_options)
            base_to_set = self.tachie_manager.get_positive_base() if apeiria_manager else "positive"
            emotion_choices = ["宽心"]
            if "脸红" in self.tachie_manager.get_available_emotions(base_to_set): emotion_choices.append("脸红")
            emotion_to_set = random.choice(emotion_choices)

        elif next_session_type_to_confirm == "long_break":
            dialog_options = ["主人已经连续完成了好几轮工作，真是太了不起了！现在是长时间的休息，请务必彻底放松哦！(｡♥‿♥｡)", "哇，已经到了长休息时间！主人可以去做些喜欢的事情！", "长时间的休憩是为了更好地前进，主人，请享受这段宝贵的恢复时光吧！"]
            message = random.choice(dialog_options)
            base_to_set = self.tachie_manager.get_positive_base() if apeiria_manager else "positive"
            emotion_choices = ["宽心"]
            if "脸红" in self.tachie_manager.get_available_emotions(base_to_set): emotion_choices.append("脸红")
            emotion_to_set = random.choice(emotion_choices)
        
        if message:
            self.show_dialog_message(message, emotion=emotion_to_set, base=base_to_set, duration_ms=10000)
            self.activateWindow(); self.raise_()
            if self.pomodoro_timer_dialog and self.pomodoro_timer_dialog.isVisible():
                self.pomodoro_timer_dialog.activateWindow(); self.pomodoro_timer_dialog.raise_()

    def on_pomodoro_snooze_activated(self, snoozed_original_session_type: str):
        logger.info(f"角色提示：番茄钟 '{snoozed_original_session_type}' 环节的开始已被拖延。")
        message = ""; emotion_to_set = "普通"; base_to_set = "normal"
        apeiria_manager = isinstance(self.tachie_manager, ApeiriaTachieManager)

        if snoozed_original_session_type == "work": # User chose to "摸鱼5分钟"
            dialog_options = ["欸嘿，稍微放松一下也是策略呢，主人～那就，再惬意五分钟好了！(ゝ∀･)", "收到！摸鱼模式启动！不过五分钟后，Apeiria会准时提醒主人的哦～ 😉", "了解～五分钟的额外休整时间！"]
            message = random.choice(dialog_options)
            base_to_set = "normal" # Or positive
            emotion_choices = ["ジト目", "闭眼"]
            if "脸红" in self.tachie_manager.get_available_emotions(base_to_set): emotion_choices.append("脸红")
            emotion_to_set = random.choice(emotion_choices)

        elif snoozed_original_session_type == "break": # User chose to "再卷5分钟"
            dialog_options = ["不愧是主人！还要再坚持一会儿吗？Apeiria会为主人加油的！Fighting! (๑•̀ㅂ•́)و✧", "燃烧起来了！主人要追加冲刺五分钟对吗？", "收到，主人！专注力MAX的最后五分钟！Apeiria全力应援！"]
            message = random.choice(dialog_options)
            base_to_set = self.tachie_manager.get_negative_base() if apeiria_manager else "negative"
            emotion_choices = ["普通", "小惊讶", "惊讶-好奇"]
            emotion_to_set = random.choice(emotion_choices)
            
        if message:
            self.show_dialog_message(message, emotion=emotion_to_set, base=base_to_set, duration_ms=7000)
            self.activateWindow(); self.raise_()

    def show_random_dialog(self):
        # Ensure tachie_manager is ApeiriaTachieManager or has similar methods if calling them
        apeiria_manager = isinstance(self.tachie_manager, ApeiriaTachieManager)
        
        # Pick a base, then pick an emotion valid for that base
        chosen_base = random.choice(["normal", "positive"])
        if not self.tachie_manager.set_base(chosen_base): # Ensure base is set
            chosen_base = "normal" # Fallback
            self.tachie_manager.set_base(chosen_base)

        available_emotions_for_base = self.tachie_manager.get_available_emotions(chosen_base)
        
        # Filter for generally positive/neutral random chat emotions
        suitable_emotions = ["普通", "宽心", "小失落", "小惊讶", "惊讶-好奇", "脸红", "闭眼", "ジト目"]
        valid_random_emotions = [e for e in suitable_emotions if e in available_emotions_for_base]
        
        if not valid_random_emotions: # Fallback if no suitable emotions found for the base
            valid_random_emotions = ["普通"] if "普通" in available_emotions_for_base else available_emotions_for_base
        
        random_emotion = random.choice(valid_random_emotions) if valid_random_emotions else "普通"
        
        random_text = random.choice(APEIRIA_DIALOGUES)
        self.show_dialog_message(random_text, emotion=random_emotion, base=chosen_base, duration_ms=6000)


    def show_dialog_message(self, text: str, emotion: Optional[str] = None, 
                            base: Optional[str] = None, duration_ms: int = 5000):
        
        original_base = self.tachie_manager.current_base
        base_changed = False

        if base and base != original_base:
            if self.tachie_manager.set_base(base):
                base_changed = True
                logger.info(f"对话框临时切换姿势为 {base}.")
            else:
                logger.warning(f"无法为对话框切换姿势到 {base}，将使用当前姿势 {original_base}.")
                # If base change failed, ensure current_base reflects the actual base for emotion setting
                self.tachie_manager.set_base(original_base) 
        
        # current_actual_base is what set_emotion will operate on
        current_actual_base = self.tachie_manager.current_base 
        final_emotion_to_set = "普通" # Default fallback

        if emotion:
            if emotion in self.tachie_manager.get_available_emotions(current_actual_base):
                final_emotion_to_set = emotion
            else:
                logger.warning(f"表情 '{emotion}' 对姿势 '{current_actual_base}' 无效。将尝试 '普通'。")
                if "普通" not in self.tachie_manager.get_available_emotions(current_actual_base) and self.tachie_manager.get_available_emotions(current_actual_base):
                    # If "普通" is also not available, pick the first available one for that base
                    final_emotion_to_set = self.tachie_manager.get_available_emotions(current_actual_base)[0]
                elif not self.tachie_manager.get_available_emotions(current_actual_base):
                     logger.error(f"姿势 '{current_actual_base}'没有任何可用表情!") # Should not happen
        
        # Set the determined emotion and trigger display update
        self.set_emotion(final_emotion_to_set, duration_ms) 
        # set_emotion already calls update_character_display, so no need to call it again here
        # unless base was changed and no emotion was specified (or specified emotion failed)

        if not self.dialog_box: # Create dialog if it doesn't exist
            # Pass the DialogBoxConfig for styling if your create_dialog supports it or DialogBox constructor.
            # For now, assuming DialogBox uses its default config.
            active_dialog_config = getattr(self, 'dialog_box_config', DialogBoxConfig())
            self.dialog_box = DialogBox(parent=self, text=text, config=active_dialog_config)
        else:
            self.dialog_box.setText(text)

        self.position_aux_dialog(self.dialog_box)
        self.dialog_box.show()
        self.dialog_box.activateWindow() 
        self.dialog_box.raise_()

    def position_aux_dialog(self, dialog_widget: QDialog):
        if not dialog_widget: return
        char_rect = self.geometry(); screen_rect = self.screen_geometry
        dw = dialog_widget.width(); dh = dialog_widget.height()
        pos_x = char_rect.right() + 10; pos_y = char_rect.top()
        if pos_x + dw > screen_rect.right(): pos_x = char_rect.left() - dw - 10
        if pos_x < screen_rect.left():
            pos_x = char_rect.left() + (char_rect.width() - dw) // 2
            pos_x = max(screen_rect.left(), min(pos_x, screen_rect.right() - dw))
            pos_y_above = char_rect.top() - dh - 10
            pos_y = pos_y_above if pos_y_above >= screen_rect.top() else char_rect.bottom() + 10
        if pos_y + dh > screen_rect.bottom(): pos_y = screen_rect.bottom() - dh
        if pos_y < screen_rect.top(): pos_y = screen_rect.top()
        dialog_widget.move(int(pos_x), int(pos_y))

    def show_dialog(self): # Default greeting
        greeting = "你好！我是Apeiria！\n有什么可以帮助你的吗？"
        self.show_dialog_message(greeting, emotion="普通", base="normal") # Default greeting expression


    def collapse_to_right(self):
        if self.current_state == self.COLLAPSED or \
           (self.animation_group and self.animation_group.state() == QPropertyAnimation.Running):
            return
        logger.info("正在向右折叠角色。")
        self.normal_geometry = self.geometry() 
        original_pixmap = self.tachie_manager.get_composite_image()
        if original_pixmap.isNull(): logger.error("无法折叠, 原始图像为空。"); return

        rotated_width = original_pixmap.height(); rotated_height = original_pixmap.width()
        visible_fraction = 0.33
        visible_width = int(rotated_width * visible_fraction)
        
        target_x = self.screen_geometry.width() - visible_width
        original_center_y = self.normal_geometry.top() + self.normal_geometry.height() // 2
        target_y = original_center_y - rotated_height // 2
        target_y = max(0, min(target_y, self.screen_geometry.height() - rotated_height))
        target_geom = QRect(target_x, target_y, rotated_width, rotated_height)

        self.animation_group = QParallelAnimationGroup(self)
        geom_anim = QPropertyAnimation(self, b"geometry")
        geom_anim.setDuration(300); geom_anim.setStartValue(self.normal_geometry)
        geom_anim.setEndValue(target_geom); geom_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation_group.addAnimation(geom_anim)
        self.animation_group.finished.connect(self._on_collapse_animation_finished)
        
        if self.dialog_box and self.dialog_box.isVisible(): 
            self.dialog_box.hide()
        if self.pomodoro_timer_dialog and self.pomodoro_timer_dialog.isVisible(): 
            self.pomodoro_timer_dialog.hide()
        self.current_state = self.COLLAPSED 
        self.animation_group.start()
        
    def _on_collapse_animation_finished(self):
        logger.info("折叠动画完成。")
        original_pixmap = self.tachie_manager.get_composite_image()
        if original_pixmap.isNull(): return
        transform = QTransform().rotate(270) 
        rotated_pixmap = original_pixmap.transformed(transform, Qt.SmoothTransformation)
        self.character_label.setPixmap(rotated_pixmap)
        self.character_label.setFixedSize(rotated_pixmap.size()) 

    def expand(self):
        if self.current_state != self.COLLAPSED or not self.normal_geometry or \
           (self.animation_group and self.animation_group.state() == QPropertyAnimation.Running):
            return
        logger.info("正在展开角色。")
        self.animation_group = QParallelAnimationGroup(self)
        geom_anim = QPropertyAnimation(self, b"geometry")
        geom_anim.setDuration(300); geom_anim.setStartValue(self.geometry())
        geom_anim.setEndValue(self.normal_geometry); geom_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation_group.addAnimation(geom_anim)
        self.animation_group.finished.connect(self._on_expand_animation_finished)
        self.animation_group.start()

    def _on_expand_animation_finished(self):
        logger.info("展开动画完成。")
        self.current_state = self.NORMAL
        self.update_character_display() 
        self.setFixedSize(self.normal_geometry.size())


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, 
        format="[%(asctime)s - %(name)s:%(lineno)d - %(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("desktop_assistant.log", mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stdout) 
        ]
    )
    logger.info("应用程序启动...")
    try:
        logger.info(f"'.' 的资源路径是: {tachie.resource_path('.')}")
        # logger.info(f"'images' 的资源路径是: {tachie.resource_path('images')}") # May fail if 'images' not at root with _MEIPASS
    except Exception as e:
        logger.error(f"resource_path 测试出错: {e}")

    app = QApplication(sys.argv)
    character_instance = None
    try:
        character_instance = AnimeCharacter(tachie_manager_name="apeiria") 
    except Exception as e:
        logger.critical(f"AnimeCharacter 初始化时发生致命错误: {e}", exc_info=True)
        error_msg_dialog = QDialog(); QVBoxLayout(error_msg_dialog)
        error_msg_dialog.setWindowTitle("初始化错误"); 
        error_msg_dialog.layout().addWidget(QLabel(f"无法启动应用:\n{e}\n\n请检查日志 (desktop_assistant.log)。"))
        btn_close = QPushButton("关闭"); btn_close.clicked.connect(app.quit) # type: ignore
        error_msg_dialog.layout().addWidget(btn_close)
        error_msg_dialog.exec_()
        sys.exit(1)

    exit_code = 0
    if character_instance:
        try:
            logger.info("启动应用程序事件循环。")
            exit_code = app.exec_()
            logger.info(f"应用程序事件循环结束，退出代码: {exit_code}")
        except SystemExit: logger.info("应用程序通过 SystemExit 退出。")
        except Exception as e: logger.critical(f"应用程序事件循环中发生未处理的异常: {e}", exc_info=True); exit_code = 1
        finally:
            logger.info("正在清理键盘钩子...")
            keyboard.unhook_all()
            logger.info(f"应用程序最终退出代码: {exit_code}")
    sys.exit(exit_code)