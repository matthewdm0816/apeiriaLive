# pomodoro.py
import logging
import re # Needed for parsing styles
from typing import Optional, Any

from PyQt5.QtWidgets import (QDialog, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
                             QProgressBar, QSpinBox, QFormLayout, QDialogButtonBox, QWidget,
                             QSizePolicy, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QTimer, QTime, pyqtSignal, QPoint, QRect, QSize
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QBrush, QPainterPath

# --- IMPORT DialogBoxConfig ---
# Ensure dialog.py is in the same directory or Python path
try:
    from dialog import DialogBoxConfig
except ImportError:
    logger = logging.getLogger(__name__)
    logger.error("CRITICAL: Cannot import DialogBoxConfig from dialog.py. Styling will fail.")
    # Define a fallback config to prevent immediate crash, but styling will be wrong
    class DialogBoxConfig:
        min_width = 300; min_height = 100; max_width = 400; padding = 15; corner_size = 10
        background_color = "#d4d0c8"; border_dark_color = "#404040"; border_light_color = "#ffffff"
        border_medium_color = "#808080"; text_color = "#000000"; title_color = "#000000"
        shadow_enabled = True; shadow_blur_radius = 15; shadow_color = QColor(0,0,0,180)
        shadow_offset_x = 5; shadow_offset_y = 5; title = "Fallback"; title_height = 30
        title_font = "Microsoft YaHei, Arial"; title_font_size = 10; close_button_text = "关闭"
        button_style = """ QPushButton { background-color: #d4d0c8; } """
        text_style = """ font-family: Microsoft YaHei, Arial; font-size: 14px; """

logger = logging.getLogger(__name__)


class PomodoroConfig:
    """番茄钟逻辑配置 (与视觉样式分离)"""
    def __init__(self):
        self.work_duration_minutes: int = 25
        self.short_break_minutes: int = 5
        self.long_break_minutes: int = 15
        self.cycles_before_long_break: int = 4
        self.snooze_duration_minutes: int = 5

    def get_work_duration_seconds(self) -> int: return self.work_duration_minutes * 60
    def get_short_break_seconds(self) -> int: return self.short_break_minutes * 60
    def get_long_break_seconds(self) -> int: return self.long_break_minutes * 60
    def get_snooze_duration_seconds(self) -> int: return self.snooze_duration_minutes * 60


class PomodoroTimerDialog(QDialog):
    """番茄钟对话框 (完全自定义绘制以匹配DialogBox风格)"""

    # --- States and Signals ---
    STATE_IDLE = "空闲"
    STATE_WORK = "工作中"
    STATE_SHORT_BREAK = "短时休息中"
    STATE_LONG_BREAK = "长时间休息中"
    STATE_WAITING_FOR_WORK_CONFIRMATION = "等待开始工作"
    STATE_WAITING_FOR_SHORT_BREAK_CONFIRMATION = "等待开始短休息"
    STATE_WAITING_FOR_LONG_BREAK_CONFIRMATION = "等待开始长休息"
    STATE_SNOOZING = "拖延中"

    pomodoro_state_changed = pyqtSignal(str, int)
    pomodoro_session_finished = pyqtSignal(str)
    pomodoro_confirmation_required = pyqtSignal(str)
    pomodoro_snooze_activated = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None,
                 pomodoro_logic_config: Optional[PomodoroConfig] = None,
                 dialog_style_config: Optional[DialogBoxConfig] = None):
        super().__init__(parent, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)

        self.logic_config = pomodoro_logic_config if pomodoro_logic_config else PomodoroConfig()
        self.style_config = dialog_style_config if dialog_style_config else DialogBoxConfig()

        self.setAttribute(Qt.WA_TranslucentBackground)

        self.current_state: str = self.STATE_IDLE
        self.cycles_completed: int = 0
        self.remaining_seconds: int = 0
        self.session_type_to_confirm_after_snooze: str = ""
        self.snoozed_original_session_type: str = ""

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer_countdown)
        self._drag_pos: Optional[QPoint] = None

        self._init_ui_widgets()
        self._apply_widget_styles()
        self.go_to_idle_state()

        # Calculate minimum size based on content + borders/title
        self._calculate_and_set_initial_size()

        if self.style_config.shadow_enabled:
            shadow = QGraphicsDropShadowEffect(self) # Parent it
            shadow.setBlurRadius(self.style_config.shadow_blur_radius)
            shadow.setColor(self.style_config.shadow_color)
            shadow.setOffset(self.style_config.shadow_offset_x, self.style_config.shadow_offset_y)
            self.setGraphicsEffect(shadow)

    def _calculate_and_set_initial_size(self):
        """ Estimates minimum needed size and sets initial dialog size """
        # Use layout's minimum size hint for a more accurate content height
        content_min_size = self.container_widget.layout().minimumSize()
        estimated_content_height = content_min_size.height()
        estimated_content_width = content_min_size.width()

        # Add space for custom title bar and borders/padding
        title_and_border_height = (self.style_config.title_height +
                                   self.style_config.padding * 2 + # Top/Bottom padding for title area
                                   (self.style_config.shadow_blur_radius // 2 if self.style_config.shadow_enabled else 0) * 2) # Approx border/shadow space

        border_width = (self.style_config.padding +
                        (self.style_config.shadow_blur_radius // 2 if self.style_config.shadow_enabled else 0)) * 2

        min_h = title_and_border_height + estimated_content_height + 10 # Add some extra margin
        min_w = max(self.style_config.min_width, border_width + estimated_content_width + 10)

        self.setMinimumSize(min_w, min_h)
        # Set initial size reasonably larger than minimum
        self.resize(max(min_w + 40, 380), max(min_h + 40, 350)) # Ensure a decent start size

    def _init_ui_widgets(self):
        self.container_widget = QWidget(self)
        # self.container_widget.setStyleSheet("background-color: rgba(0, 255, 0, 30);") # Debug Green

        main_layout = QVBoxLayout(self.container_widget)
        main_layout.setContentsMargins(self.style_config.padding // 2, self.style_config.padding // 2,
                                       self.style_config.padding // 2, self.style_config.padding // 2)
        main_layout.setSpacing(6)

        self.status_label = QLabel(f"状态: {self.current_state}")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        main_layout.addWidget(self.status_label)

        self.time_label = QLabel("00:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.time_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(16)
        main_layout.addWidget(self.progress_bar)

        self.cycles_label = QLabel(f"已完成轮次: 0/{self.logic_config.cycles_before_long_break}")
        self.cycles_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.cycles_label)

        self.main_action_button = QPushButton("开始工作")
        self.main_action_button.setMinimumHeight(28)
        self.main_action_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.main_action_button.clicked.connect(self.handle_main_action_button_click)
        main_layout.addWidget(self.main_action_button)

        secondary_controls_layout = QHBoxLayout(); secondary_controls_layout.setSpacing(6)
        self.snooze_button = QPushButton("再等5分钟")
        self.snooze_button.setMinimumHeight(25)
        self.snooze_button.clicked.connect(self.handle_snooze_button_click)
        secondary_controls_layout.addWidget(self.snooze_button)
        self.skip_button = QPushButton("跳过当前")
        self.skip_button.setMinimumHeight(25)
        self.skip_button.clicked.connect(self.handle_skip_button_click)
        secondary_controls_layout.addWidget(self.skip_button)
        main_layout.addLayout(secondary_controls_layout)

        tertiary_controls_layout = QHBoxLayout(); tertiary_controls_layout.setSpacing(6)
        self.reset_button = QPushButton("重置轮次")
        self.reset_button.setMinimumHeight(25)
        self.reset_button.clicked.connect(self.handle_reset_button_click)
        tertiary_controls_layout.addWidget(self.reset_button)
        self.settings_button = QPushButton("设置")
        self.settings_button.setMinimumHeight(25)
        self.settings_button.clicked.connect(self.handle_settings_button_click)
        tertiary_controls_layout.addWidget(self.settings_button)
        self.custom_close_button = QPushButton(self.style_config.close_button_text)
        self.custom_close_button.setMinimumHeight(25)
        self.custom_close_button.clicked.connect(self.reject) # reject() closes the dialog with Rejected status
        tertiary_controls_layout.addWidget(self.custom_close_button)
        main_layout.addLayout(tertiary_controls_layout)
        
        # Let the layout manage the spacing naturally unless needed otherwise
        # main_layout.addStretch(1) 


    def _apply_widget_styles(self):
        """Applies styles derived from DialogBoxConfig to internal widgets."""
        cfg = self.style_config
        font_family = "SimSun, Microsoft YaHei, Arial" # Default fallback
        base_font_size_pt = 10 # Default fallback

        # Extract font info more safely
        try:
            style_font_family = cfg.text_style.split("font-family:", 1)[1].split(";", 1)[0].strip()
            if style_font_family: font_family = style_font_family
        except IndexError: pass # Keep default if parsing fails

        try:
            style_font_size_str = cfg.text_style.split("font-size:", 1)[1].split(";", 1)[0].strip().lower()
            if 'px' in style_font_size_str:
                # Approximate conversion px to pt (common for UI design: 16px ~ 12pt)
                px_val = int(re.sub(r'[^\d]', '', style_font_size_str))
                base_font_size_pt = max(8, int(px_val * 0.75)) # Ensure minimum size
            elif 'pt' in style_font_size_str:
                base_font_size_pt = int(re.sub(r'[^\d]', '', style_font_size_str))
        except (IndexError, ValueError): pass # Keep default if parsing fails

        # Label Styling (QSS for general, QFont for specifics)
        label_qss = f"""
            QLabel {{
                color: {cfg.text_color};
                font-family: {font_family};
                font-size: {base_font_size_pt}pt;
                background-color: transparent;
            }}
        """
        self.setStyleSheet(label_qss)

        status_font = QFont(font_family.split(",")[0].strip().replace("'", ""), base_font_size_pt + 1)
        self.status_label.setFont(status_font)
        # Timer uses fixed font size for better layout stability
        timer_font = QFont("Arial", 36, QFont.Bold) # Keep timer large and clear
        self.time_label.setFont(timer_font)
        cycles_font = QFont(font_family.split(",")[0].strip().replace("'", ""), base_font_size_pt - 1)
        self.cycles_label.setFont(cycles_font)


        # Button Styling (Use QSS from config directly)
        # Make sure the button QSS includes font settings if desired, otherwise set font separately
        button_qss = cfg.button_style
        all_buttons = self.container_widget.findChildren(QPushButton)
        try: # Extract button font from QSS for QFont override if needed
             button_font_family = button_qss.split("font-family:", 1)[1].split(";", 1)[0].strip()
             button_font_size_str = button_qss.split("font-size:", 1)[1].split(";", 1)[0].strip().lower()
             if 'pt' in button_font_size_str: button_font_size_val = int(re.sub(r'[^\d]', '', button_font_size_str))
             elif 'px' in button_font_size_str: button_font_size_val = max(8, int(int(re.sub(r'[^\d]', '', button_font_size_str)) * 0.75))
             else: button_font_size_val = base_font_size_pt # Fallback
        except (IndexError, ValueError):
             button_font_family = font_family
             button_font_size_val = base_font_size_pt -1 # Slightly smaller for buttons

        for button in all_buttons:
            button.setStyleSheet(button_qss) # Apply the style sheet from DialogBoxConfig
            # Optional: Override font using QFont if QSS font handling is inconsistent
            button.setFont(QFont(button_font_family.split(",")[0].strip().replace("'", ""), button_font_size_val))

        # Special style for main button
        self.main_action_button.setFont(QFont(button_font_family.split(",")[0].strip().replace("'", ""), button_font_size_val + 1, QFont.Bold))


        # Progress Bar Styling
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {cfg.border_medium_color};
                background-color: {cfg.border_light_color};
                text-align: center;
                height: 16px;
                border-radius: 2px; /* Slight rounding */
            }}
            QProgressBar::chunk {{
                background-color: #0050a0; /* Classic blue */
                border-radius: 1px;
            }}
        """)


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        cfg = self.style_config
        
        # Adjust rect based on shadow offset IF shadow is enabled AND WA_TranslucentBackground is set
        # This ensures we paint within the non-shadow area.
        shadow_margin_x = self.style_config.shadow_offset_x if cfg.shadow_enabled else 0
        shadow_margin_y = self.style_config.shadow_offset_y if cfg.shadow_enabled else 0
        blur_radius_margin = cfg.shadow_blur_radius // 2 if cfg.shadow_enabled else 1 # Approx margin for blur

        # Adjust based on which side the shadow offsets towards (assuming positive offset means bottom-right)
        left_margin = blur_radius_margin - min(0, shadow_margin_x)
        top_margin = blur_radius_margin - min(0, shadow_margin_y)
        right_margin = blur_radius_margin + max(0, shadow_margin_x)
        bottom_margin = blur_radius_margin + max(0, shadow_margin_y)

        paint_rect = self.rect().adjusted(left_margin, top_margin, -right_margin, -bottom_margin)

        path = QPainterPath()
        corner = cfg.corner_size
        
        # Path with rounded corners using arcTo
        path.moveTo(paint_rect.left() + corner, paint_rect.top())
        path.lineTo(paint_rect.right() - corner, paint_rect.top())
        path.arcTo(paint_rect.right() - 2 * corner, paint_rect.top(), 2 * corner, 2 * corner, 90, -90)
        path.lineTo(paint_rect.right(), paint_rect.bottom() - corner)
        path.arcTo(paint_rect.right() - 2 * corner, paint_rect.bottom() - 2 * corner, 2 * corner, 2 * corner, 0, -90)
        path.lineTo(paint_rect.left() + corner, paint_rect.bottom())
        path.arcTo(paint_rect.left(), paint_rect.bottom() - 2 * corner, 2 * corner, 2 * corner, 270, -90)
        path.lineTo(paint_rect.left(), paint_rect.top() + corner)
        path.arcTo(paint_rect.left(), paint_rect.top(), 2 * corner, 2 * corner, 180, -90)
        path.closeSubpath()

        # Fill background
        painter.setBrush(QBrush(QColor(cfg.background_color)))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)

        # --- Draw 3D Border ---
        pen_light = QPen(QColor(cfg.border_light_color), 1)
        pen_dark = QPen(QColor(cfg.border_dark_color), 1)

        # Top Edge
        painter.setPen(pen_light)
        painter.drawLine(paint_rect.left() + corner, paint_rect.top(), paint_rect.right() - corner, paint_rect.top())
        # Left Edge
        painter.drawLine(paint_rect.left(), paint_rect.top() + corner, paint_rect.left(), paint_rect.bottom() - corner)
        # Bottom Edge
        painter.setPen(pen_dark)
        painter.drawLine(paint_rect.left() + corner, paint_rect.bottom(), paint_rect.right() - corner, paint_rect.bottom())
        # Right Edge
        painter.drawLine(paint_rect.right(), paint_rect.top() + corner, paint_rect.right(), paint_rect.bottom() - corner)

        # Draw corner arcs with appropriate pens for 3D effect
        # Top-Left (Light)
        painter.setPen(pen_light)
        painter.drawArc(paint_rect.left(), paint_rect.top(), 2 * corner, 2 * corner, 180 * 16, -90 * 16)
        # Top-Right (Dark on vertical, Light on horizontal - mimic bevel)
        # Simplification: Draw dark arc, may need more lines for true bevel
        painter.setPen(pen_dark)
        painter.drawArc(paint_rect.right() - 2 * corner, paint_rect.top(), 2 * corner, 2 * corner, 90 * 16, -90 * 16)
        # Bottom-Left (Dark on horizontal, Light on vertical - mimic bevel)
        # Simplification: Draw light arc
        painter.setPen(pen_light)
        painter.drawArc(paint_rect.left(), paint_rect.bottom() - 2 * corner, 2 * corner, 2 * corner, 270 * 16, -90 * 16)
        # Bottom-Right (Dark)
        painter.setPen(pen_dark)
        painter.drawArc(paint_rect.right() - 2 * corner, paint_rect.bottom() - 2 * corner, 2 * corner, 2 * corner, 0 * 16, -90 * 16)


        # Draw Title Text
        title_rect = QRect(paint_rect.left() + cfg.padding, paint_rect.top() + cfg.padding // 3,
                           paint_rect.width() - 2 * cfg.padding, cfg.title_height)
        painter.setPen(QColor(cfg.title_color))
        title_font_family = cfg.title_font.split(",")[0].strip().replace("'", "")
        painter.setFont(QFont(title_font_family if title_font_family else "Microsoft YaHei", cfg.title_font_size))
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, "番茄工作法计时器")

        # Draw Separator Line
        separator_y = paint_rect.top() + cfg.title_height + cfg.padding // 2
        # Dark line first
        painter.setPen(QPen(QColor(cfg.border_medium_color), 1))
        painter.drawLine(paint_rect.left() + cfg.padding, separator_y,
                         paint_rect.right() - cfg.padding, separator_y)
        # Light line below for 3D effect
        painter.setPen(QPen(QColor(cfg.border_light_color), 1))
        painter.drawLine(paint_rect.left() + cfg.padding, separator_y + 1,
                         paint_rect.right() - cfg.padding, separator_y + 1)


    def resizeEvent(self, event: Any): # type: ignore
        super().resizeEvent(event)
        cfg = self.style_config

        # Calculate margins for the container, considering shadow and desired padding
        shadow_margin_x_left = max(0, cfg.shadow_blur_radius // 2 - cfg.shadow_offset_x) if cfg.shadow_enabled else 1
        shadow_margin_y_top = max(0, cfg.shadow_blur_radius // 2 - cfg.shadow_offset_y) if cfg.shadow_enabled else 1
        shadow_margin_x_right = max(0, cfg.shadow_blur_radius // 2 + cfg.shadow_offset_x) if cfg.shadow_enabled else 1
        shadow_margin_y_bottom = max(0, cfg.shadow_blur_radius // 2 + cfg.shadow_offset_y) if cfg.shadow_enabled else 1

        # Total inset from dialog edge to where content container starts
        total_inset_x_left = shadow_margin_x_left + cfg.padding
        total_inset_y_top = shadow_margin_y_top + cfg.padding // 2 + cfg.title_height + cfg.padding // 2
        total_inset_x_right = shadow_margin_x_right + cfg.padding
        total_inset_y_bottom = shadow_margin_y_bottom + cfg.padding

        container_x = total_inset_x_left
        container_y = total_inset_y_top
        container_width = self.width() - total_inset_x_left - total_inset_x_right
        container_height = self.height() - total_inset_y_top - total_inset_y_bottom

        # Ensure non-negative dimensions
        container_width = max(0, container_width)
        container_height = max(0, container_height)

        self.container_widget.setGeometry(container_x, container_y, container_width, container_height)
        # logger.debug(f"Dialog resize: {self.size()}, Container geo: {self.container_widget.geometry()}")

    # --- Mouse Events for Dragging ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            shadow_margin_y_top = max(0, self.style_config.shadow_blur_radius // 2 - self.style_config.shadow_offset_y) if self.style_config.shadow_enabled else 1
            title_bar_bottom = shadow_margin_y_top + self.style_config.padding // 2 + self.style_config.title_height + self.style_config.padding // 2
            # Define clickable title bar bounds more precisely
            shadow_margin_x_left = max(0, self.style_config.shadow_blur_radius // 2 - self.style_config.shadow_offset_x) if self.style_config.shadow_enabled else 1
            shadow_margin_x_right = max(0, self.style_config.shadow_blur_radius // 2 + self.style_config.shadow_offset_x) if self.style_config.shadow_enabled else 1
            
            if event.y() >= shadow_margin_y_top and event.y() < title_bar_bottom \
               and event.x() >= shadow_margin_x_left and event.x() < self.width() - shadow_margin_x_right :
                    self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                    event.accept()
                    return
            # Allow clicks on widgets inside the container
            # Check if click is within container_widget bounds
            if self.container_widget.geometry().contains(event.pos()):
                 event.ignore() # Let children handle it
            else:
                 event.accept() # Consume clicks on the border/empty area
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos); event.accept()
        else: event.ignore()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_pos is not None:
            self._drag_pos = None; event.accept()
        else: event.ignore()

    # --- ALL LOGIC METHODS ---
    # (update_ui_for_current_state, update_timer_and_progress_display, update_cycles_display,
    #  set_time_for_state, handle_main_action_button_click, update_timer_countdown,
    #  process_timed_session_completion, handle_snooze_button_click, handle_skip_button_click,
    #  handle_reset_button_click, go_to_idle_state, transition_to_state,
    #  handle_settings_button_click, showEvent, closeEvent MUST BE COPIED HERE from the previous full version)
    def update_ui_for_current_state(self): # Ensure this method exists and is called
        self.status_label.setText(f"当前状态: {self.current_state}")
        self.snooze_button.setVisible(False) 
        self.skip_button.setText("跳过当前") 
        self.main_action_button.setEnabled(True)
        self.skip_button.setEnabled(True)

        is_timer_active = self.timer.isActive()

        if self.current_state == self.STATE_IDLE:
            self.main_action_button.setText("开始工作")
            self.skip_button.setEnabled(False)
        elif self.current_state in [self.STATE_WORK, self.STATE_SHORT_BREAK, self.STATE_LONG_BREAK, self.STATE_SNOOZING]:
            self.main_action_button.setText("暂停" if is_timer_active else "继续")
        elif self.current_state == self.STATE_WAITING_FOR_WORK_CONFIRMATION:
            self.main_action_button.setText("开始工作")
            self.snooze_button.setVisible(True)
            self.snooze_button.setText("摸鱼5分钟")
            self.skip_button.setText("跳过工作")
        elif self.current_state == self.STATE_WAITING_FOR_SHORT_BREAK_CONFIRMATION:
            self.main_action_button.setText("开始短休息")
            self.snooze_button.setVisible(True)
            self.snooze_button.setText("再卷5分钟")
            self.skip_button.setText("跳过短休息")
        elif self.current_state == self.STATE_WAITING_FOR_LONG_BREAK_CONFIRMATION:
            self.main_action_button.setText("开始长休息")
            self.snooze_button.setVisible(True)
            self.snooze_button.setText("再卷5分钟")
            self.skip_button.setText("跳过长休息")

        self.update_timer_and_progress_display()
        self.update_cycles_display()

    def update_timer_and_progress_display(self):
        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        self.time_label.setText(f"{minutes:02d}:{seconds:02d}")

        total_duration_for_progress = 0
        if self.current_state == self.STATE_WORK: total_duration_for_progress = self.logic_config.get_work_duration_seconds()
        elif self.current_state == self.STATE_SHORT_BREAK: total_duration_for_progress = self.logic_config.get_short_break_seconds()
        elif self.current_state == self.STATE_LONG_BREAK: total_duration_for_progress = self.logic_config.get_long_break_seconds()
        elif self.current_state == self.STATE_SNOOZING: total_duration_for_progress = self.logic_config.get_snooze_duration_seconds()

        if total_duration_for_progress > 0:
            progress = int(((total_duration_for_progress - self.remaining_seconds) / total_duration_for_progress) * 100)
            self.progress_bar.setValue(progress)
        else:
            self.progress_bar.setValue(0)

    def update_cycles_display(self):
        cycles_in_set = self.cycles_completed % self.logic_config.cycles_before_long_break
        total_for_long_break = self.logic_config.cycles_before_long_break
        self.cycles_label.setText(f"本大轮已完成: {cycles_in_set}/{total_for_long_break} (总计: {self.cycles_completed}轮)")

    def set_time_for_state(self, state_to_set_time_for: str):
        if state_to_set_time_for == self.STATE_WORK: self.remaining_seconds = self.logic_config.get_work_duration_seconds()
        elif state_to_set_time_for == self.STATE_SHORT_BREAK: self.remaining_seconds = self.logic_config.get_short_break_seconds()
        elif state_to_set_time_for == self.STATE_LONG_BREAK: self.remaining_seconds = self.logic_config.get_long_break_seconds()
        elif state_to_set_time_for == self.STATE_SNOOZING: self.remaining_seconds = self.logic_config.get_snooze_duration_seconds()
        elif state_to_set_time_for == self.STATE_IDLE: self.remaining_seconds = self.logic_config.get_work_duration_seconds()
        else: 
            if state_to_set_time_for == self.STATE_WAITING_FOR_WORK_CONFIRMATION: self.remaining_seconds = self.logic_config.get_work_duration_seconds()
            elif state_to_set_time_for == self.STATE_WAITING_FOR_SHORT_BREAK_CONFIRMATION: self.remaining_seconds = self.logic_config.get_short_break_seconds()
            elif state_to_set_time_for == self.STATE_WAITING_FOR_LONG_BREAK_CONFIRMATION: self.remaining_seconds = self.logic_config.get_long_break_seconds()
        # Update display immediately after setting time
        self.update_timer_and_progress_display() 

    def handle_main_action_button_click(self):
        logger.debug(f"主操作按钮点击。当前状态: {self.current_state}, 计时器活动: {self.timer.isActive()}")
        
        if self.current_state == self.STATE_IDLE:
            self.transition_to_state(self.STATE_WORK, start_timer=True)
        elif self.current_state in [self.STATE_WORK, self.STATE_SHORT_BREAK, self.STATE_LONG_BREAK, self.STATE_SNOOZING]:
            if self.timer.isActive():
                self.timer.stop()
                logger.info(f"计时器已暂停: {self.current_state}")
            else: 
                if self.remaining_seconds > 0:
                    self.timer.start(1000)
                    logger.info(f"计时器已继续: {self.current_state}")
        elif self.current_state == self.STATE_WAITING_FOR_WORK_CONFIRMATION:
            self.transition_to_state(self.STATE_WORK, start_timer=True)
        elif self.current_state == self.STATE_WAITING_FOR_SHORT_BREAK_CONFIRMATION:
            self.transition_to_state(self.STATE_SHORT_BREAK, start_timer=True)
        elif self.current_state == self.STATE_WAITING_FOR_LONG_BREAK_CONFIRMATION:
            self.transition_to_state(self.STATE_LONG_BREAK, start_timer=True)
        
        self.update_ui_for_current_state() 

    def update_timer_countdown(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            if self.timer.isActive():
                 self.pomodoro_state_changed.emit(self.current_state, self.remaining_seconds)
        
        if self.remaining_seconds <= 0: 
            if self.timer.isActive(): 
                self.timer.stop()
                self.process_timed_session_completion()
        
        self.update_ui_for_current_state() 


    def process_timed_session_completion(self):
        finished_session = self.current_state
        logger.info(f"计时环节结束: {finished_session}")
        
        if finished_session in [self.STATE_WORK, self.STATE_SHORT_BREAK, self.STATE_LONG_BREAK]:
            self.pomodoro_session_finished.emit(finished_session)

        next_confirmation_type = ""
        new_state_after_completion = self.STATE_IDLE 

        if finished_session == self.STATE_WORK:
            self.cycles_completed += 1
            if self.cycles_completed > 0 and self.cycles_completed % self.logic_config.cycles_before_long_break == 0:
                new_state_after_completion = self.STATE_WAITING_FOR_LONG_BREAK_CONFIRMATION
                next_confirmation_type = "long_break"
            else:
                new_state_after_completion = self.STATE_WAITING_FOR_SHORT_BREAK_CONFIRMATION
                next_confirmation_type = "short_break"
        elif finished_session in [self.STATE_SHORT_BREAK, self.STATE_LONG_BREAK]:
            new_state_after_completion = self.STATE_WAITING_FOR_WORK_CONFIRMATION
            next_confirmation_type = "work"
        elif finished_session == self.STATE_SNOOZING:
            if self.session_type_to_confirm_after_snooze == "work": new_state_after_completion = self.STATE_WAITING_FOR_WORK_CONFIRMATION
            elif self.session_type_to_confirm_after_snooze == "short_break": new_state_after_completion = self.STATE_WAITING_FOR_SHORT_BREAK_CONFIRMATION
            elif self.session_type_to_confirm_after_snooze == "long_break": new_state_after_completion = self.STATE_WAITING_FOR_LONG_BREAK_CONFIRMATION
            next_confirmation_type = self.session_type_to_confirm_after_snooze
        
        self.transition_to_state(new_state_after_completion, start_timer=False)
        if next_confirmation_type:
            self.pomodoro_confirmation_required.emit(next_confirmation_type)

    def handle_snooze_button_click(self):
        snooze_applied_to = "" 
        if self.current_state == self.STATE_WAITING_FOR_WORK_CONFIRMATION:
            self.session_type_to_confirm_after_snooze = "work"; snooze_applied_to = "work"
        elif self.current_state == self.STATE_WAITING_FOR_SHORT_BREAK_CONFIRMATION:
            self.session_type_to_confirm_after_snooze = "short_break"; snooze_applied_to = "break"
        elif self.current_state == self.STATE_WAITING_FOR_LONG_BREAK_CONFIRMATION:
            self.session_type_to_confirm_after_snooze = "long_break"; snooze_applied_to = "break"
        else: logger.warning(f"拖延按钮在无效状态下点击: {self.current_state}"); return

        self.transition_to_state(self.STATE_SNOOZING, start_timer=True)
        logger.info(f"环节已拖延 ({self.logic_config.snooze_duration_minutes}分钟). 下一个确认: {self.session_type_to_confirm_after_snooze}")
        if snooze_applied_to: self.pomodoro_snooze_activated.emit(snooze_applied_to)

    def handle_skip_button_click(self):
        logger.info(f"跳过按钮点击。当前状态: {self.current_state}")
        self.timer.stop()
        current_active_session_state = self.current_state
        if current_active_session_state in [self.STATE_WORK, self.STATE_SHORT_BREAK, self.STATE_LONG_BREAK, self.STATE_SNOOZING]:
            self.remaining_seconds = 0; self.process_timed_session_completion() 
        elif current_active_session_state == self.STATE_WAITING_FOR_WORK_CONFIRMATION:
            self.pomodoro_session_finished.emit(self.STATE_WORK); self.cycles_completed +=1 
            if self.cycles_completed % self.logic_config.cycles_before_long_break == 0:
                self.transition_to_state(self.STATE_WAITING_FOR_LONG_BREAK_CONFIRMATION); self.pomodoro_confirmation_required.emit("long_break")
            else: self.transition_to_state(self.STATE_WAITING_FOR_SHORT_BREAK_CONFIRMATION); self.pomodoro_confirmation_required.emit("short_break")
        elif current_active_session_state in [self.STATE_WAITING_FOR_SHORT_BREAK_CONFIRMATION, self.STATE_WAITING_FOR_LONG_BREAK_CONFIRMATION]:
            original_break_type = self.STATE_SHORT_BREAK if current_active_session_state == self.STATE_WAITING_FOR_SHORT_BREAK_CONFIRMATION else self.STATE_LONG_BREAK
            self.pomodoro_session_finished.emit(original_break_type)
            self.transition_to_state(self.STATE_WAITING_FOR_WORK_CONFIRMATION); self.pomodoro_confirmation_required.emit("work")
        logger.info(f"环节已跳过. 当前状态更新为: {self.current_state}")

    def handle_reset_button_click(self):
        self.timer.stop(); self.cycles_completed = 0; self.go_to_idle_state()
        self.pomodoro_state_changed.emit(self.current_state, self.remaining_seconds) 
        logger.info("番茄钟已完全重置。")

    def go_to_idle_state(self):
        self.transition_to_state(self.STATE_IDLE, start_timer=False)

    def transition_to_state(self, new_state: str, start_timer: bool = False):
        logger.debug(f"状态转换: 从 {self.current_state} 到 {new_state}, 启动计时器: {start_timer}")
        self.current_state = new_state
        self.set_time_for_state(new_state) 
        if start_timer and self.remaining_seconds > 0:
            self.timer.start(1000)
            # Only emit state changed if timer actually starts counting down
            self.pomodoro_state_changed.emit(self.current_state, self.remaining_seconds)
        elif not start_timer: self.timer.stop()
        # Reset progress unless resuming an active timer
        if not (start_timer and self.current_state in [self.STATE_WORK, self.STATE_SHORT_BREAK, self.STATE_LONG_BREAK, self.STATE_SNOOZING]):
             self.progress_bar.setValue(0)
        self.update_ui_for_current_state()

    def handle_settings_button_click(self):
        timer_was_active = self.timer.isActive()
        if timer_was_active: self.timer.stop()
        settings_dialog = PomodoroSettingsDialog(self.logic_config, self.style_config, self)
        if settings_dialog.exec_():
            self.logic_config = settings_dialog.get_logic_config()
            logger.info("番茄钟设置已更新。")
            current_is_non_timed_state = self.current_state in [self.STATE_IDLE, self.STATE_WAITING_FOR_WORK_CONFIRMATION, self.STATE_WAITING_FOR_SHORT_BREAK_CONFIRMATION, self.STATE_WAITING_FOR_LONG_BREAK_CONFIRMATION]
            if current_is_non_timed_state: self.set_time_for_state(self.current_state)
            elif self.current_state == self.STATE_SNOOZING: self.set_time_for_state(self.STATE_SNOOZING)
            self.update_ui_for_current_state() 
        if timer_was_active and self.current_state not in [self.STATE_IDLE, self.STATE_WAITING_FOR_WORK_CONFIRMATION, self.STATE_WAITING_FOR_SHORT_BREAK_CONFIRMATION, self.STATE_WAITING_FOR_LONG_BREAK_CONFIRMATION] and self.remaining_seconds > 0 :
            self.timer.start(1000)

    def showEvent(self, event):
        super().showEvent(event)
        self.update_ui_for_current_state()
        if self.current_state == self.STATE_IDLE and self.remaining_seconds == 0: self.go_to_idle_state()

    def closeEvent(self, event: Any): # type: ignore
        logger.info("番茄钟对话框已关闭。")
        super().closeEvent(event)
    # --- END OF LOGIC METHODS ---

class PomodoroSettingsDialog(QDialog):
    # --- This class remains exactly the same as provided in the previous answer ---
    # It already includes frameless, custom paint, dragging, uses DialogBoxConfig,
    # and layout fixes. Ensure the full code for it is used.
    def __init__(self, current_logic_config: PomodoroConfig, 
                 current_style_config: DialogBoxConfig, 
                 parent: Optional[QWidget] = None):
        super().__init__(parent, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        
        self.new_logic_config = PomodoroConfig() 
        self.new_logic_config.work_duration_minutes = current_logic_config.work_duration_minutes
        self.new_logic_config.short_break_minutes = current_logic_config.short_break_minutes
        self.new_logic_config.long_break_minutes = current_logic_config.long_break_minutes
        self.new_logic_config.cycles_before_long_break = current_logic_config.cycles_before_long_break
        self.new_logic_config.snooze_duration_minutes = current_logic_config.snooze_duration_minutes
        
        self.style_config = current_style_config 
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._drag_pos: Optional[QPoint] = None

        self._init_settings_ui_widgets()
        self._apply_settings_dialog_style()

        est_content_h = 5 * 25 + 4 * 6 + 30 
        title_border_h = self.style_config.title_height + (self.style_config.padding * 2) + (self.style_config.shadow_blur_radius // 2 if self.style_config.shadow_enabled else 0) * 2
        min_sh = title_border_h + est_content_h + 20

        self.setMinimumSize(max(self.style_config.min_width - 20, 340), min_sh)
        self.resize(max(self.style_config.min_width, 360), min_sh + 20)

        if self.style_config.shadow_enabled:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(self.style_config.shadow_blur_radius)
            shadow.setColor(self.style_config.shadow_color); shadow.setOffset(self.style_config.shadow_offset_x, self.style_config.shadow_offset_y)
            self.setGraphicsEffect(shadow)

    def _init_settings_ui_widgets(self):
        self.container_widget = QWidget(self) 
        layout = QFormLayout(self.container_widget)
        layout.setLabelAlignment(Qt.AlignTrailing)
        layout.setRowWrapPolicy(QFormLayout.DontWrapRows) 
        layout.setContentsMargins(self.style_config.padding // 2, self.style_config.padding // 2, 
                                   self.style_config.padding // 2, self.style_config.padding // 2)
        layout.setSpacing(6)

        self.work_spinbox = QSpinBox(); self.work_spinbox.setRange(1, 120); self.work_spinbox.setValue(self.new_logic_config.work_duration_minutes)
        layout.addRow("工作时长 (分钟):", self.work_spinbox)

        self.short_break_spinbox = QSpinBox(); self.short_break_spinbox.setRange(1, 60); self.short_break_spinbox.setValue(self.new_logic_config.short_break_minutes)
        layout.addRow("短休息时长 (分钟):", self.short_break_spinbox)

        self.long_break_spinbox = QSpinBox(); self.long_break_spinbox.setRange(1, 120); self.long_break_spinbox.setValue(self.new_logic_config.long_break_minutes)
        layout.addRow("长休息时长 (分钟):", self.long_break_spinbox)

        self.cycles_spinbox = QSpinBox(); self.cycles_spinbox.setRange(1, 10); self.cycles_spinbox.setValue(self.new_logic_config.cycles_before_long_break)
        layout.addRow("长休息前轮次:", self.cycles_spinbox)

        self.snooze_spinbox = QSpinBox(); self.snooze_spinbox.setRange(1, 30); self.snooze_spinbox.setValue(self.new_logic_config.snooze_duration_minutes)
        layout.addRow("拖延单位 (分钟):", self.snooze_spinbox)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("确定")
        self.button_box.button(QDialogButtonBox.Cancel).setText("取消")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)

    def _apply_settings_dialog_style(self):
        cfg = self.style_config 
        font_family = "SimSun, Microsoft YaHei, Arial"; base_font_size_pt = 10
        try:
            style_font_family = cfg.text_style.split("font-family:", 1)[1].split(";", 1)[0].strip(); font_family = style_font_family if style_font_family else font_family
            style_font_size_str = cfg.text_style.split("font-size:", 1)[1].split(";", 1)[0].strip().lower()
            if 'px' in style_font_size_str: base_font_size_pt = max(8, int(int(re.sub(r'[^\d]', '', style_font_size_str)) * 0.75))
            elif 'pt' in style_font_size_str: base_font_size_pt = int(re.sub(r'[^\d]', '', style_font_size_str))
        except Exception: pass

        common_widget_style = f""" color: {cfg.text_color}; font-family: {font_family}; font-size: {base_font_size_pt -1}pt; background: transparent; """
        self.container_widget.setStyleSheet(f""" QLabel {{ {common_widget_style} }} QSpinBox {{ color: {cfg.text_color}; font-family: {font_family}; font-size: {base_font_size_pt -1}pt; background-color: {cfg.border_light_color}; border: 1px solid {cfg.border_medium_color}; padding: 1px 2px; min-height: 20px; }} /* QPushButton styling will be inherited or set below */ """)
        for button in self.button_box.findChildren(QPushButton):
            button.setStyleSheet(cfg.button_style)
            try:
                 button_font_family = cfg.button_style.split("font-family:", 1)[1].split(";", 1)[0].strip(); button_font_size_str = cfg.button_style.split("font-size:", 1)[1].split(";", 1)[0].strip().lower()
                 if 'pt' in button_font_size_str: button_font_size_val = int(re.sub(r'[^\d]', '', button_font_size_str))
                 elif 'px' in button_font_size_str: button_font_size_val = max(8, int(int(re.sub(r'[^\d]', '', button_font_size_str)) * 0.75))
                 else: button_font_size_val = base_font_size_pt -1
                 button.setFont(QFont(button_font_family.split(",")[0].strip().replace("'", ""), button_font_size_val))
            except Exception: pass # Use QSS font if parsing fails

    def paintEvent(self, event): 
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing); cfg = self.style_config
        shadow_margin_x = cfg.shadow_offset_x if cfg.shadow_enabled else 0; shadow_margin_y = cfg.shadow_offset_y if cfg.shadow_enabled else 0
        blur_radius_margin = cfg.shadow_blur_radius // 2 if cfg.shadow_enabled else 1
        left_margin = blur_radius_margin - min(0, shadow_margin_x); top_margin = blur_radius_margin - min(0, shadow_margin_y)
        right_margin = blur_radius_margin + max(0, shadow_margin_x); bottom_margin = blur_radius_margin + max(0, shadow_margin_y)
        paint_rect = self.rect().adjusted(left_margin, top_margin, -right_margin, -bottom_margin)

        path = QPainterPath(); corner = cfg.corner_size
        path.moveTo(paint_rect.left() + corner, paint_rect.top()); path.lineTo(paint_rect.right() - corner, paint_rect.top())
        path.arcTo(paint_rect.right() - 2 * corner, paint_rect.top(), 2 * corner, 2 * corner, 90, -90)
        path.lineTo(paint_rect.right(), paint_rect.bottom() - corner)
        path.arcTo(paint_rect.right() - 2 * corner, paint_rect.bottom() - 2 * corner, 2 * corner, 2 * corner, 0, -90)
        path.lineTo(paint_rect.left() + corner, paint_rect.bottom())
        path.arcTo(paint_rect.left(), paint_rect.bottom() - 2 * corner, 2 * corner, 2 * corner, 270, -90)
        path.lineTo(paint_rect.left(), paint_rect.top() + corner)
        path.arcTo(paint_rect.left(), paint_rect.top(), 2 * corner, 2 * corner, 180, -90); path.closeSubpath()

        painter.setBrush(QBrush(QColor(cfg.background_color))); painter.setPen(Qt.NoPen); painter.drawPath(path)
        pen_light = QPen(QColor(cfg.border_light_color), 1); pen_dark = QPen(QColor(cfg.border_dark_color), 1)
        painter.setPen(pen_light); painter.drawLine(paint_rect.left() + corner, paint_rect.top(), paint_rect.right() - corner, paint_rect.top()); painter.drawLine(paint_rect.left(), paint_rect.top() + corner, paint_rect.left(), paint_rect.bottom() - corner)
        painter.setPen(pen_dark); painter.drawLine(paint_rect.left() + corner, paint_rect.bottom(), paint_rect.right() - corner, paint_rect.bottom()); painter.drawLine(paint_rect.right(), paint_rect.top() + corner, paint_rect.right(), paint_rect.bottom() - corner)
        painter.setPen(pen_light); painter.drawArc(paint_rect.left(), paint_rect.top(), 2 * corner, 2 * corner, 180 * 16, -90 * 16)
        painter.setPen(pen_dark); painter.drawArc(paint_rect.right() - 2 * corner, paint_rect.top(), 2 * corner, 2 * corner, 90 * 16, -90 * 16)
        painter.setPen(pen_light); painter.drawArc(paint_rect.left(), paint_rect.bottom() - 2 * corner, 2 * corner, 2 * corner, 270 * 16, -90 * 16)
        painter.setPen(pen_dark); painter.drawArc(paint_rect.right() - 2 * corner, paint_rect.bottom() - 2 * corner, 2 * corner, 2 * corner, 0 * 16, -90 * 16)

        title_rect = QRect(paint_rect.left() + cfg.padding, paint_rect.top() + cfg.padding // 3, paint_rect.width() - 2 * cfg.padding, cfg.title_height)
        painter.setPen(QColor(cfg.title_color)); title_font_family = cfg.title_font.split(",")[0].strip().replace("'", "")
        painter.setFont(QFont(title_font_family if title_font_family else "Microsoft YaHei", cfg.title_font_size))
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, "番茄钟设置") 
        separator_y = paint_rect.top() + cfg.title_height + cfg.padding // 2
        painter.setPen(QPen(QColor(cfg.border_medium_color), 1)); painter.drawLine(paint_rect.left() + cfg.padding, separator_y, paint_rect.right() - cfg.padding, separator_y)
        painter.setPen(QPen(QColor(cfg.border_light_color), 1)); painter.drawLine(paint_rect.left() + cfg.padding, separator_y + 1, paint_rect.right() - cfg.padding, separator_y + 1)


    def resizeEvent(self, event: Any): # type: ignore
        super().resizeEvent(event)
        cfg = self.style_config
        shadow_margin_x_left = max(0, cfg.shadow_blur_radius // 2 - cfg.shadow_offset_x) if cfg.shadow_enabled else 1
        shadow_margin_y_top = max(0, cfg.shadow_blur_radius // 2 - cfg.shadow_offset_y) if cfg.shadow_enabled else 1
        shadow_margin_x_right = max(0, cfg.shadow_blur_radius // 2 + cfg.shadow_offset_x) if cfg.shadow_enabled else 1
        shadow_margin_y_bottom = max(0, cfg.shadow_blur_radius // 2 + cfg.shadow_offset_y) if cfg.shadow_enabled else 1

        title_area_total_height = cfg.padding // 2 + cfg.title_height + cfg.padding # Approx total height used by title area
        
        container_x = shadow_margin_x_left + cfg.padding // 2
        container_y = shadow_margin_y_top + title_area_total_height
        container_width = self.width() - shadow_margin_x_left - shadow_margin_x_right - cfg.padding
        container_height = self.height() - shadow_margin_y_top - title_area_total_height - shadow_margin_y_bottom - cfg.padding // 2

        container_width = max(0, container_width); container_height = max(0, container_height)
        self.container_widget.setGeometry(container_x, container_y, container_width, container_height)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            shadow_margin_y_top = max(0, self.style_config.shadow_blur_radius // 2 - self.style_config.shadow_offset_y) if self.style_config.shadow_enabled else 1
            title_bar_clickable_height = shadow_margin_y_top + self.style_config.padding // 2 + self.style_config.title_height + self.style_config.padding // 2
            shadow_margin_x_left = max(0, self.style_config.shadow_blur_radius // 2 - self.style_config.shadow_offset_x) if self.style_config.shadow_enabled else 1
            shadow_margin_x_right = max(0, self.style_config.shadow_blur_radius // 2 + self.style_config.shadow_offset_x) if self.style_config.shadow_enabled else 1
            if event.y() >= shadow_margin_y_top and event.y() < title_bar_clickable_height and event.x() >= shadow_margin_x_left and event.x() < self.width() - shadow_margin_x_right :
                 self._drag_pos = event.globalPos() - self.frameGeometry().topLeft(); event.accept(); return
            if self.container_widget.geometry().contains(event.pos()): event.ignore()
            else: event.accept() 
        else: event.ignore()
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None: self.move(event.globalPos() - self._drag_pos); event.accept()
        else: event.ignore()
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_pos is not None: self._drag_pos = None; event.accept()
        else: event.ignore()

    def accept(self):
        self.new_logic_config.work_duration_minutes = self.work_spinbox.value()
        self.new_logic_config.short_break_minutes = self.short_break_spinbox.value()
        self.new_logic_config.long_break_minutes = self.long_break_spinbox.value()
        self.new_logic_config.cycles_before_long_break = self.cycles_spinbox.value()
        self.new_logic_config.snooze_duration_minutes = self.snooze_spinbox.value()
        super().accept()

    def get_logic_config(self) -> PomodoroConfig:
        return self.new_logic_config