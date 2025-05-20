import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QSpacerItem, QHBoxLayout, QDialog, QMessageBox, QRadioButton, QButtonGroup, QComboBox, QSlider, QDialogButtonBox, QSystemTrayIcon, QMenu, QStyle, QProgressDialog, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QCheckBox, QGroupBox, QFrame, QFormLayout, QScrollArea, QTextEdit
)
from PyQt6.QtCore import QSize, Qt, QUrl, QThread, pyqtSignal, QSettings, QTimer, QEvent, QPropertyAnimation, QEasingCurve, QRect, QPoint
from PyQt6.QtGui import QPixmap, QFont, QCursor, QDesktopServices, QImage, QIcon, QAction, QColor
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from auth_service import supabase
from datetime import datetime, timezone
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from mediapipe import solutions as mp_solutions
import traceback
import math
from data_manager import init_db, add_session_data, get_session_data
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import os
import requests
import threading
import asyncio
import edge_tts
import tempfile
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
import shutil
import platform
import time
from requests.exceptions import ConnectionError
from utils import resource_path
from TTS.api import TTS
import torch

# Set Coqui TTS license agreement environment variable
os.environ['COQUI_TTS_AGREED'] = '1'

# Global variable to hold the main server instance
_main_local_server = None

POSE_MODEL_PATH = "PostureApp/models/pose_landmarker_heavy.task"
# DEFAULT_SENSITIVITY_DEGREES = 25 # This is not directly used for the dynamic threshold
CURRENT_APP_VERSION = "1.0.0"
UPDATE_INFO_URL = "https://example.com/update-info.json"  # Replace with actual URL
WEB_APP_BASE_URL = "http://localhost:3000" # Base URL for the web application
MANAGE_SUBSCRIPTION_URL = "https://localhost:3000/dashboard" # URL for managing subscription

# New Constants for secondary posture checks - These will be removed/modified
# SHOULDER_VERTICAL_DIFF_RATIO = 0.1  # 10% of inter-shoulder distance for vertical imbalance
# HEAD_HORIZONTAL_SHIFT_RATIO = 0.1   # 10% of calibrated inter-shoulder distance for horizontal head shift

# Set organization and app name for QSettings
QSettings.setDefaultFormat(QSettings.Format.IniFormat)
ORGANIZATION_NAME = "devdash AB"
APPLICATION_NAME = "Ergo"

# Custom Notification Toast Widget
class CustomNotificationToast(QWidget):
    def __init__(self, message, parent=None, duration=3000, fade_duration=500):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool | # Ensures it doesn't get taskbar entry, stays on top more reliably
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.duration = duration
        self.fade_duration = fade_duration

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0) # Margin handled by inner frame

        self.container_frame = QWidget(self) # Use a QWidget for styling container
        self.container_frame.setObjectName("NotificationToastContainer")
        
        container_layout = QVBoxLayout(self.container_frame)
        container_layout.setContentsMargins(15, 10, 15, 10) # Padding inside the toast

        self.message_label = QLabel(message)
        self.message_label.setObjectName("NotificationToastMessage")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        container_layout.addWidget(self.message_label)
        
        layout.addWidget(self.container_frame)
        self.setLayout(layout)

        # Opacity effect for fading
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self.opacity_effect)

        # Shadow effect (optional, but adds depth)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 3)
        self.container_frame.setGraphicsEffect(shadow)
        
        self.adjustSize() # Adjust size based on content

    def show_toast(self):
        if not self.parentWidget():
            # Center on screen if no parent
            screen_geometry = QApplication.primaryScreen().geometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)
        else:
            # Center on parent widget
            parent_geometry = self.parentWidget().geometry()
            parent_global_pos = self.parentWidget().mapToGlobal(QPoint(0,0))
            x = parent_global_pos.x() + (parent_geometry.width() - self.width()) // 2
            y = parent_global_pos.y() + (parent_geometry.height() - self.height()) // 2
            self.move(x, y)
        
        self.show()

        self.animation_fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation_fade_in.setDuration(self.fade_duration)
        self.animation_fade_in.setStartValue(0.0)
        self.animation_fade_in.setEndValue(0.9) # Slightly transparent
        self.animation_fade_in.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation_fade_in.start()

        QTimer.singleShot(self.duration, self._start_fade_out)

    def _start_fade_out(self):
        self.animation_fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation_fade_out.setDuration(self.fade_duration)
        self.animation_fade_out.setStartValue(self.opacity_effect.opacity())
        self.animation_fade_out.setEndValue(0.0)
        self.animation_fade_out.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation_fade_out.finished.connect(self.close)
        self.animation_fade_out.start()

def load_stylesheet(app):
    try:
        # Use resource_path to locate styles.qss
        stylesheet_file_path = resource_path("styles.qss")
        with open(stylesheet_file_path, "r") as f:
            stylesheet = f.read()
            app.setStyleSheet(stylesheet)
            print(f"Stylesheet '{stylesheet_file_path}' loaded successfully.")
    except FileNotFoundError:
        print(f"Warning: styles.qss not found at '{resource_path("styles.qss")}'. Using default styles.")
    except Exception as e:
        print(f"Error loading stylesheet: {e}")

class WebcamThread(QThread):
    new_frame_ready = pyqtSignal(QImage)
    error_occurred = pyqtSignal(str)

    def __init__(self, camera_index=0, show_landmarks=True, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self.should_draw_landmarks = show_landmarks
        self._running = False
        self.cap = None
        self.pose_processor = None
        self.mp_pose_connections = None
        self.drawing_utils = mp_solutions.drawing_utils
        self.drawing_styles = mp_solutions.drawing_styles
        self.error = None
        self.latest_pose_landmarks = None
        self._init_pose_landmarker()

    def _init_pose_landmarker(self):
        try:
            self.pose_processor = mp_solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=2, # Consider making this configurable or using a lighter model
                enable_segmentation=False,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self.mp_pose_connections = mp_solutions.pose.POSE_CONNECTIONS
            self.pose_landmarker = None # This seems unused if mp_solutions.pose.Pose is primary
        except Exception as e:
            self.error = f"Failed to initialize MediaPipe Pose: {e}"
            print(self.error)
            traceback.print_exc()
            self.pose_processor = None
            # Emit error if initialization fails critically
            # self.error_occurred.emit(self.error) # Consider if this should stop thread start

    def run(self):
        if not self.pose_processor:
            init_error_msg = self.error if self.error else "MediaPipe Pose processor failed to initialize."
            self.error_occurred.emit(init_error_msg)
            self._running = False # Ensure thread doesn't run if pose processor is bad
            return

        self._running = True
        self.cap = cv2.VideoCapture(self.camera_index)
        frame_idx = 0
        fail_count = 0
        fail_limit = 60  # About 1 second of failures
        while self._running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                fail_count += 1
                if fail_count >= fail_limit:
                    # Try to distinguish error
                    msg = f"Webcam error (index {self.camera_index})."
                    if not self.cap.isOpened():
                        msg = f"Webcam (index {self.camera_index}) could not be opened. It might be disconnected or unavailable."
                    else:
                        # Try to check for permission denied or in use
                        msg = f"Webcam (index {self.camera_index}) access denied or in use. Try another webcam in Settings."
                    self.error_occurred.emit(msg)
                    break
                continue
            fail_count = 0
            annotated_frame = frame.copy()
            try:
                if self.pose_processor:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    result = self.pose_processor.process(rgb_frame)

                    if result.pose_landmarks:
                        self.latest_pose_landmarks = [
                            [lm.x * frame.shape[1], lm.y * frame.shape[0]] for lm in result.pose_landmarks.landmark
                        ]
                        if self.should_draw_landmarks:
                            self.drawing_utils.draw_landmarks(
                                annotated_frame,
                                result.pose_landmarks,
                                self.mp_pose_connections
                            )
                    else:
                        self.latest_pose_landmarks = None
            except Exception as e:
                print(f"MediaPipe Pose (solutions API) processing error: {e}")
                traceback.print_exc()
            output_rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = output_rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(output_rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self.new_frame_ready.emit(qt_image)
            frame_idx += 1
            self.msleep(30)  # ~30 FPS
        if self.cap:
            self.cap.release()

    def start_capture(self, camera_index=0):
        self.camera_index = camera_index
        if not self.isRunning():
            self.start()

    def stop_capture(self):
        print("[DEBUG] WebcamThread.stop_capture() called") # DEBUG
        self._running = False
        print("[DEBUG] WebcamThread waiting for run() to finish...") # DEBUG
        self.wait()
        print("[DEBUG] WebcamThread.run() finished") # DEBUG

    def set_show_landmarks(self, show_landmarks: bool):
        self.should_draw_landmarks = show_landmarks

class SignUpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sign Up")
        self.setFixedSize(350, 220)
        layout = QVBoxLayout()
        layout.setSpacing(12)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText('Email')
        layout.addWidget(self.email_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Password')
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText('Confirm Password')
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.confirm_password_input)

        self.error_label = QLabel()
        self.error_label.setStyleSheet('color: red;')
        self.error_label.hide()
        layout.addWidget(self.error_label)

        self.signup_button = QPushButton('Sign Up')
        self.signup_button.clicked.connect(self.handle_signup)
        layout.addWidget(self.signup_button)

        self.setLayout(layout)

    def handle_signup(self):
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        confirm_password = self.confirm_password_input.text().strip()
        self.error_label.hide()
        if not email or not password or not confirm_password:
            self.error_label.setText("All fields are required.")
            self.error_label.show()
            return
        if password != confirm_password:
            self.error_label.setText("Passwords do not match.")
            self.error_label.show()
            return
        try:
            response = supabase.auth.sign_up({"email": email, "password": password})
            user = response.user
            if user:
                QMessageBox.information(self, "Sign Up Successful", "Account created! Please check your email to verify your account before logging in.")
                self.accept()
            else:
                self.error_label.setText("Sign up failed. Please try again.")
                self.error_label.show()
        except Exception as e:
            msg = str(e)
            if "already registered" in msg:
                self.error_label.setText("Email is already registered.")
            else:
                self.error_label.setText("Sign up error: " + msg)
            self.error_label.show()

class LoginView(QWidget):
    def __init__(self, parent=None, on_login=None):
        super().__init__(parent)
        self.setObjectName("LoginViewContainer") # Added for specific container styling
        self.on_login = on_login
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        # App name label
        app_name_label = QLabel('Ergo')
        app_name_label.setObjectName("H1Title") # Apply H1Title style
        app_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(app_name_label)

        # Logo
        logo_label = QLabel()
        logo_pixmap_size = 120
        # Use resource_path here
        logo_path = resource_path(os.path.join('resources', 'icons', 'ergo-logo.png'))
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            logo_label.setPixmap(pixmap.scaled(logo_pixmap_size, logo_pixmap_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            # Fallback placeholder if logo not found
            pixmap = QPixmap(logo_pixmap_size, logo_pixmap_size)
            pixmap.fill(QColor("#3C3C50")) # lightDarkGray
            logo_label.setPixmap(pixmap)
            print(f"Warning: Logo image not found at {logo_path}. Using placeholder.")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setContentsMargins(0, 0, 0, 10) # Add some space below logo
        layout.addWidget(logo_label)

        # Tagline
        tagline_label = QLabel('Improve your posture with real-time feedback.')
        tagline_label.setObjectName("TaglineLabel") # More specific than just class
        tagline_label.setProperty("class", "BodySecondary") # Keep class for general BodySecondary styling
        tagline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline_label.setContentsMargins(0, 0, 0, 20)
        layout.addWidget(tagline_label)

        # Email input
        self.email_input = QLineEdit()
        self.email_input.setObjectName("EmailInput") # Added objectName
        self.email_input.setPlaceholderText('Email')
        self.email_input.setFixedWidth(300)
        layout.addWidget(self.email_input, alignment=Qt.AlignmentFlag.AlignCenter)

        # Password input
        self.password_input = QLineEdit()
        self.password_input.setObjectName("PasswordInput") # Added objectName
        self.password_input.setPlaceholderText('Password')
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedWidth(300)
        layout.addWidget(self.password_input, alignment=Qt.AlignmentFlag.AlignCenter)

        # Login button
        self.login_button = QPushButton('Login')
        self.login_button.setObjectName("PrimaryCTA")
        self.login_button.setFixedWidth(300)
        self.login_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.login_button.clicked.connect(self.handle_login)
        layout.addWidget(self.login_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Error message label
        self.error_label = QLabel()
        self.error_label.setObjectName("ErrorLabel") # Added objectName
        self.error_label.setProperty("class", "ErrorText") # Keep class for general error styling
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.setFixedWidth(300)
        self.error_label.hide()
        layout.addWidget(self.error_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Horizontal layout for links
        links_hbox = QHBoxLayout()
        links_hbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        links_hbox.setSpacing(10)

        # Sign-up Button (now styled as a secondary button)
        self.signup_button = QPushButton('Create Account')
        self.signup_button.setProperty("class", "Secondary") # Apply Secondary button style
        self.signup_button.setFixedWidth(145)
        self.signup_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.signup_button.clicked.connect(self.open_signup_dialog)
        links_hbox.addWidget(self.signup_button)

        # Forgot Password Link Label
        link_label = QLabel('<a href="#">Forgot Password?</a>')
        link_label.setObjectName("ForgotPasswordLink") # Added objectName
        link_label.setProperty("class", "BodySecondary") # Keep class for general BodySecondary styling
        link_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        link_label.setOpenExternalLinks(False) # We handle this manually now
        link_label.linkActivated.connect(lambda: QDesktopServices.openUrl(QUrl(f"{WEB_APP_BASE_URL}/forgot-password")))
        link_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        links_hbox.addWidget(link_label)

        layout.addLayout(links_hbox)
        layout.addStretch()
        self.setLayout(layout)

    def open_signup_dialog(self):
        # dialog = SignUpDialog(self)
        # dialog.exec()
        QDesktopServices.openUrl(QUrl(f"{WEB_APP_BASE_URL}/signup"))

    def handle_login(self):
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        self.error_label.hide()
        if not email or not password:
            self.error_label.setText("Please enter both email and password.")
            self.error_label.show()
            return
        try:
            try:
                response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            except Exception as e:
                # Network error for supabase-py
                if "Network" in str(e) or "Failed to establish a new connection" in str(e) or "ConnectionError" in str(e):
                    self.error_label.setText("Network error. Could not connect to login service. Please check your internet connection.")
                    self.error_label.show()
                    return
                raise
            user = response.user
            if user:
                # Query user_subscriptions table for this user
                try:
                    user_id = user.id
                    try:
                        sub_resp = supabase.table("user_subscriptions").select("status,expires_at").eq("user_id", user_id).single().execute()
                    except Exception as e:
                        if "Network" in str(e) or "Failed to establish a new connection" in str(e) or "ConnectionError" in str(e):
                            self.error_label.setText("Network error. Could not connect to login service. Please check your internet connection.")
                            self.error_label.show()
                            return
                        raise
                    sub_data = sub_resp.data
                    if not sub_data:
                        raise Exception("No subscription record found.")
                    status = sub_data.get("status", "")
                    expires_at_str = sub_data.get("expires_at", "")
                    parsed_expires_dt = None
                    if expires_at_str:
                        try:
                            parsed_expires_dt = datetime.fromisoformat(expires_at_str)
                        except ValueError:
                            pass
                    if status != "active" or not parsed_expires_dt:
                        raise Exception("inactive_or_invalid_expiry")
                    is_expired = False
                    if parsed_expires_dt.tzinfo is None or parsed_expires_dt.tzinfo.utcoffset(parsed_expires_dt) is None:
                        if parsed_expires_dt.time() == datetime.min.time():
                            is_expired = parsed_expires_dt.date() < datetime.now().date()
                        else:
                            is_expired = parsed_expires_dt < datetime.now()
                    else:
                        is_expired = parsed_expires_dt < datetime.now(timezone.utc)
                    if is_expired:
                        raise Exception("expired")
                    # Success: pass info to dashboard
                    self.error_label.hide()
                    if self.on_login:
                        self.on_login(email, status, expires_at_str)
                except Exception as sub_err:
                    # Sign out and show error
                    try:
                        supabase.auth.sign_out()
                    except Exception:
                        pass
                    self.error_label.setText(
                        f'Your subscription has expired or is inactive. Please visit <a href="{WEB_APP_BASE_URL}/dashboard">Subscription Page</a> to renew.'
                    )
                    self.error_label.setOpenExternalLinks(True)
                    self.error_label.show()
            else:
                self.error_label.setText("Invalid email or password.")
                self.error_label.show()
        except Exception as e:
            msg = str(e)
            if "Invalid login credentials" in msg or "400" in msg:
                self.error_label.setText("Invalid email or password.")
            elif "Could not verify subscription" in msg:
                self.error_label.setText("Could not verify subscription. Please check your internet connection.")
            elif "Network error" in msg or "Could not connect to login service" in msg or isinstance(e, ConnectionError):
                self.error_label.setText("Network error. Could not connect to login service. Please check your internet connection.")
            else:
                self.error_label.setText("Network error. Please check your connection.")
            self.error_label.show()

    def clear_fields(self):
        self.email_input.clear()
        self.password_input.clear()
        self.error_label.hide()

# Utility function to get available cameras
def get_available_cameras(max_cameras=5):
    cameras = []
    for idx in range(max_cameras):
        cap = cv2.VideoCapture(idx)
        if cap is not None and cap.isOpened():
            cameras.append((idx, f"Camera {idx}"))
            cap.release()
    return cameras

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(540, 560)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        main_layout.setSpacing(30)
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # Helper: shadow effect
        def make_shadow():
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(16)
            shadow.setColor(QColor(0,0,0,40))
            shadow.setOffset(0, 2)
            return shadow

        # Sensitivity Section
        sens_group = QGroupBox("Sensitivity")
        sens_group.setMinimumWidth(400)
        sens_group.setGraphicsEffect(make_shadow())
        sens_layout = QVBoxLayout()
        sens_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        sens_desc = QLabel("How sensitive should posture detection be?")
        sens_desc.setObjectName("SectionDescription")
        sens_desc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        sens_desc.setStyleSheet("background: transparent;")
        sens_layout.addWidget(sens_desc)
        self.sens_combo = QComboBox()
        self.sens_combo.addItems(["Low", "Medium", "High"])
        self.sens_combo.setMinimumWidth(180)
        self.sens_combo.setMaximumWidth(260)
        self.sens_combo.setToolTip("Set how sensitive the posture detection should be.")
        self.sens_combo.setGraphicsEffect(make_shadow())
        sens_layout.addWidget(self.sens_combo, alignment=Qt.AlignmentFlag.AlignHCenter)
        sens_group.setLayout(sens_layout)
        main_layout.addWidget(sens_group)

        # Notification Settings
        notif_group = QGroupBox("Notifications")
        notif_group.setMinimumWidth(400)
        notif_group.setGraphicsEffect(make_shadow())
        notif_layout = QVBoxLayout()
        notif_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        notif_desc = QLabel("Choose how you want to be notified.")
        notif_desc.setObjectName("SectionDescription")
        notif_desc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        notif_desc.setStyleSheet("background: transparent;")
        notif_layout.addWidget(notif_desc)
        self.audio_radio = QRadioButton("Audio Alert Only")
        self.visual_radio = QRadioButton("Visual Alert Only")
        self.both_radio = QRadioButton("Both Audio and Visual Alerts")
        self.notif_group = QButtonGroup(self)
        self.notif_group.addButton(self.audio_radio)
        self.notif_group.addButton(self.visual_radio)
        self.notif_group.addButton(self.both_radio)
        notif_radio_layout = QHBoxLayout()
        notif_radio_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        notif_radio_layout.setSpacing(18)
        notif_radio_layout.addWidget(self.audio_radio)
        notif_radio_layout.addWidget(self.visual_radio)
        notif_radio_layout.addWidget(self.both_radio)
        notif_layout.addLayout(notif_radio_layout)
        notif_group.setLayout(notif_layout)
        main_layout.addWidget(notif_group)

        # Custom Alert Message
        custom_msg_group = QGroupBox("Custom Alert Message")
        custom_msg_group.setMinimumWidth(400)
        custom_msg_group.setGraphicsEffect(make_shadow())
        custom_msg_layout = QVBoxLayout()
        custom_msg_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        custom_msg_desc = QLabel("Personalize the message you receive when posture is bad.")
        custom_msg_desc.setObjectName("SectionDescription")
        custom_msg_desc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        custom_msg_desc.setStyleSheet("background: transparent;")
        custom_msg_layout.addWidget(custom_msg_desc)
        self.custom_msg_edit = QTextEdit()
        self.custom_msg_edit.setPlaceholderText("Enter your custom alert message here (e.g. 'Fix your posture!')")
        self.custom_msg_edit.setMinimumHeight(40)
        self.custom_msg_edit.setMaximumHeight(80)
        self.custom_msg_edit.setMaximumWidth(320)
        self.custom_msg_edit.setGraphicsEffect(make_shadow())
        custom_msg_layout.addWidget(self.custom_msg_edit, alignment=Qt.AlignmentFlag.AlignHCenter)
        custom_msg_group.setLayout(custom_msg_layout)
        main_layout.addWidget(custom_msg_group)

        # Voice Selection Section
        voice_selection_group = QGroupBox("Voice Selection")
        voice_selection_group.setMinimumWidth(400)
        voice_selection_group.setGraphicsEffect(make_shadow())
        voice_selection_layout = QVBoxLayout()
        voice_selection_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        voice_selection_desc = QLabel("Choose the voice for audio alerts.")
        voice_selection_desc.setObjectName("SectionDescription")
        voice_selection_desc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        voice_selection_desc.setStyleSheet("background: transparent;")
        voice_selection_layout.addWidget(voice_selection_desc)
        self.voice_selector_combobox = QComboBox()
        self.voice_selector_combobox.setMinimumWidth(180)
        self.voice_selector_combobox.setMaximumWidth(260)
        self.voice_selector_combobox.setToolTip("Select the voice for TTS alerts.")
        self.voice_selector_combobox.setGraphicsEffect(make_shadow())
        # Populate voice selector - this will be done in load_settings or init
        voice_selection_layout.addWidget(self.voice_selector_combobox, alignment=Qt.AlignmentFlag.AlignHCenter)
        voice_selection_group.setLayout(voice_selection_layout)
        main_layout.addWidget(voice_selection_group)

        # Webcam Settings
        webcam_group = QGroupBox("Webcam")
        webcam_group.setMinimumWidth(400)
        webcam_group.setGraphicsEffect(make_shadow())
        webcam_layout = QVBoxLayout()
        webcam_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        webcam_desc = QLabel("Select which webcam to use and whether to show posture landmarks.")
        webcam_desc.setObjectName("SectionDescription")
        webcam_desc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        webcam_desc.setStyleSheet("background: transparent;")
        webcam_layout.addWidget(webcam_desc)
        self.webcam_selector_combobox = QComboBox()
        for idx, name in get_available_cameras():
            self.webcam_selector_combobox.addItem(name, idx)
        self.webcam_selector_combobox.setMinimumWidth(180)
        self.webcam_selector_combobox.setMaximumWidth(260)
        self.webcam_selector_combobox.setToolTip("Choose which webcam to use for posture detection.")
        self.webcam_selector_combobox.setGraphicsEffect(make_shadow())
        webcam_layout.addWidget(self.webcam_selector_combobox, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.show_landmarks_checkbox = QCheckBox("Show Posture Landmarks on Webcam Feed")
        self.show_landmarks_checkbox.setToolTip("Toggle the display of detected posture landmarks on the webcam feed.")
        webcam_layout.addWidget(self.show_landmarks_checkbox, alignment=Qt.AlignmentFlag.AlignHCenter)
        webcam_group.setLayout(webcam_layout)
        main_layout.addWidget(webcam_group)

        # Manage Subscription
        sub_group = QGroupBox("Subscription")
        sub_group.setMinimumWidth(400)
        sub_group.setGraphicsEffect(make_shadow())
        sub_layout = QVBoxLayout()
        sub_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        sub_desc = QLabel("Manage your subscription and billing details online.")
        sub_desc.setObjectName("SectionDescription")
        sub_desc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        sub_desc.setStyleSheet("background: transparent;")
        sub_layout.addWidget(sub_desc)
        self.manage_sub_button = QPushButton("Manage Subscription")
        self.manage_sub_button.setProperty("class", "Secondary")
        self.manage_sub_button.setMinimumWidth(220)
        self.manage_sub_button.setMaximumWidth(220)
        icon_sub_settings = self.style().standardIcon(QStyle.StandardPixmap.SP_FileLinkIcon)
        self.manage_sub_button.setIcon(icon_sub_settings)
        self.manage_sub_button.clicked.connect(self.open_subscription_page)
        self.manage_sub_button.setGraphicsEffect(make_shadow())
        sub_layout.addWidget(self.manage_sub_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        sub_group.setLayout(sub_layout)
        main_layout.addWidget(sub_group)

        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        for btn in self.button_box.buttons():
            btn.setMinimumWidth(160)
            btn.setMaximumWidth(160)
            btn.setGraphicsEffect(make_shadow())
        self.button_box.setCenterButtons(True)
        self.button_box.accepted.connect(self.save_settings)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box, alignment=Qt.AlignmentFlag.AlignHCenter)

        scroll.setWidget(content_widget)
        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        self.setLayout(layout)
        self.load_settings()

    def load_settings(self):
        settings = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)
        sens = settings.value("sensitivity", "Medium")
        notif = settings.value("notification_mode", "both")
        custom_msg = settings.value("custom_alert_message", "Fix your posture!")
        webcam_idx_setting = settings.value("webcam_index", 0)
        webcam_idx = int(webcam_idx_setting) if webcam_idx_setting is not None else 0
        show_lm = settings.value("show_landmarks", True, type=bool)
        selected_voice_file = settings.value("selected_voice_file", "Leif GW.wav") # Default voice

        self.sens_combo.setCurrentText(sens)
        if notif == "audio":
            self.audio_radio.setChecked(True)
        elif notif == "visual":
            self.visual_radio.setChecked(True)
        else:
            self.both_radio.setChecked(True)
        self.custom_msg_edit.setPlainText(custom_msg)
        self.show_landmarks_checkbox.setChecked(show_lm)
        
        # Populate and set voice selector
        self.voice_selector_combobox.clear()
        audio_dir = resource_path("resources/audio")
        if os.path.exists(audio_dir) and os.path.isdir(audio_dir):
            wav_files = [f for f in os.listdir(audio_dir) if f.endswith('.wav')]
            for wav_file in sorted(wav_files):
                self.voice_selector_combobox.addItem(wav_file)
        
        voice_idx = self.voice_selector_combobox.findText(selected_voice_file)
        if voice_idx != -1:
            self.voice_selector_combobox.setCurrentIndex(voice_idx)
        elif self.voice_selector_combobox.count() > 0:
             self.voice_selector_combobox.setCurrentIndex(0) # Fallback to first if saved not found

        idx = self.webcam_selector_combobox.findData(webcam_idx)
        if idx != -1:
            self.webcam_selector_combobox.setCurrentIndex(idx)
        else:
            self.webcam_selector_combobox.setCurrentIndex(0)

    def save_settings(self):
        settings = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)
        sens = self.sens_combo.currentText()
        if self.audio_radio.isChecked():
            notif = "audio"
        elif self.visual_radio.isChecked():
            notif = "visual"
        else:
            notif = "both"
        custom_msg = self.custom_msg_edit.toPlainText()
        webcam_idx = self.webcam_selector_combobox.currentData()
        show_lm_val = self.show_landmarks_checkbox.isChecked()
        selected_voice_file_val = self.voice_selector_combobox.currentText()
        settings.setValue("sensitivity", sens)
        settings.setValue("notification_mode", notif)
        settings.setValue("custom_alert_message", custom_msg)
        settings.setValue("webcam_index", webcam_idx)
        settings.setValue("show_landmarks", show_lm_val)
        settings.setValue("selected_voice_file", selected_voice_file_val)
        self.accept()
        if hasattr(self.parent(), "apply_settings"):
            self.parent().apply_settings()

    def open_subscription_page(self):
        # This method now directly opens the URL
        QDesktopServices.openUrl(QUrl(MANAGE_SUBSCRIPTION_URL))

class SessionGraphCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(7, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.updateGeometry()
        self.current_graph_type = None # To track if live or historical is shown

    def plot_historical_data(self, session_data):
        self.ax.clear()
        # New theme colors
        primary_color = '#414b53' # Main background
        card_bg_color = '#586168' # Lighter primary for plot area, similar to cards
        accent_color = '#d4d3c8'  # Text, ticks, spines
        secondary_color = '#919da0' # Borders, grid lines
        data_viz_color = '#88c0d0' # For bar/line plots

        if session_data:
            dates = [row[0] for row in session_data]
            counts = [row[1] for row in session_data]
            self.ax.bar(dates, counts, color=data_viz_color) # Use data_viz_color
            self.ax.set_title('Posture Reminders Per Session (Historical)')
            self.ax.set_xlabel('Session Date')
            self.ax.set_ylabel('Total Reminders')
            self.ax.tick_params(axis='x', rotation=45)
            
            self.fig.patch.set_facecolor(primary_color)
            self.ax.set_facecolor(card_bg_color)
            
            self.ax.spines['bottom'].set_color(accent_color)
            self.ax.spines['top'].set_color(accent_color) 
            self.ax.spines['right'].set_color(accent_color)
            self.ax.spines['left'].set_color(accent_color)
            
            self.ax.tick_params(axis='x', colors=accent_color)
            self.ax.tick_params(axis='y', colors=accent_color)
            self.ax.yaxis.label.set_color(accent_color)
            self.ax.xaxis.label.set_color(accent_color)
            self.ax.title.set_color(accent_color)
            self.ax.grid(True, linestyle='--', alpha=0.3, color=secondary_color)
        else:
            self.ax.set_title('Posture Reminders Per Session (Historical)')
            self.ax.text(0.5, 0.5, 'No session data yet.', ha='center', va='center', fontsize=12, color=accent_color, transform=self.ax.transAxes)
            self.ax.set_xlabel('Session Date')
            self.ax.set_ylabel('Total Reminders')
            self.ax.set_xticks([0, 1])
            self.ax.set_yticks([0, 1])
            self.ax.set_xlim(left=0, right=1)
            self.ax.set_ylim(bottom=0, top=1)
            
            self.fig.patch.set_facecolor(primary_color)
            self.ax.set_facecolor(card_bg_color)
            self.ax.spines['bottom'].set_color(accent_color)
            self.ax.spines['top'].set_color(accent_color) 
            self.ax.spines['right'].set_color(accent_color)
            self.ax.spines['left'].set_color(accent_color)
            self.ax.tick_params(axis='x', colors=accent_color)
            self.ax.tick_params(axis='y', colors=accent_color)
            self.ax.yaxis.label.set_color(accent_color)
            self.ax.xaxis.label.set_color(accent_color)
            self.ax.title.set_color(accent_color)
            self.ax.grid(True, linestyle='--', alpha=0.3, color=secondary_color)
            
        self.fig.tight_layout(pad=0.5)
        self.draw()
        self.current_graph_type = "historical"

    def plot_live_data(self, live_reminder_data):
        self.ax.clear()
        # New theme colors
        primary_color = '#414b53'
        card_bg_color = '#586168'
        accent_color = '#d4d3c8'
        secondary_color = '#919da0'
        data_viz_color = '#88c0d0' # For bar/line plots

        if live_reminder_data and len(live_reminder_data) > 1:
            time_data = [item[0] for item in live_reminder_data]
            count_data = [item[1] for item in live_reminder_data]
            
            self.ax.plot(time_data, count_data, linestyle='-', color=data_viz_color, linewidth=2)
            
            self.ax.set_title('Live Reminders This Session')
            self.ax.set_xlabel('Time Elapsed (seconds)')
            self.ax.set_ylabel('Cumulative Reminders')
            
            max_y = max(count_data) if count_data else 0
            yticks = [0]
            if max_y > 0:
                yticks.append(max_y)
            self.ax.set_yticks(yticks)
            self.ax.set_ylim(bottom=-0.5, top=max_y + 1.5 if max_y > 0 else 1.5)
            self.ax.set_xlim(left=0)
            self.ax.grid(True, linestyle='--', alpha=0.3, color=secondary_color)

        elif live_reminder_data and len(live_reminder_data) == 1 and live_reminder_data[0][0] == 0 and live_reminder_data[0][1] == 0:
            self.ax.plot([0], [0], color=data_viz_color, linewidth=2)
            self.ax.set_title('Live Reminders This Session')
            self.ax.set_xlabel('Time Elapsed (seconds)')
            self.ax.set_ylabel('Cumulative Reminders')
            self.ax.set_ylim(bottom=-0.5, top=1.5)
            self.ax.set_xlim(left=0, right=60)
            self.ax.set_yticks([0])
            self.ax.set_xticks([0, 30, 60])
            self.ax.grid(True, linestyle='--', alpha=0.3, color=secondary_color)
            self.ax.text(0.5, 0.6, 'Session active. Monitoring...', ha='center', va='center', fontsize=10, color=accent_color, transform=self.ax.transAxes)
        else:
            self.ax.set_title('Live Reminders This Session') 
            self.ax.text(0.5, 0.5, 'Session started. Waiting for first reminder...', ha='center', va='center', fontsize=10, color=accent_color, transform=self.ax.transAxes)
            self.ax.set_xlabel('Time Elapsed (seconds)')
            self.ax.set_ylabel('Cumulative Reminders')
            self.ax.set_xticks([0, 30, 60])
            self.ax.set_yticks([0, 2, 4, 6, 8, 10]) # Keeping these default ticks for now, can adjust
            self.ax.set_xlim(left=0, right=60)
            self.ax.set_ylim(bottom=-0.5, top=10.5)
            self.ax.grid(True, linestyle='--', alpha=0.3, color=secondary_color)

        self.fig.patch.set_facecolor(primary_color)
        self.ax.set_facecolor(card_bg_color)
        self.ax.spines['bottom'].set_color(accent_color)
        self.ax.spines['top'].set_color(accent_color)
        self.ax.spines['right'].set_color(accent_color)
        self.ax.spines['left'].set_color(accent_color)
        self.ax.tick_params(axis='x', colors=accent_color)
        self.ax.tick_params(axis='y', colors=accent_color)
        self.ax.yaxis.label.set_color(accent_color)
        self.ax.xaxis.label.set_color(accent_color)
        self.ax.title.set_color(accent_color)
        
        self.fig.tight_layout(pad=0.5)
        self.draw()
        self.current_graph_type = "live"

    def clear_graph(self): # Optional, explicit clear
        self.ax.clear()
        self.current_graph_type = None # Reset graph type
        self.draw()

    def update_user_info(self, email, status=None, expires_at=None):
        self.user_email = email
        # The UI elements for displaying this directly on DashboardView are removed.
        # This method can still be used to store the info if needed for other purposes (e.g. tray tooltip)
        if status and expires_at:
            try:
                expires_dt = datetime.fromisoformat(expires_at)
                expires_str = expires_dt.strftime('%Y-%m-%d')
                # Example: self.current_subscription_details = f"Subscription: {status.capitalize()} until {expires_str}"
            except Exception:
                # self.current_subscription_details = f"Subscription: {status.capitalize()} until {expires_at}"
                pass # Store as is if parsing fails
        else:
            # self.current_subscription_details = f"Subscription Status: - for {email}"
            pass

    def open_manage_subscription(self):
        QDesktopServices.openUrl(QUrl(MANAGE_SUBSCRIPTION_URL))

    def handle_logout(self):
        # Implement logout functionality
        pass

class DashboardView(QWidget):
    # Signal emitted with temp file path to play TTS on main thread
    tts_play = pyqtSignal(str)
    calibration_successful_and_session_started = pyqtSignal()
    show_toast_signal = pyqtSignal(str, int) # New signal for toasts

    def __init__(self, parent=None, on_logout=None):
        super().__init__(parent)
        self.settings = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)
        self.main_window = parent # Store reference to MainWindow
        self.on_logout_callback = on_logout
        self.current_email = ""
        self.subscription_status = "unknown"
        self.subscription_expires_at = None
        self.is_calibrated = False # Initialize is_calibrated
        self.app_settings = self.load_app_settings() # Load settings before _init_ui uses them

        self._init_ui() # _init_ui will now use self.app_settings
        self.show_toast_signal.connect(self._handle_show_toast)

        # Initialize TTS engine in a separate thread to avoid UI freeze
        self.tts_init_thread = threading.Thread(target=self._initialize_tts_engine, daemon=True)
        self.tts_init_thread.start()

    def _handle_show_toast(self, message, duration):
        toast = CustomNotificationToast(message, parent=self, duration=duration)
        toast.show_toast()

    def _init_ui(self):
        self.setObjectName("DashboardViewContainer") # Added objectName
        self.user_email = None
        self.subscription_status_str = None
        self.webcam_thread = None
        self.session_active = False
        self.calibrating = False
        self.reference_angles = {'head_forward': None, 'shoulder_line': None}
        self.latest_landmarks = None
        self.current_session_reminder_count = 0
        self.current_session_live_reminder_data = [] # Stores (time_elapsed_sec, cumulative_count)
        self.session_start_time = None # To track time for live graph
        self.settings_btn = QPushButton('Settings')
        self.settings_btn.clicked.connect(self.open_settings_dialog)
        # self.app_settings = self.load_app_settings() # Moved to __init__ before _init_ui
        # Connect TTS play signal to playback slot
        self.tts_play.connect(self._play_media)
        # Initialize TTS cache: only regenerate audio when text changes
        self._cached_tts_text = None
        self._last_tts_text = None 
        self._cached_tts_file = os.path.join(tempfile.gettempdir(), 'postureapp_alert.mp3') # Standardized cache file path
        
        self.tts_engine = None # For Coqui TTS
        # self.speaker_wav_path is now initialized within _init_ui from self.app_settings
        self.speaker_wav_path = None 

        main_layout = QVBoxLayout()
        main_layout.setSpacing(24)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        # Initialize last alert timestamp and interval
        self._last_alert_time = 0
        self.alert_interval = 15  # seconds between posture deviation alerts

        # Top buttons (Start/Stop Session, Settings, Logout)
        top_button_bar = QWidget() # Create a container for the top button bar
        top_button_bar.setObjectName("TopButtonBar")
        button_layout = QHBoxLayout(top_button_bar) # Apply layout to the container
        button_layout.setContentsMargins(0,0,0,0) # No margins for the bar itself
        button_layout.setSpacing(10) # Spacing between buttons

        self.start_session_btn = QPushButton('Start Session')
        self.start_session_btn.setObjectName("PrimaryCTA") # Primary action
        # Use standard icon as fallback
        icon_start = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        self.start_session_btn.setIcon(icon_start)

        self.stop_session_btn = QPushButton('Stop Session')
        self.stop_session_btn.setObjectName("StopButton") 
        icon_stop = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop)
        self.stop_session_btn.setIcon(icon_stop)
        self.stop_session_btn.setEnabled(False)

        # Standard icon for settings button
        icon_settings = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon) # Or SP_FileDialogDetailedView, SP_ToolBarHorizontalExtensionButton
        self.settings_btn.setIcon(icon_settings)

        logout_btn = QPushButton('Logout')
        logout_btn.setProperty("class", "Secondary") # Secondary action
        icon_logout = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton) # Or SP_DialogCancelButton
        logout_btn.setIcon(icon_logout)
        logout_btn.clicked.connect(self.handle_logout)  # Connect the button to the logout handler
        button_layout.addWidget(self.start_session_btn)
        button_layout.addWidget(self.stop_session_btn)
        button_layout.addWidget(self.settings_btn)
        button_layout.addWidget(logout_btn)

        # Add reminder count label
        self.reminder_count_label = QLabel("Reminders: 0")
        self.reminder_count_label.setObjectName("ReminderCountLabel")
        button_layout.addWidget(self.reminder_count_label)

        button_layout.addStretch()
        main_layout.addWidget(top_button_bar) # Add the button bar widget

        # Webcam feed area
        webcam_frame = QFrame() # Use a QFrame for better styling options (e.g. border, background)
        webcam_frame.setObjectName("CameraViewFrame") # Matches QSS
        webcam_frame_layout = QVBoxLayout(webcam_frame)
        webcam_frame_layout.setContentsMargins(0,0,0,0)
        self.webcam_feed_label = QLabel("Initializing camera...") # Initial text
        self.webcam_feed_label.setObjectName("WebcamFeedLabel") # Matches QSS
        self.webcam_feed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Removed fixed size to allow QFrame to manage it, or use setSizePolicy
        self.webcam_feed_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        webcam_frame_layout.addWidget(self.webcam_feed_label)
        # The QFrame itself can have a fixed size or be expansive
        webcam_frame.setFixedSize(640, 480) # Or use layout to control size
        main_layout.addWidget(webcam_frame, alignment=Qt.AlignmentFlag.AlignCenter)

        # Calibration overlay widgets
        self.calib_overlay = QWidget()
        self.calib_overlay.setObjectName("CalibrationOverlay")
        calib_layout = QVBoxLayout()
        self.calib_instructions = QLabel(
            "Sit upright, shoulders relaxed and back. Align your head over your shoulders, looking straight ahead. Match the example postures shown below. Click 'Capture Good Posture' when ready."
        )
        self.calib_instructions.setObjectName("CalibrationInstructionsLabel")
        self.calib_instructions.setProperty("class", "BodyPrimary") # Use BodyPrimary for good readability
        self.calib_instructions.setWordWrap(True)
        self.calib_instructions.setStyleSheet("background: transparent;")
        calib_layout.addWidget(self.calib_instructions)

        # Image container for side-by-side example postures
        image_container_layout = QHBoxLayout()
        image_container_layout.setSpacing(20)

        self.front_view_image_label = QLabel()
        self.side_view_image_label = QLabel()

        image_height = 360 # Desired height for the example images

        # Use resource_path here
        front_image_path = resource_path(os.path.join('resources', 'icons', 'calibration_posture.jpg'))
        if os.path.exists(front_image_path):
            front_pixmap = QPixmap(front_image_path)
            self.front_view_image_label.setPixmap(front_pixmap.scaledToHeight(image_height, Qt.TransformationMode.SmoothTransformation))
        else:
            self.front_view_image_label.setText("Front View Image Missing")
            print(f"Warning: Front view calibration image not found at {front_image_path}")
        self.front_view_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_container_layout.addWidget(self.front_view_image_label)

        # Use resource_path here
        side_image_path = resource_path(os.path.join('resources', 'icons', 'side_posture.jpg'))
        if os.path.exists(side_image_path):
            side_pixmap = QPixmap(side_image_path)
            self.side_view_image_label.setPixmap(side_pixmap.scaledToHeight(image_height, Qt.TransformationMode.SmoothTransformation))
        else:
            self.side_view_image_label.setText("Side View Image Missing")
            print(f"Warning: Side view calibration image not found at {side_image_path}")
        self.side_view_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_container_layout.addWidget(self.side_view_image_label)
        
        calib_layout.addLayout(image_container_layout) # Add the hbox for images

        # Buttons
        btn_row = QHBoxLayout()
        self.capture_btn = QPushButton('Capture Good Posture')
        self.capture_btn.setObjectName("PrimaryCTA") # Primary action in this context
        icon_capture = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton) # Changed to a valid standard icon
        self.capture_btn.setIcon(icon_capture)
        self.capture_btn.clicked.connect(self.capture_good_posture)
        btn_row.addWidget(self.capture_btn)

        self.cancel_calib_btn = QPushButton('Cancel Calibration')
        self.cancel_calib_btn.setProperty("class", "Secondary") # Secondary action
        icon_cancel = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton)
        self.cancel_calib_btn.setIcon(icon_cancel)
        btn_row.addWidget(self.cancel_calib_btn)
        calib_layout.addLayout(btn_row)
        self.calib_overlay.setLayout(calib_layout)
        self.calib_overlay.hide()
        main_layout.addWidget(self.calib_overlay, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- Posture Reminders Over Time section --- (Using QGroupBox)
        graph_group = QGroupBox("Posture Reminders Over Time")
        graph_group.setObjectName("GraphDisplayGroup") # Matches QSS for potential specific styling
        graph_layout = QVBoxLayout()
        graph_layout.setSpacing(10)
        self.session_graph = SessionGraphCanvas(self)
        # graph_label removed as QGroupBox provides a title
        graph_layout.addWidget(self.session_graph, alignment=Qt.AlignmentFlag.AlignCenter)
        graph_group.setLayout(graph_layout)
        main_layout.addWidget(graph_group)

        # Update notification label (hidden by default)
        self.update_notification_label = QLabel()
        self.update_notification_label.setObjectName("UpdateNotificationLabel") # For QSS styling
        self.update_notification_label.setStyleSheet("background: transparent;")
        self.update_notification_label.setVisible(False)
        # self._update_download_urls = None
        # self._update_notes = None
        # self._update_version = None
        # Insert at top of layout
        main_layout.insertWidget(0, self.update_notification_label)

        # Status/alert label for webcam/landmark issues
        self.status_label = QLabel()
        self.status_label.setObjectName("StatusAlertLabel") # For QSS styling
        self.status_label.setStyleSheet("background: transparent;")
        self.status_label.setVisible(False)
        main_layout.insertWidget(1, self.status_label)  # Just below update label
        self._landmark_missing_since = None

        main_layout.addStretch()
        self.setLayout(main_layout)

        # Add to __init__ of DashboardView:
        self._bad_posture_start_time = None  # Track when bad posture started

        # Initialize speaker_wav_path based on current settings loaded into self.app_settings
        default_speaker_path = resource_path("audio/Leif GW.wav") # Define a clear default
        self.speaker_wav_path = self.app_settings.get("speaker_wav_path", default_speaker_path)
        if not self.speaker_wav_path or not os.path.exists(self.speaker_wav_path):
            print(f"Warning: Initial speaker WAV file '{self.speaker_wav_path}' not found or not set. Falling back to default.")
            self.speaker_wav_path = default_speaker_path
            if not os.path.exists(self.speaker_wav_path):
                 print(f"Warning: Default speaker WAV '{os.path.basename(default_speaker_path)}' also not found. TTS may not use a custom speaker.")
                 self.speaker_wav_path = None # No valid speaker WAV found
        else:
            print(f"Initialized with speaker WAV: {self.speaker_wav_path}")

    def start_calibration(self):
        if self.session_active or self.calibrating:
            return
        # Webcam presence check
        cameras = get_available_cameras()
        if not cameras:
            QMessageBox.critical(self, "No Webcam Detected", "No webcam detected. Please connect a webcam to use Ergo.")
            return
        self.calibrating = True
        self.start_session_btn.setEnabled(False)
        self.stop_session_btn.setEnabled(False)
        self.calib_overlay.show()
        # Start webcam if not running
        if not self.webcam_thread:
            cam_idx = self.app_settings.get("webcam_index", 0)
            show_lm_setting = self.app_settings.get("show_landmarks", True)
            self.webcam_thread = WebcamThread(camera_index=cam_idx, show_landmarks=show_lm_setting)
            self.webcam_thread.new_frame_ready.connect(self.update_webcam_feed)
            self.webcam_thread.error_occurred.connect(self.handle_webcam_error)
            self.webcam_thread.pose_processor = None  # force re-init if needed
            self.webcam_thread._init_pose_landmarker()
            self.webcam_thread.latest_landmarks_callback = self.receive_landmarks
            self.webcam_thread.start_capture()

    def receive_landmarks(self, landmarks):
        self.latest_landmarks = landmarks

    def update_webcam_feed(self, qt_image):
        pixmap = QPixmap.fromImage(qt_image)
        self.webcam_feed_label.setPixmap(pixmap.scaled(self.webcam_feed_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        now = time.time()
        landmarks = self.webcam_thread.latest_pose_landmarks if self.webcam_thread else None
        
        if self.calibrating or self.session_active:
            if not landmarks:
                if not self._landmark_missing_since:
                    self._landmark_missing_since = now
                elapsed = now - self._landmark_missing_since
                if elapsed > 1.5:  
                    self.status_label.setText("Cannot detect posture. Ensure face and shoulders are clearly visible, improve lighting, or move closer.")
                    self.status_label.setVisible(True)
            else:
                self._landmark_missing_since = None
                self.status_label.setVisible(False)

        if (self.session_active and 
            self.session_start_time is not None and 
            self.reference_angles.get('head_forward') is not None and 
            self.reference_angles.get('shoulder_line') is not None and 
            self.reference_angles.get('neck_dx') is not None and 
            self.reference_angles.get('inter_shoulder_distance') is not None):
            if landmarks:
                try:
                    current_calculated_values = self.calculate_reference_angles(landmarks)
                    threshold_angle = self.app_settings.get("sensitivity_degrees", 40)
                    sensitivity_setting_str = self.app_settings.get("sensitivity_string", "Low") # Default to Low

                    # Define ratios based on sensitivity string
                    if sensitivity_setting_str == "High":
                        current_head_ratio = 0.02  # Stricter for High sensitivity
                        current_shoulder_ratio = 0.04 # Stricter for High sensitivity
                    elif sensitivity_setting_str == "Low":
                        current_head_ratio = 0.6  # Looser for Low sensitivity
                        current_shoulder_ratio = 0.12 # Looser for Low sensitivity
                    else: # Medium or fallback
                        current_head_ratio = 0.04
                        current_shoulder_ratio = 0.08
                    # Primary angle deviation checks
                    head_angle_deviation = abs(current_calculated_values['head_forward'] - self.reference_angles['head_forward'])
                    shoulder_angle_deviation = abs(current_calculated_values['shoulder_line'] - self.reference_angles['shoulder_line'])
                    
                    head_angle_bad = head_angle_deviation > threshold_angle
                    shoulder_angle_bad = shoulder_angle_deviation > threshold_angle

                    # Secondary check for head forward tilt (horizontal shift)
                    head_horizontal_shift = abs(current_calculated_values['neck_dx'] - self.reference_angles['neck_dx'])
                    # Use calibrated inter_shoulder_distance for a stable reference for this threshold
                    head_horizontal_shift_limit = self.reference_angles['inter_shoulder_distance'] * current_head_ratio 
                    head_shift_bad = head_horizontal_shift > head_horizontal_shift_limit
                    
                    # Secondary check for shoulder tilt (vertical difference)
                    vertical_shoulder_diff = current_calculated_values['vertical_shoulder_difference']
                    # Use current inter_shoulder_distance as this is about current geometry proportions
                    current_inter_shoulder_dist = current_calculated_values['inter_shoulder_distance'] 
                    shoulder_vertical_limit = current_inter_shoulder_dist * current_shoulder_ratio
                    shoulder_vertical_diff_bad = vertical_shoulder_diff > shoulder_vertical_limit

                    alert_for_head = head_angle_bad and head_shift_bad
                    alert_for_shoulder = shoulder_angle_bad and shoulder_vertical_diff_bad

                    posture_broken = alert_for_head or alert_for_shoulder
                    
                    if posture_broken:
                        if self._bad_posture_start_time is None:
                            self._bad_posture_start_time = now
                        bad_posture_duration = now - self._bad_posture_start_time

                        # Check for alert conditions
                        if bad_posture_duration >= 2.0: # Held bad posture for 2s
                            if now - self._last_alert_time >= self.alert_interval: # Cooldown passed
                                # --- This is an alert event ---
                                self.current_session_reminder_count += 1
                                self.reminder_count_label.setText(f"Reminders: {self.current_session_reminder_count}")
                                
                                time_elapsed_seconds = now - self.session_start_time
                                self.current_session_live_reminder_data.append((time_elapsed_seconds, self.current_session_reminder_count))
                                self.session_graph.plot_live_data(self.current_session_live_reminder_data)
                                
                                notification_mode = self.app_settings.get("notification_mode", "both")
                                alert_message_text = self.app_settings.get('custom_alert_message', 'Fix your posture!')

                                if notification_mode in ["visual", "both"]:
                                    toast = CustomNotificationToast(alert_message_text, parent=self)
                                    toast.show_toast()
                                
                                if notification_mode in ["audio", "both"]:
                                    # Pass the actual alert message text to _speak_alert
                                    threading.Thread(target=self._speak_alert, args=(alert_message_text,), daemon=True).start() 
                                
                                self._last_alert_time = now # Update last alert time
                    else: # Posture is not broken
                        self._bad_posture_start_time = None
                        # bad_posture_duration = 0 # Not strictly needed here

                except Exception as e:
                    print(f"Deviation calculation error: {e}")

    def capture_good_posture(self):
        # Get latest landmarks from MediaPipe
        if not self.webcam_thread or not self.webcam_thread.latest_pose_landmarks:
            self.status_label.setText("Cannot detect posture. Ensure face and shoulders are clearly visible, improve lighting, or move closer.")
            self.status_label.setVisible(True)
            QMessageBox.warning(self, "Calibration Failed", "No pose detected. Please ensure your face and shoulders are visible to the camera.")
            return
        self.status_label.setVisible(False)
        landmarks = self.webcam_thread.latest_pose_landmarks
        # Calculate reference angles
        try:
            ref_values = self.calculate_reference_angles(landmarks)
            self.reference_angles = {
                'head_forward': ref_values['head_forward'],
                'shoulder_line': ref_values['shoulder_line'],
                'neck_dx': ref_values['neck_dx'],
                'inter_shoulder_distance': ref_values['inter_shoulder_distance']
            }
            self.calib_overlay.hide()
            self.session_active = True
            self.is_calibrated = True # Set calibrated to True
            self.current_session_reminders = 0
            self.reminder_count_label.setText(f"Reminders: {self.current_session_reminders}")
            print("[DEBUG] DashboardView.session_active set to True in capture_good_posture")
            self.calibrating = False
            self.start_session_btn.setEnabled(False)
            self.stop_session_btn.setEnabled(True)
            
            self.session_start_time = time.time() # Record session start time
            self.current_session_reminder_count = 0 
            self.current_session_live_reminder_data = [] 
            # Add an initial point at t=0 with 0 reminders for the line to start from the origin
            self.current_session_live_reminder_data.append((0, 0))
            self.session_graph.plot_live_data(self.current_session_live_reminder_data) 

            QMessageBox.information(self, "Calibration Successful", "Calibration successful! Monitoring started.")
            self.calibration_successful_and_session_started.emit()
        except Exception as e:
            QMessageBox.warning(self, "Calibration Failed", f"Error: {e}")

    def cancel_calibration(self):
        self.calibrating = False
        self.is_calibrated = False # Reset calibration status
        self.calib_overlay.hide()
        self.stop_webcam()
        self.webcam_feed_label.clear()
        self.webcam_feed_label.setStyleSheet('background-color: black; border: 1px solid #aaa;')
        self.start_session_btn.setEnabled(True)
        self.stop_session_btn.setEnabled(False)
        # Revert graph to historical if calibration is cancelled
        self.update_session_graph()

    def stop_session(self):
        print("[DEBUG] DashboardView.stop_session() called")
        if not self.session_active:
            print("[DEBUG] DashboardView.stop_session() returning early - session not active.")
            return

        self.session_active = False
        self.is_calibrated = False # Reset calibration status
        print(f"[DEBUG] DashboardView.session_active set to {self.session_active}")
        self.stop_webcam()
        print("[DEBUG] DashboardView.stop_webcam() returned")

        reminders = self.current_session_reminder_count
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            add_session_data(today, reminders)
            # After saving, switch graph to historical data
            self.update_session_graph() 
            QMessageBox.information(self, "Session Ended", f"Session ended. Reminders this session: {reminders}")
        except Exception as e:
            print(f"Error during session stop (data saving/graph update): {e}")
            QMessageBox.warning(self, "Session Stop Issue", f"Session stopped. Reminders: {reminders}.\nHowever, there was an issue saving session data or updating the graph.")
            # Still try to update graph to historical view even if save failed
            self.update_session_graph()
        finally:
            self.current_session_reminder_count = 0
            self.current_session_live_reminder_data = [] 
            self.session_start_time = None # Reset session start time
            self.reference_angles = {'head_forward': None, 'shoulder_line': None}
            self.webcam_feed_label.clear()
            self.webcam_feed_label.setStyleSheet('background-color: black; border: 1px solid #aaa;')
            self.start_session_btn.setEnabled(True)
            self.stop_session_btn.setEnabled(False)
            # Ensure graph is showing historical data if it wasn't updated in try/except
            if self.session_graph.current_graph_type != "historical":
                 self.update_session_graph()

    def stop_webcam(self):
        print("[DEBUG] DashboardView.stop_webcam() called")
        if self.webcam_thread:
            self.webcam_thread.stop_capture()
            self.webcam_thread = None
            print("[DEBUG] DashboardView.webcam_thread stopped and set to None")
        else:
            print("[DEBUG] DashboardView.stop_webcam() - no webcam_thread to stop")

    def calculate_reference_angles(self, landmarks):
        # Helper indices
        NOSE = 0
        LEFT_EAR = 7
        RIGHT_EAR = 8
        LEFT_SHOULDER = 11
        RIGHT_SHOULDER = 12

        # Extract coordinates
        nose_pt = landmarks[NOSE]
        left_ear_pt = landmarks[LEFT_EAR]
        right_ear_pt = landmarks[RIGHT_EAR]
        left_shoulder_pt = landmarks[LEFT_SHOULDER]
        right_shoulder_pt = landmarks[RIGHT_SHOULDER]

        ear_midpoint = self.calculate_midpoint(left_ear_pt, right_ear_pt)
        shoulder_midpoint = self.calculate_midpoint(left_shoulder_pt, right_shoulder_pt)
        
        neck_dx = ear_midpoint[0] - shoulder_midpoint[0]
        neck_dy_for_atan2 = shoulder_midpoint[1] - ear_midpoint[1]
        neck_posture_angle_rad = math.atan2(neck_dx, neck_dy_for_atan2)

        shoulder_line_angle_rad = math.atan2(
            right_shoulder_pt[1] - left_shoulder_pt[1],
            right_shoulder_pt[0] - left_shoulder_pt[0]
        )

        # Calculate additional metrics for secondary checks
        inter_shoulder_distance = math.sqrt(
            (right_shoulder_pt[0] - left_shoulder_pt[0])**2 +
            (right_shoulder_pt[1] - left_shoulder_pt[1])**2
        )
        # Ensure distance is not zero to avoid division by zero if landmarks are coincident
        if inter_shoulder_distance < 1e-6: # Using a small epsilon
            inter_shoulder_distance = 1e-6

        vertical_shoulder_difference = abs(right_shoulder_pt[1] - left_shoulder_pt[1])

        return {
            'head_forward': math.degrees(neck_posture_angle_rad),
            'shoulder_line': math.degrees(shoulder_line_angle_rad),
            'neck_dx': neck_dx,  # Horizontal distance ear_mid to shoulder_mid
            'inter_shoulder_distance': inter_shoulder_distance, # Distance between shoulders
            'vertical_shoulder_difference': vertical_shoulder_difference # Abs Y-diff between shoulders
        }

    @staticmethod
    def calculate_midpoint(lm1, lm2):
        return [(lm1[0] + lm2[0]) / 2, (lm1[1] + lm2[1]) / 2]

    def update_user_info(self, email, status=None, expires_at=None):
        self.user_email = email
        # The UI elements for displaying this directly on DashboardView are removed.
        # This method can still be used to store the info if needed for other purposes (e.g. tray tooltip)
        if status and expires_at:
            try:
                expires_dt = datetime.fromisoformat(expires_at)
                expires_str = expires_dt.strftime('%Y-%m-%d')
                # Example: self.current_subscription_details = f"Subscription: {status.capitalize()} until {expires_str}"
            except Exception:
                # self.current_subscription_details = f"Subscription: {status.capitalize()} until {expires_at}"
                pass # Store as is if parsing fails
        else:
            # self.current_subscription_details = f"Subscription Status: - for {email}"
            pass

    def open_manage_subscription(self):
        QDesktopServices.openUrl(QUrl(MANAGE_SUBSCRIPTION_URL))

    def handle_logout(self):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        # Clear session-specific data
        self.user_email = None
        self.subscription_status_str = None
        self.reference_angles = {'head_forward': None, 'shoulder_line': None}
        self.current_session_reminder_count = 0
        self.session_active = False
        self.calibrating = False
        self.stop_webcam()
        self.webcam_feed_label.clear()
        self.webcam_feed_label.setStyleSheet('background-color: black; border: 1px solid #aaa;')
        self.status_label.setVisible(False)
        self.session_start_time = None # Reset session start time on logout
        self.current_session_live_reminder_data = [] # Clear live data
        if self.on_logout_callback:
            self.on_logout_callback()
        # Ensure graph shows historical after logout
        self.update_session_graph()

    def open_settings_dialog(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    def apply_settings(self):
        old_cam_idx = self.app_settings.get("webcam_index", 0)
        old_selected_voice_file_name = self.app_settings.get("selected_voice_file", "Leif GW.wav")

        self.app_settings = self.load_app_settings() # Reload all settings, including new speaker_wav_path

        new_cam_idx = self.app_settings.get("webcam_index", 0)
        new_show_lm_setting = self.app_settings.get("show_landmarks", True)
        new_selected_voice_file_name = self.app_settings.get("selected_voice_file", "Leif GW.wav")
        
        # Update speaker_wav_path for the dashboard instance
        default_speaker_path = resource_path("audio/Leif GW.wav") # Define a clear default
        self.speaker_wav_path = self.app_settings.get("speaker_wav_path", default_speaker_path)
        if not self.speaker_wav_path or not os.path.exists(self.speaker_wav_path):
            print(f"Warning: Speaker WAV '{self.speaker_wav_path}' from settings not found. Falling back to default.")
            self.speaker_wav_path = default_speaker_path
            if not os.path.exists(self.speaker_wav_path):
                 print(f"Warning: Default speaker WAV '{os.path.basename(default_speaker_path)}' also not found during settings apply. TTS speaker disabled.")
                 self.speaker_wav_path = None
        else:
            print(f"Applied speaker WAV path from settings: {self.speaker_wav_path}")

        # If the voice file NAME changed, clear TTS cache
        if old_selected_voice_file_name != new_selected_voice_file_name:
            print(f"Speaker voice file changed from '{old_selected_voice_file_name}' to '{new_selected_voice_file_name}'. Clearing TTS cache.")
            self._cached_tts_text = None 
            self._last_tts_text = None   
            if self._cached_tts_file and os.path.exists(self._cached_tts_file):
                try:
                    os.remove(self._cached_tts_file)
                    print(f"Removed old cached TTS file: {self._cached_tts_file}")
                except OSError as e:
                    print(f"Error removing old cached TTS file: {e}")
            # _cached_tts_file path remains the same, but its content is now invalid for the new voice

        if self.webcam_thread:
            if old_cam_idx != new_cam_idx:
                # Camera changed, stop and restart webcam
                self.stop_webcam()
                if self.session_active or self.calibrating: # Only restart if a session was active or calibrating
                    self.webcam_thread = WebcamThread(camera_index=new_cam_idx, show_landmarks=new_show_lm_setting)
                    self.webcam_thread.new_frame_ready.connect(self.update_webcam_feed)
                    self.webcam_thread.error_occurred.connect(self.handle_webcam_error)
                    # self.webcam_thread.latest_landmarks_callback = self.receive_landmarks # If you still use this
                    self.webcam_thread.start_capture()
            elif self.webcam_thread.isRunning():
                # Camera did not change, but landmarks visibility might have
                self.webcam_thread.set_show_landmarks(new_show_lm_setting)

    def load_app_settings(self):
        settings = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)
        sens = settings.value("sensitivity", "Medium")
        notif = settings.value("notification_mode", "both")
        custom_msg = settings.value("custom_alert_message", "Fix your posture!")
        # Ensure webcam_idx is an int, even if QSettings returns None
        webcam_idx_setting = settings.value("webcam_index", 0)
        webcam_idx = int(webcam_idx_setting) if webcam_idx_setting is not None else 0
        show_lm = settings.value("show_landmarks", True, type=bool)
        selected_voice_file = settings.value("selected_voice_file", "Leif GW.wav") # Default voice

        # Map sensitivity to degrees (High:20, Medium:30, Low:40)
        if sens == "Low":
            sens_deg = 40
        elif sens == "High":
            sens_deg = 20
        else: # Default to Medium
            sens_deg = 30
        return {
            "sensitivity_string": sens, # Store the original sensitivity string
            "sensitivity_degrees": sens_deg,
            "notification_mode": notif,
            "custom_alert_message": custom_msg,
            "webcam_index": webcam_idx,
            "show_landmarks": show_lm,
            "selected_voice_file": selected_voice_file, # Store the raw file name
            "speaker_wav_path": resource_path(os.path.join("resources", "audio", selected_voice_file)) # Store the full path
        }

    def showEvent(self, event):
        super().showEvent(event)
        if self.session_active and self.session_start_time is not None:
            self.session_graph.plot_live_data(self.current_session_live_reminder_data)
        else:
            self.update_session_graph()
        self.check_for_updates()

    def update_session_graph(self):
        session_data = get_session_data()
        self.session_graph.plot_historical_data(session_data)

    def check_for_updates(self):
        try:
            resp = requests.get(UPDATE_INFO_URL, timeout=5)
            if resp.status_code != 200:
                return
            data = resp.json()
            remote_version = data.get("version")
            notes = data.get("notes", "")
            download_urls = data.get("download_urls", {})
            if remote_version and self._is_newer_version(remote_version, CURRENT_APP_VERSION):
                self._update_download_urls = download_urls
                self._update_notes = notes
                self._update_version = remote_version
                self.update_notification_label.setText(f'<b>Update available:</b> Version {remote_version}. <u>Click here to download.</u>')
                self.update_notification_label.setVisible(True)
            else:
                self.update_notification_label.setVisible(False)
        except ConnectionError:
            # Show a brief status message for update check failure
            self.status_label.setText("Could not check for updates: No internet.")
            self.status_label.setVisible(True)
            QTimer.singleShot(3000, lambda: self.status_label.setVisible(False))
            self.update_notification_label.setVisible(False)
        except Exception as e:
            print(f"Update check failed: {e}")
            self.update_notification_label.setVisible(False)

    @staticmethod
    def _is_newer_version(remote, current):
        # Simple semantic version comparison
        def parse(v):
            return [int(x) for x in v.split('.') if x.isdigit()]
        try:
            r, c = parse(remote), parse(current)
            return r > c
        except Exception:
            return remote > current  # fallback to string compare

    def _on_update_label_clicked(self, event):
        plat = get_platform()
        url = self._update_download_urls.get(plat) if self._update_download_urls else None
        if not url:
            QDesktopServices.openUrl(QUrl("https://example.com"))  # fallback
            return
        # Download the installer in background
        temp_dir = tempfile.gettempdir()
        filename = os.path.basename(url.split('?')[0])
        dest_path = os.path.join(temp_dir, filename)
        self.progress_dialog = QProgressDialog("Downloading update...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle("Downloading Update")
        self.progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.progress_dialog.setValue(0)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.canceled.connect(self._cancel_update_download)
        self._update_download_thread = UpdateDownloadThread(url, dest_path)
        self._update_download_thread.progress_changed.connect(self.progress_dialog.setValue)
        self._update_download_thread.download_finished.connect(self._on_update_download_finished)
        self._update_download_thread.start()
        self.progress_dialog.show()
        self._update_download_canceled = False
        self._update_download_path = dest_path

    def _cancel_update_download(self):
        self._update_download_canceled = True
        if hasattr(self, '_update_download_thread') and self._update_download_thread.isRunning():
            self._update_download_thread.terminate()
        self.progress_dialog.cancel()

    def _on_update_download_finished(self, file_path, error):
        self.progress_dialog.hide()
        if self._update_download_canceled:
            return
        if error:
            QMessageBox.critical(self, "Download Failed", f"Failed to download update: {error}")
            return
        # Download successful
        notes = self._update_notes or ""
        version = self._update_version or ""
        reply = QMessageBox.question(
            self,
            f"Update {version} Downloaded",
            f"Update {version} downloaded.\n\nRelease notes:\n{notes}\n\nRestart and install now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Open folder containing the installer
            folder = os.path.dirname(file_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
            QMessageBox.information(self, "Install Update", "Please run the downloaded installer. The application will now close.")
            QApplication.quit()
        # else: do nothing (user chose to install later)

    def handle_webcam_error(self, msg):
        self.status_label.setText(msg)
        self.status_label.setVisible(True)
        self.stop_webcam()
        self.webcam_feed_label.clear()
        self.webcam_feed_label.setStyleSheet('background-color: black; border: 1px solid #aaa;')
        self.start_session_btn.setEnabled(True)
        self.stop_session_btn.setEnabled(False)
        if len(get_available_cameras()) > 1:
            # Ensure the message is generic or updated if it mentions the old app name
            current_msg = self.status_label.text()
            if "Axial" in current_msg: # Check for old name
                 current_msg = current_msg.replace("Axial", "Ergo")
            elif "PostureApp" in current_msg: # Check for even older name
                 current_msg = current_msg.replace("PostureApp", "Ergo")
            self.status_label.setText(current_msg + " Try another webcam in Settings.")
        # Example of how to use a QMessageBox with the new app name if needed here:
        # QMessageBox.warning(self, "Webcam Issue - Ergo", msg)

    def _initialize_tts_engine(self):
        if self.tts_engine is None:
            try:
                print("Initializing Coqui TTS engine...")
                self.show_toast_signal.emit("Downloading voice model... This may take a few minutes.", 5000)
                
                # Determine device for Coqui TTS
                device = "cuda" if torch.cuda.is_available() else "cpu"
                print(f"Attempting to initialize Coqui TTS on device: {device}")

                self.tts_engine = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
                self.tts_engine.to(device) # Move the TTS engine to the selected device

                print(f"Coqui TTS engine initialized and moved to {device}.")
                self.show_toast_signal.emit("Voice model ready!", 3000)
            except Exception as e:
                print(f"Failed to initialize Coqui TTS engine: {e}")
                traceback.print_exc()
                self.tts_engine = None # Ensure it's None on failure
                self.show_toast_signal.emit("TTS engine failed to load. Voice alerts disabled.", 5000)
        else:
            print("Coqui TTS engine already initialized.")

    def _speak_alert(self, alert_text_to_speak): # Modified signature
        print("[DEBUG] _speak_alert entered.") # Debug print
        if not self.session_active or not self.is_calibrated:
            print("[DEBUG] _speak_alert: Session not active or not calibrated. Returning.") # Debug print
            return
        
        # alert_text is now passed as alert_text_to_speak
        
        # Check if TTS engine is ready (initialized in __init__ thread)
        if self.tts_engine is None:
            print("TTS engine not yet available or failed to initialize. Cannot speak alert.")
            return

        try:
            if self._cached_tts_file and self._last_tts_text == alert_text_to_speak:
                self.tts_play.emit(self._cached_tts_file)
            else:
                if self._cached_tts_file and os.path.exists(self._cached_tts_file):
                    try:
                        os.remove(self._cached_tts_file)
                    except OSError as e:
                        print(f"Error removing old cached TTS file: {e}")
                
                temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav').name
                
                print(f"Synthesizing TTS for: '{alert_text_to_speak}'")
                speaker_wav_arg = self.speaker_wav_path if self.speaker_wav_path and os.path.exists(self.speaker_wav_path) else None
                
                self.tts_engine.tts_to_file(
                    text=alert_text_to_speak,
                    speaker_wav=speaker_wav_arg,
                    language='en', 
                    file_path=temp_audio_file
                )
                
                self._cached_tts_file = temp_audio_file
                self._last_tts_text = alert_text_to_speak
                self.tts_play.emit(self._cached_tts_file)

            # REMOVED: Reminder count and graph updates are now handled in update_webcam_feed
            # self.current_session_reminder_count += 1
            # self.reminder_count_label.setText(f"Reminders: {self.current_session_reminder_count}")
            # current_time_elapsed = time.time() - self.session_start_time
            # self.current_session_live_reminder_data.append((current_time_elapsed, self.current_session_reminder_count))
            # self.session_graph.plot_live_data(self.current_session_live_reminder_data)

        except ConnectionError as e:
            # This might have been relevant for edge_tts, less so for local Coqui unless model download fails
            print(f"TTS Connection Error: {e}. Using cached or no audio.")
            if self._cached_tts_file and os.path.exists(self._cached_tts_file):
                self.tts_play.emit(self._cached_tts_file)
        except RuntimeError as e:
            # Catch potential runtime errors from PyTorch/TTS, e.g. CUDA issues
             print(f"TTS Runtime Error: {e}")
             traceback.print_exc()
             self.show_toast_signal.emit("TTS synthesis failed. Voice alert skipped.", 5000)
        except Exception as e:
            print(f"Error in _speak_alert with Coqui TTS: {e}")
            traceback.print_exc()
            # Optionally, emit cached file if available as a fallback
            if self._cached_tts_file and os.path.exists(self._cached_tts_file):
                self.tts_play.emit(self._cached_tts_file)

    def _play_media(self, file_path):
        """
        Play the given media file using QtMultimedia and clean up after playback.
        """
        # DEBUG: beginning playback
        print(f"[_play_media] Received request to play file: {file_path}") # Debug print
        if not file_path or not os.path.exists(file_path):
            print(f"[_play_media] Error: File path is invalid or file does not exist: {file_path}") # Debug print
            return

        print(f"[_play_media] Playing file: {file_path}")
        player = QMediaPlayer()
        audio_output = QAudioOutput()
        # Ensure volume is up
        audio_output.setVolume(1.0)
        player.setAudioOutput(audio_output)

        def on_status(status):
            from PyQt6.QtMultimedia import QMediaPlayer as _MP
            print(f"[_play_media] Player status changed: {status}, for file: {file_path}") # Debug print

            if status == _MP.MediaStatus.EndOfMedia or status == _MP.MediaStatus.InvalidMedia:
                if status == _MP.MediaStatus.InvalidMedia:
                    error_string = player.errorString()
                    print(f"[_play_media] Error playing media (InvalidMedia): {player.error()} - {error_string} for file: {file_path}") # Debug print
                player.stop()
                player.deleteLater()
                audio_output.deleteLater()
                # Do not remove the cached TTS file; keep it for future alerts
                self._active_players = [
                    ap for ap in getattr(self, '_active_players', []) if ap[2] != file_path
                ]

        player.mediaStatusChanged.connect(on_status)
        player.errorOccurred.connect(lambda error, error_string: print(f"[_play_media] QMediaPlayer errorOccurred: {error} - {error_string} for file: {file_path}")) # Debug print
        player.setSource(QUrl.fromLocalFile(file_path))
        player.play()
        # Keep reference to prevent GC
        self._active_players = getattr(self, '_active_players', [])
        self._active_players.append((player, audio_output, file_path))

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Ergo")
        layout = QVBoxLayout()
        layout.setSpacing(14)

        # App name - now a clickable link
        app_name = QLabel(f'<a href="{WEB_APP_BASE_URL}/about">Ergo</a>')
        app_name.setOpenExternalLinks(True) # Allow clicking the link
        font = QFont()
        font.setPointSize(22)
        font.setBold(True)
        app_name.setFont(font)
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_name.setWordWrap(True)
        layout.addWidget(app_name)

        # Version
        version_label = QLabel(f"Version: {CURRENT_APP_VERSION}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setWordWrap(True)
        layout.addWidget(version_label)

        # Copyright
        year = datetime.now().year
        copyright_label = QLabel(f"© {year} devdash AB. All rights reserved.")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copyright_label.setWordWrap(True)
        layout.addWidget(copyright_label)

        # Description
        desc = QLabel("Ergo helps you improve your posture using your webcam and real-time feedback.")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        # Privacy
        privacy = QLabel("Webcam processing is done locally on your computer. No images or video are transmitted or stored.")
        privacy.setWordWrap(True)
        privacy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(privacy)

        # Links
        links_layout = QVBoxLayout()
        privacy_link = QLabel(f'<a href="{WEB_APP_BASE_URL}/privacy-policy">Privacy Policy</a>')
        privacy_link.setOpenExternalLinks(True)
        privacy_link.setWordWrap(True)
        help_link = QLabel(f'<a href="{WEB_APP_BASE_URL}/help">Help/Documentation</a>')
        help_link.setOpenExternalLinks(True)
        help_link.setWordWrap(True)
        contact_link = QLabel(f'<a href="{WEB_APP_BASE_URL}/contact">Contact Us/Support</a>')
        contact_link.setOpenExternalLinks(True)
        contact_link.setWordWrap(True)
        terms_link = QLabel(f'<a href="{WEB_APP_BASE_URL}/terms-of-service">Terms of Service</a>') # Added Terms link
        terms_link.setOpenExternalLinks(True)
        terms_link.setWordWrap(True)

        for link in (privacy_link, help_link, contact_link, terms_link): # Added terms_link
            link.setAlignment(Qt.AlignmentFlag.AlignCenter)
            links_layout.addWidget(link)
        layout.addLayout(links_layout)

        # OK button
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)
        self.adjustSize()
        self.setMinimumSize(self.sizeHint())
        self.setSizeGripEnabled(True)

def get_platform():
    system = platform.system().lower()
    if 'windows' in system:
        return 'windows'
    elif 'darwin' in system or 'mac' in system:
        return 'macos'
    elif 'linux' in system:
        return 'linux'
    else:
        return 'windows'  # fallback

class UpdateDownloadThread(QThread):
    progress_changed = pyqtSignal(int)
    download_finished = pyqtSignal(str, str)  # file_path, error (None if success)

    def __init__(self, url, dest_path):
        super().__init__()
        self.url = url
        self.dest_path = dest_path

    def run(self):
        try:
            with requests.get(self.url, stream=True, timeout=10) as r:
                r.raise_for_status()
                total = int(r.headers.get('content-length', 0))
                with open(self.dest_path, 'wb') as f:
                    downloaded = 0
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total > 0:
                                percent = int(downloaded * 100 / total)
                                self.progress_changed.emit(percent)
            self.download_finished.emit(self.dest_path, None)
        except Exception as e:
            self.download_finished.emit('', str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Ergo')

        # Define icon path using resource_path
        self.icon_path = resource_path(os.path.join('resources', 'icons', 'ergo-logo.png'))

        # Menu bar
        menubar = self.menuBar()

        # View Menu
        view_menu = menubar.addMenu("View")
        self.fullscreen_action = QAction("Toggle Fullscreen", self, checkable=True)
        self.fullscreen_action.setShortcut(Qt.Key.Key_F11)
        self.fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(self.fullscreen_action)

        # Help Menu (existing)
        help_menu = menubar.addMenu("Help")
        about_action = QAction("About Ergo", self)
        help_menu.addAction(about_action)
        about_action.triggered.connect(self.show_about_dialog)

        self.stacked_widget = QStackedWidget()
        self.login_view = LoginView(on_login=self.show_dashboard_view)
        self.dashboard_view = DashboardView(on_logout=self.show_login_view)

        # Wrap dashboard_view in a QScrollArea for scrollability
        self.dashboard_scroll_area = QScrollArea()
        self.dashboard_scroll_area.setWidgetResizable(True)
        self.dashboard_scroll_area.setWidget(self.dashboard_view)

        self.stacked_widget.addWidget(self.login_view)      # Index 0
        self.stacked_widget.addWidget(self.dashboard_scroll_area)  # Index 1

        self.setCentralWidget(self.stacked_widget)
        self.stacked_widget.setCurrentIndex(0)  # Show LoginView on startup
        self.current_user_email = None
        self.current_subscription_status = None
        self.current_subscription_expires = None
        self.is_session_active = False

        # System tray icon setup
        self.tray_icon = QSystemTrayIcon(self)
        
        if os.path.exists(self.icon_path):
            self.icon_normal = QIcon(self.icon_path)
            self.icon_active = QIcon(self.icon_path) # Using the same icon for active state for now
        else:
            print(f"Warning: Tray icon image not found at {self.icon_path}. Using system default.")
            self.icon_normal = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
            self.icon_active = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon) # Fallback for active
        
        self.tray_icon.setIcon(self.icon_normal)
        self.tray_icon.setToolTip('Ergo')
        self.tray_menu = QMenu()

        self.action_open = QAction('Open Ergo Window', self)
        self.action_open.triggered.connect(self.show_and_raise)
        self.tray_menu.addAction(self.action_open)

        self.action_session = QAction('Start Session', self)
        self.action_session.triggered.connect(self.toggle_session_from_tray)
        self.tray_menu.addAction(self.action_session)

        self.action_settings = QAction('Settings', self)
        self.action_settings.triggered.connect(self.open_settings_from_tray)
        self.tray_menu.addAction(self.action_settings)

        self.action_quit = QAction('Quit Ergo', self)
        self.action_quit.triggered.connect(self.quit_app)
        self.tray_menu.addAction(self.action_quit)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()
        self._quit_from_tray = False

        # Wire dashboard buttons to logic in MainWindow
        # Remove .disconnect() calls as DashboardView buttons are not connected in its __init__
        self.dashboard_view.start_session_btn.clicked.connect(self.start_session_logic)
        self.dashboard_view.stop_session_btn.clicked.connect(self.stop_session_logic)

        # Connect to DashboardView's signal for when session fully starts
        self.dashboard_view.calibration_successful_and_session_started.connect(self._handle_session_fully_started)

    def _handle_session_fully_started(self):
        print("[DEBUG] MainWindow._handle_session_fully_started() called") # DEBUG
        self.is_session_active = True
        print(f"[DEBUG] MainWindow.is_session_active set to {self.is_session_active} by signal") # DEBUG
        self.update_tray_session_label()
        self.tray_icon.setIcon(self.icon_active)
        # Ensure MainWindow's view of button states is also consistent if it were to manage them
        # For now, DashboardView handles its own buttons primarily.

    def toggle_fullscreen(self, checked):
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()
        # Update the action's checked state if changed by other means (e.g., Esc key)
        self.fullscreen_action.setChecked(self.isFullScreen())

    def show_and_raise(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def toggle_session_from_tray(self):
        if self.is_session_active:
            self.stop_session_logic()
        else:
            self.start_session_logic()

    def open_settings_from_tray(self):
        if self.stacked_widget.currentWidget() == self.dashboard_scroll_area:
            self.dashboard_view.open_settings_dialog()
        else:
            self.show_and_raise()

    def quit_app(self):
        self._quit_from_tray = True
        QApplication.quit()

    def start_session_logic(self):
        if self.is_session_active:
            return
        # Show dashboard if not visible
        if self.stacked_widget.currentWidget() != self.dashboard_scroll_area:
            self.show_dashboard_view(self.current_user_email, self.current_subscription_status, self.current_subscription_expires)
        
        # Calibration step if needed (DashboardView handles its UI for this)
        if self.dashboard_view.reference_angles.get('head_forward') is None:
            self.dashboard_view.start_calibration() 
            # self.is_session_active will be set by the signal _handle_session_fully_started
        else:
            # Already calibrated, directly start monitoring (DashboardView handles its state)
            self.dashboard_view.session_active = True # Ensure dashboard knows
            print("[DEBUG] MainWindow.start_session_logic() - already calibrated, setting dashboard_view.session_active=True")
            # And now also ensure MainWindow knows by calling the handler
            self._handle_session_fully_started() 
            # Update DashboardView buttons since we bypassed its usual start_calibration flow
            self.dashboard_view.start_session_btn.setEnabled(False)
            self.dashboard_view.stop_session_btn.setEnabled(True)

    def stop_session_logic(self):
        print("[DEBUG] MainWindow.stop_session_logic() called") # DEBUG
        if not self.is_session_active:
            print("[DEBUG] MainWindow.stop_session_logic() returning early - session not active.") # DEBUG
            return
        self.dashboard_view.stop_session()
        self.is_session_active = False
        print(f"[DEBUG] MainWindow.is_session_active set to {self.is_session_active}") # DEBUG

        # UI updates in MainWindow for buttons - this seems to be missing for stop_session_btn, but present in DashboardView itself.
        self.update_tray_session_label()
        self.tray_icon.setIcon(self.icon_normal)

    def update_tray_session_label(self):
        if self.is_session_active:
            self.action_session.setText('Stop Session')
        else:
            self.action_session.setText('Start Session')

    def closeEvent(self, event):
        if self.is_session_active:
            event.ignore()
            self.hide()
            QMessageBox.information(self, 'Ergo', 'The app is still running in the system tray and monitoring your posture.')
        elif not self._quit_from_tray:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage('Ergo', 'The app is still running in the system tray.', QSystemTrayIcon.MessageIcon.Information, 2000)
        else:
            event.accept()

    def show_dashboard_view(self, email=None, status=None, expires_at=None):
        if email:
            self.current_user_email = email
        if status:
            self.current_subscription_status = status
        if expires_at:
            self.current_subscription_expires = expires_at
        self.dashboard_view.update_user_info(self.current_user_email, self.current_subscription_status, self.current_subscription_expires)
        self.stacked_widget.setCurrentWidget(self.dashboard_scroll_area)
        self.login_view.clear_fields()
        # If calibration just finished and session is active in dashboard, ensure MainWindow is also synced.
        # This check becomes less critical with the signal, but acts as a safeguard.
        if self.dashboard_view.session_active and not self.is_session_active:
            print("[DEBUG] MainWindow.show_dashboard_view() syncing is_session_active")
            self._handle_session_fully_started()

    def show_login_view(self):
        self.stacked_widget.setCurrentWidget(self.login_view)
        self.login_view.clear_fields()
        self.current_user_email = None
        self.current_subscription_status = None
        self.current_subscription_expires = None
        self.is_session_active = False
        self.update_tray_session_label()
        self.tray_icon.setIcon(self.icon_normal)

    def show_about_dialog(self):
        dlg = AboutDialog(self)
        dlg.exec()

    # It's good practice to update the menu item if fullscreen is exited by other means (e.g. Esc key)
    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
             if self.isFullScreen():
                 self.fullscreen_action.setChecked(True)
             else:
                 self.fullscreen_action.setChecked(False)

    def handle_new_instance_connection(self):
        global _main_local_server # Access the global server instance
        if _main_local_server:
            client_connection = _main_local_server.nextPendingConnection()
            if client_connection:
                # Wait for the message from the client (the new instance)
                if client_connection.waitForReadyRead(250): # 250ms timeout
                    message = client_connection.readAll().data().decode()
                    if message == "show_yourself":
                        self.show_and_raise() # Use existing method to show and activate
                client_connection.close()

def main():
    # Ensure the app scales reasonably on high-DPI displays
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # --- Single Instance Logic --- 
    global _main_local_server # So we can assign to it
    server_name = f"{ORGANIZATION_NAME}_{APPLICATION_NAME}_InstanceLock"

    socket = QLocalSocket()
    socket.connectToServer(server_name)

    if socket.waitForConnected(500): # Timeout 500ms
        # Connected to an existing instance. Send a message to raise its window.
        socket.write(b"show_yourself")
        socket.flush()
        socket.waitForBytesWritten(200)
        socket.close()
        # print("Another instance is already running. Exiting.") # Optional debug
        sys.exit(0) # This instance exits
    else:
        # Cannot connect, so this instance becomes the server.
        # Try to remove a stale server file if it exists (important on Unix-like systems)
        QLocalServer.removeServer(server_name)
        
        _main_local_server = QLocalServer()
        # WorldAccessOption allows other users on the same machine to trigger it too, 
        # UserAccessOption is usually sufficient and more secure if only same user.
        _main_local_server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption) 

        if not _main_local_server.listen(server_name):
            # If listen still fails, another instance might have started in a race condition
            # or there's a more persistent issue.
            if _main_local_server.serverError() == QLocalServer.ServerSocketError.AddressInUseError:
                 # Could attempt to connect again as client one last time before failing
                socket.connectToServer(server_name)
                if socket.waitForConnected(200):
                    socket.write(b"show_yourself")
                    socket.flush()
                    socket.waitForBytesWritten(200)
                    socket.close()
                    sys.exit(0)
                else:
                    QMessageBox.critical(None, "Application Startup Error",
                                     f"Failed to start. Another instance might be running or locked. Please try again or check task manager. Error: Address in use.")
                    sys.exit(1)
            else:
                QMessageBox.critical(None, "Application Startup Error",
                                     f"Could not start the local server: {_main_local_server.errorString()}")
                sys.exit(1)
    # --- End Single Instance Logic ---

    # Set Application Window Icon
    app_icon_path = resource_path(os.path.join('resources', 'icons', 'ergo-logo.png'))
    if os.path.exists(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))
    else:
        print(f"Warning: Application window icon not found at {app_icon_path}. System default will be used.")

    # Load the custom stylesheet
    load_stylesheet(app)

    # Initialize database
    init_db()

    window = MainWindow()
    
    # Connect the server's newConnection signal if it was created
    if _main_local_server:
        _main_local_server.newConnection.connect(window.handle_new_instance_connection)

    window.show()
    exit_code = app.exec()
    
    # Clean up server on exit
    if _main_local_server:
        _main_local_server.close()
        QLocalServer.removeServer(server_name) # Clean up the named socket/pipe if it exists

    sys.exit(exit_code)

if __name__ == '__main__':
    main() 