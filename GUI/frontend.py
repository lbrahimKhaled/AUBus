import os
import socket
import requests
import sys
import json
import random
import threading
import tempfile
import base64
import time
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox,
    QVBoxLayout, QHBoxLayout, QGridLayout, QStackedWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QMainWindow, QFrame, QRadioButton, QMessageBox, QSpinBox, QSplitter,
    QScrollArea, QTimeEdit
)
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QRectF, QPointF, QTime
from PyQt5.QtGui import QPainter, QColor, QPen, QPixmap
try:
    from PyQt5.QtMultimedia import (
        QAudioRecorder,
        QAudioEncoderSettings,
        QMultimedia,
        QMediaPlayer,
    QMediaContent,
    )
except ImportError:
    QAudioRecorder = None
    QAudioEncoderSettings = None
    QMultimedia = None
    QMediaPlayer = None
    QMediaContent = None
from backend.connections.client.client import * #connectToServer, sendCredentials, requestOther, receiveOther, changeMsg, 
from backend.DB.db import get_user_by_username, list_schedules_for_user

# ---------------------------- CONTROLLER ---------------------------- #
#for practical reasons and so that we don't let the pages block each other we will have a common controller to glue the GUI to the backend
class AUBusController:
    def __init__(self, conn: socket.socket):
        self.conn = conn
        self.p2pcon = None
        self.on_p2p_ready = None

    def set_p2p_socket(self, sock: socket.socket):
        """Store the active P2P socket and notify any listener."""
        try:
            if self.p2pcon and self.p2pcon is not sock:
                self.p2pcon.close()
        except Exception:
            pass
        self.p2pcon = sock
        if callable(self.on_p2p_ready):
            self.on_p2p_ready()

    def close_p2p(self):
        """Close and clear current P2P socket if any."""
        try:
            if self.p2pcon:
                self.p2pcon.close()
        except Exception:
            pass
        self.p2pcon = None

    def login(self, username, password, name, email, area, is_driver, login: int) -> bool:
        """
        login = 1  → send only username/password
        login = 0  → send full registration data
        """

        if login == 1:
            payload = {
                "login": 1,
                "username": username,
                "password": password,
            }
        else:
            payload = {
                "login": 0,
                "username": username,
                "password": password,
                "name": name,
                "email": email,
                "area": area,
                "is_driver": bool(is_driver),
            }

        try:
            return sendCredentials(self.conn, payload)
        except Exception as e:
            print("Failed to send credentials:", e)
            return False
    
    def changeMode(self):
        changeMsg(self.conn)
        # if switching away from driver mode, stop listener
        self.stop_driver_listener()

    def driverListener(self):
        # when a passenger connects, capture the socket so chat can use it
        start_driver_listener(lambda conn: self.set_p2p_socket(conn))

    def stop_driver_listener(self):
        try:
            stop_driver_listener()
        except Exception as e:
            print("Failed to stop driver listener:", e)

    def getOther(
        self,
        area_filter: str | None = None,
        target: str = "drivers",
        min_rating: float | None = None,
        depart_time: str | None = None,
    ):
        try:
            requestOther(
                self.conn,
                area_filter=area_filter,
                target=target,
                min_rating=min_rating,
                depart_time=depart_time,
            )
            drivers: list[dict] = receiveOther(self.conn)
            return drivers if isinstance(drivers, list) else []
        except Exception as e:
            print("Error while fetching drivers:", e)
            return []
    
    def get_weather(self, location: str)->str:
        """
        Fetch weather with a short timeout so the UI never freezes.
        Falls back quietly if network is blocked/unavailable.
        """
        target_loc = location or "Beirut"
        try:
            api_key = "34b53f4628054c4bbf2154149251611"
            url = f"https://api.weatherapi.com/v1/current.json?key={api_key}&q={target_loc}&aqi=no"
            response = requests.get(url, timeout=1.5)
            response.raise_for_status()
            data = response.json()
            temp = float(data["current"]["temp_c"])
            description = data["current"]["condition"]["text"].capitalize()
            return f"🌤️ {temp:.1f}°C, {description} in {target_loc}"
        except Exception:
            return f"🌤️ Weather unavailable in {target_loc}"

    def rate_partner(self, target_username: str, stars: int, comment: str = "") -> bool:
        try:
            return send_rating(self.conn, target_username, stars, comment)
        except Exception as e:
            print("Failed to send rating:", e)
            return False

    def refresh_user_from_db(self, username: str, current_data: dict) -> dict | None:
        """
        Pull the latest user row from the DB and update user_data.
        """
        user = get_user_by_username(username)
        if not user:
            return None
        data = user.to_dict()
        # align keys used through UI
        data["rating"] = int(data.get("rating_avg", 0))
        current_data.update(data)
        return data

    def sendSchedule(self, weekday: int, depart_time: str, direction: str) -> bool:
        try:
            return send_schedule_to_server(self.conn, weekday, str(depart_time), direction)
        except Exception as e:
            print("Failed to send schedule:", e)
            return False

    def update_location(self, latitude: float | None, longitude: float | None, city: str | None, country: str | None, area: str | None) -> bool:
        try:
            return update_location_on_server(self.conn, latitude, longitude, city, country, area)
        except Exception as e:
            print("Failed to update location:", e)
            return False

    def get_user_schedule(self, user_id: int) -> list[dict]:
        try:
            return list_schedules_for_user(user_id) or []
        except Exception as e:
            print("Failed to fetch schedule:", e)
            return []

    def send_emergency_report(self, payload: dict) -> bool:
        try:
            return send_emergency(self.conn, payload)
        except Exception as e:
            print("Failed to send emergency report:", e)
            return False



# ---------------------------- AUTH PAGE ---------------------------- #
class AuthPage(QWidget):
    """Unified Login & Register Page"""
    def __init__(self, parent, controller: AUBusController):
        super().__init__()
        self.parent = parent
        self.controller = controller
        layout = QVBoxLayout()

        title = QLabel("<h1 style='color:#781414;'>AUBus</h1>")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Login or Register below")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color:#555; font-size:15px;")

        self.name = QLineEdit()
        self.name.setPlaceholderText("Full Name (Register only)")
        self.email = QLineEdit()
        self.email.setPlaceholderText("Email (Register only)")
        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("Password")
        self.area = QComboBox()
        self.area.addItems(["Select Area", "Hamra", "Achrafieh", "Verdun", "Jnah", "Other"])

        self.mode = "login"
        self.toggle_btn = QPushButton("Switch to Register")
        self.toggle_btn.clicked.connect(self.toggle_mode)
        self.submit_btn = QPushButton("Login")
        self.submit_btn.clicked.connect(self.submit_action)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        layout.addWidget(self.name)
        layout.addWidget(self.email)
        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addWidget(self.area)
        layout.addSpacing(10)
        layout.addWidget(self.submit_btn)
        layout.addWidget(self.toggle_btn)
        layout.addStretch()
        layout.setContentsMargins(300, 50, 300, 50)
        self.setLayout(layout)
        self.update_fields()

    def toggle_mode(self):
        self.mode = "register" if self.mode == "login" else "login"
        self.update_fields()

    def update_fields(self):
        reg = self.mode == "register"
        self.name.setVisible(reg)
        self.email.setVisible(reg)
        self.area.setVisible(reg)
        self.submit_btn.setText("Register" if reg else "Login")
        self.toggle_btn.setText("Switch to Login" if reg else "Switch to Register")

    def submit_action(self):
        auth: bool 
        if self.mode == "register":
            if not self.username.text() or not self.password.text():
                QMessageBox.warning(self, "Missing Info", "Please fill in required fields.")
                return
            self.parent.user_data = {
                "name": self.name.text(),
                "email": self.email.text(),
                "username": self.username.text(),
                "password": self.password.text(),
                "area": self.area.currentText(),
                "rating": 0,
                "role": "passenger"
            }  

            data = self.parent.user_data
            username   = data["username"]
            password   = data["password"]
            name       = data["name"]
            email      = data["email"]
            area       = data["area"]
            is_driver  = False  # or however you store it

            auth = self.controller.login(
                username,
                password,
                name,
                email,
                area,
                is_driver,
                login=0
            )

        else:
            if not self.username.text() or not self.password.text():
                QMessageBox.warning(self, "Missing Info", "Please enter your credentials")
                return
            self.parent.user_data = {
                "name": self.username.text(),
                "email": "student@aub.edu.lb",
                "username": self.username.text(),
                "password": self.password.text(),
                "area": "Hamra",
                "rating": 0,
                "role": "passenger"
            }
            data = self.parent.user_data
            username   = data["username"]
            password   = data["password"]
            name       = data["name"]
            email      = data["email"]
            area       = data["area"]
            is_driver  = False  # or however you store it

            auth = self.controller.login(
                username,
                password,
                name,
                email,
                area,
                is_driver,
                login=1
            )
        self.parent.weather_label.setText(self.controller.get_weather(self.parent.user_data.get('area','') if self.parent.user_data.get("area") in self.parent.user_data else "Beirut"))
        
        #sending username and password to the backend
        if(not auth):
            QMessageBox.warning(self, "Authentication Failed", "Invalid credentials or registration error.")
            self.parent.goto_page("auth")

        self.parent.user_data["authenticated"] = auth
        self.parent.goto_page("profile")


# ---------------------------- PROFILE PAGE ---------------------------- #
class ProfilePage(QWidget):
    def __init__(self, parent, controller: AUBusController):
        super().__init__()
        self.parent = parent
        self.controller = controller
        layout = QVBoxLayout()
        title = QLabel("<h1 style='color:#781414;'>Profile</h1>")
        title.setAlignment(Qt.AlignCenter)
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("font-size:15px; color:#222;")
        self.rating_label = QLabel()
        self.rating_label.setAlignment(Qt.AlignCenter)

        self.driver_radio = QRadioButton("Driver")
        self.passenger_radio = QRadioButton("Passenger")
        go_btn = QPushButton("Continue")
        self.parent.user_data["role"] = "passenger"
        go_btn.clicked.connect(self.set_role)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(self.info_label)
        layout.addWidget(self.rating_label)
        layout.addSpacing(20)
        layout.addWidget(QLabel("Select your role:"), alignment=Qt.AlignCenter)
        layout.addWidget(self.driver_radio, alignment=Qt.AlignCenter)
        layout.addWidget(self.passenger_radio, alignment=Qt.AlignCenter)
        layout.addWidget(go_btn, alignment=Qt.AlignCenter)
        layout.addStretch()
        self.setLayout(layout)

    def refresh_info(self):
        data = self.parent.user_data
        if not data:
            return
        if data.get("username"):
            self.controller.refresh_user_from_db(data["username"], self.parent.user_data)
            data = self.parent.user_data
        info = f"""
        <b>Name:</b> {data.get('name','')}<br>
        <b>Username:</b> {data.get('username','')}<br>
        <b>Email:</b> {data.get('email','')}<br>
        <b>Area:</b> {data.get('area','')}
        """
        stars = "⭐" * int(data.get("rating", 0))
        self.info_label.setText(info)
        self.rating_label.setText(f"<b>Your Rating:</b> {stars if stars else 'Not rated yet'} (avg: {data.get('rating_avg',0):.1f} from {data.get('rating_count',0)} ratings)")

    def set_role(self):
        if self.driver_radio.isChecked():
            if(self.parent.user_data["role"] != "driver"): 
                self.controller.changeMode()
                self.controller.driverListener()

            self.parent.user_data["role"] = "driver"
            self.parent.goto_page("schedule")
        elif self.passenger_radio.isChecked():
            if(self.parent.user_data["role"] != "passenger"):
                self.controller.changeMode()
                self.controller.stop_driver_listener()
            self.parent.user_data["role"] = "passenger"
            self.parent.goto_page("dashboard")
        else:
            QMessageBox.warning(self, "Selection Required", "Please select Driver or Passenger.")
# ---------------------------- SCHEDULE PAGE ---------------------------- #
class SchedulePage(QWidget):
    def __init__(self, parent, controller: AUBusController):
        super().__init__()
        self.parent = parent
        self.controller = controller
        self.day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        layout = QVBoxLayout()
        title = QLabel("<h1 style='color:#781414;'>Your Schedule</h1>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.day_select = QComboBox()
        self.day_select.addItems(self.day_names)

        self.home_depart = QSpinBox()
        self.home_depart.setRange(0, 23)
        self.home_depart.setPrefix("From Home (hr): ")

        self.aub_depart = QSpinBox()
        self.aub_depart.setRange(0, 23)
        self.aub_depart.setPrefix("From AUB (hr): ")

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Day", "Dep. Home", "Dep. AUB"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        add_btn = QPushButton("Add Day")
        add_btn.clicked.connect(self.add_schedule)

        layout.addWidget(QLabel("Select Day:"))
        layout.addWidget(self.day_select)
        layout.addWidget(self.home_depart)
        layout.addWidget(self.aub_depart)
        layout.addWidget(add_btn)
        layout.addWidget(self.table)
        layout.addStretch()
        self.setLayout(layout)

    def _get_user_id(self) -> int | None:
        user_id = self.parent.user_data.get("id")
        if user_id:
            return user_id
        username = self.parent.user_data.get("username")
        if username:
            self.controller.refresh_user_from_db(username, self.parent.user_data)
            return self.parent.user_data.get("id")
        return None

    def load_schedule(self):
        """Load schedule rows from the DB for the signed-in user."""
        self.table.setRowCount(0)
        user_id = self._get_user_id()
        if not user_id:
            return

        schedules = self.controller.get_user_schedule(user_id)
        grouped: dict[int, dict[str, list[str]]] = {}
        for entry in schedules:
            weekday = entry.get("weekday")
            direction = entry.get("direction")
            if weekday is None or direction not in ("toAUB", "fromAUB"):
                continue
            if not isinstance(weekday, int):
                try:
                    weekday = int(weekday)
                except (ValueError, TypeError):
                    continue
            if not 0 <= weekday < len(self.day_names):
                continue
            grouped.setdefault(weekday, {"toAUB": [], "fromAUB": []})
            grouped[weekday][direction].append(str(entry.get("depart_time", "")))

        for weekday in range(len(self.day_names)):
            day_data = grouped.get(weekday)
            if not day_data:
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(self.day_names[weekday]))
            home_times = ", ".join(day_data["toAUB"]) if day_data["toAUB"] else "-"
            aub_times = ", ".join(day_data["fromAUB"]) if day_data["fromAUB"] else "-"
            self.table.setItem(row, 1, QTableWidgetItem(home_times))
            self.table.setItem(row, 2, QTableWidgetItem(aub_times))

    def add_schedule(self):
        dep_home = self.home_depart.value()
        dep_aub = self.aub_depart.value()
        dep_home_str = f"{dep_home:02d}:00"
        dep_aub_str = f"{dep_aub:02d}:00"

        success_home = self.controller.sendSchedule(self.day_select.currentIndex(), dep_home_str, "toAUB")
        success_aub = self.controller.sendSchedule(self.day_select.currentIndex(), dep_aub_str, "fromAUB")

        if not (success_home and success_aub):
            QMessageBox.warning(self, "Save Failed", "Could not save one or more schedule entries.")
        self.load_schedule()


# ---------------------------- DASHBOARD PAGE ---------------------------- #
class LebanonMapWidget(QWidget):
    """
    Static Lebanon map with a highlighted user location and driver locations.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_location = None  # (lat, lon, label)
        self.driver_locations: list[tuple[float, float, str]] = []
        self.setMinimumHeight(260)
        self.pixmap_path = os.path.join(os.path.dirname(__file__), "assets", "lebanon_map.png")
        self.pixmap = QPixmap(self.pixmap_path) if os.path.exists(self.pixmap_path) else QPixmap()

    def set_user_location(self, latitude: float | None, longitude: float | None, label: str = ""):
        if latitude is None or longitude is None:
            self.user_location = None
        else:
            self.user_location = (float(latitude), float(longitude), label)
        if self.pixmap.isNull() and os.path.exists(self.pixmap_path):
            self.pixmap = QPixmap(self.pixmap_path)
        self.update()

    def set_driver_locations(self, locations: list[tuple[float, float, str]]):
        """locations is a list of (lat, lon, label)"""
        cleaned: list[tuple[float, float, str]] = []
        for loc in locations:
            try:
                lat, lon, label = loc
                cleaned.append((float(lat), float(lon), label))
            except Exception:
                continue
        self.driver_locations = cleaned
        if self.pixmap.isNull() and os.path.exists(self.pixmap_path):
            self.pixmap = QPixmap(self.pixmap_path)
        self.update()

    def _latlon_to_point(self, lat: float, lon: float, rect: QRectF) -> QPointF:
        # rough bounding box for Lebanon
        min_lat, max_lat = 33.0, 34.7
        min_lon, max_lon = 35.0, 36.7
        lat = max(min_lat, min(max_lat, lat))
        lon = max(min_lon, min(max_lon, lon))
        x_ratio = (lon - min_lon) / (max_lon - min_lon)
        y_ratio = (lat - min_lat) / (max_lat - min_lat)
        x = rect.left() + x_ratio * rect.width()
        y = rect.bottom() - y_ratio * rect.height()
        return QPointF(x, y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()
        height = self.height()
        margin = 20
        map_rect = QRectF(margin, margin, width - 2 * margin, height - 2 * margin)

        # background image or fallback
        if not self.pixmap.isNull():
            scaled = self.pixmap.scaled(map_rect.size().toSize(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            # center the scaled pixmap inside map_rect
            x_offset = map_rect.left() + (map_rect.width() - scaled.width()) / 2
            y_offset = map_rect.top() + (map_rect.height() - scaled.height()) / 2
            painter.drawPixmap(int(x_offset), int(y_offset), scaled)
            # update map_rect to the actual drawn pixmap area for coordinate mapping
            map_rect = QRectF(x_offset, y_offset, scaled.width(), scaled.height())
        else:
            painter.fillRect(self.rect(), QColor("#f7f8fa"))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#e5e7eb"))
            painter.drawRoundedRect(map_rect, 18, 18)
            painter.setPen(QPen(QColor(200, 200, 200, 110), 1))
            for i in range(6):
                offset = (i + 1) * 8
                painter.drawArc(map_rect.adjusted(offset, offset, -offset, -offset), 30 * 16, 220 * 16)
            painter.setPen(QPen(QColor("#7f1d1d")))
            painter.drawText(map_rect, Qt.AlignCenter, "Place lebanon_map.png in GUI/assets")

        # driver dots (draw first, so user appears on top)
        painter.setPen(QPen(QColor("#d35400"), 1.2))
        painter.setBrush(QColor("#f39c12"))
        for lat, lon, label in self.driver_locations:
            pt = self._latlon_to_point(lat, lon, map_rect)
            painter.drawEllipse(pt, 6, 6)
            painter.setPen(QPen(QColor("#7f8c8d")))
            painter.drawText(pt + QPointF(8, -4), label or "Driver")
            painter.setPen(QPen(QColor("#d35400"), 1.2))
            painter.setBrush(QColor("#f39c12"))

        # user dot
        if self.user_location:
            lat, lon, label = self.user_location
            pt = self._latlon_to_point(lat, lon, map_rect)
            painter.setPen(QPen(QColor("#a93226"), 1.6))
            painter.setBrush(QColor("#c0392b"))
            painter.drawEllipse(pt, 8, 8)
            painter.setPen(QPen(QColor("#1f2933")))
            painter.drawText(pt + QPointF(10, -6), label or "You")


class DashboardPage(QWidget):
    def __init__(self, parent, controller: AUBusController):
        super().__init__()
        self.controller = controller
        self.parent = parent
        self.driver_markers: list[tuple[float, float, str]] = []
        layout = QVBoxLayout()
        title = QLabel("<h1 style='color:#781414;'>Dashboard</h1>")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Request a ride and view available drivers")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color:#555; font-size:14px;")

        self.area_box = QComboBox()
        self.area_box.addItems(["Select Area", "Hamra", "Achrafieh", "Verdun", "Jnah", "Other"])

        self.depart_time_edit = QTimeEdit()
        self.depart_time_edit.setDisplayFormat("HH:mm")
        self.depart_time_edit.setTime(QTime.currentTime())
        self.depart_time_edit.setToolTip("Preferred departure time from your location")

        self.rating_filter = QSpinBox()
        self.rating_filter.setRange(0, 5)
        self.rating_filter.setPrefix("Min Rating: ")
        self.rating_filter.setSuffix(" ★")
        self.rating_filter.setValue(0)
        self.rating_filter.setToolTip("Only show drivers with this rating or above (0 to disable)")

        req_btn = QPushButton("Send Ride Request")
        req_btn.clicked.connect(self.show_drivers)

        self.location_btn = QPushButton("Refresh Location")
        self.location_btn.clicked.connect(self.refresh_location)
        self.location_label = QLabel("Location: Unknown")
        self.location_label.setStyleSheet("color:#333;")
        self.map_widget = LebanonMapWidget()

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Driver Name", "Username", "Email", "Area", "IP", "Rating"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.cellDoubleClicked.connect(self.open_chat)
        self.table.setVisible(False)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(15)
        layout.addWidget(self.area_box)
        layout.addWidget(self.depart_time_edit)
        layout.addWidget(self.rating_filter)
        layout.addWidget(req_btn)
        layout.addWidget(self.location_btn)
        layout.addWidget(self.location_label)
        layout.addWidget(self.map_widget)
        layout.addSpacing(20)
        layout.addWidget(self.table)
        layout.addStretch()
        self.setLayout(layout)

    def show_drivers(self):
        try:
            selection = self.area_box.currentText()
            # Determine which area filter to use based on selection
            if selection == "Select Area":
                area_filter = self.parent.user_data.get("area")
            elif selection == "Other":
                area_filter = "all"  # show every online driver
            else:
                area_filter = selection

            min_rating = self.rating_filter.value()
            min_rating = min_rating if min_rating > 0 else None
            depart_time = self.depart_time_edit.time().toString("HH:mm")

            drivers : list[dict] = self.controller.getOther(
                area_filter,
                min_rating=min_rating,
                depart_time=depart_time,
            ) or []
            if not isinstance(drivers, list):
                drivers = []
            markers: list[tuple[float, float, str]] = []
            self.table.setRowCount(0)
            for driver in drivers:
                if not isinstance(driver, dict):
                    continue
                if not driver.get("is_driver", True):
                    continue
                row_idx = self.table.rowCount()
                self.table.insertRow(row_idx)
                name = str(driver.get("name", "N/A"))
                username = str(driver.get("username", "N/A"))
                email = str(driver.get("email", "N/A"))
                area = str(driver.get("area", driver.get("location", "N/A")))
                ip = str(driver.get("ip", ""))
                rating = self._format_rating(driver.get("rating_avg", driver.get("rating", "N/A")))
                for j, val in enumerate([name, username, email, area, ip, rating]):
                    self.table.setItem(row_idx, j, QTableWidgetItem(val))
                lat = driver.get("latitude")
                lon = driver.get("longitude")
                label = area or name
                if lat is None or lon is None:
                    coords = self._coords_for_area(area)
                    if coords:
                        lat, lon = coords
                if lat is not None and lon is not None:
                    markers.append((float(lat), float(lon), label))
            self.table.setVisible(True)
            self.driver_markers = markers
            self.map_widget.set_driver_locations(markers)
        except Exception as e:
            print("Error showing drivers:", e)
            QMessageBox.warning(self, "Error", "Could not load drivers. Please try again.")

    def refresh_location(self):
        """Fetch public IP, geolocate, update DB, and refresh map."""
        self.location_label.setText("Fetching location...")
        QApplication.processEvents()
        try:
            api_key = "221f518db3f84c76a57801bdf9ef8c6e"
            res = requests.get(f"https://api.ipgeolocation.io/ipgeo?apiKey={api_key}", timeout=8)
            data = res.json()
            if not data or "latitude" not in data or "longitude" not in data:
                raise RuntimeError("Geo lookup failed")
            lat = float(data.get("latitude"))
            lon = float(data.get("longitude"))
            city = data.get("city") or data.get("state_prov") or ""
            country = data.get("country_name") or data.get("country_code2") or ""
            area = city or data.get("state_prov") or self.parent.user_data.get("area")
            print(f"Location fetched: {lat}, {lon} - {city}, {country}, {area}")

            # Persist to server and local cache
            success = self.controller.update_location(lat, lon, city, country, area)
            self.parent.user_data["latitude"] = lat
            self.parent.user_data["longitude"] = lon
            self.parent.user_data["city"] = city
            self.parent.user_data["country"] = country
            if area:
                self.parent.user_data["area"] = area

            pretty_coords = f"({float(lat):.2f}, {float(lon):.2f})" if lat is not None and lon is not None else ""
            self.location_label.setText(f"Location: {city}, {country} {pretty_coords}".strip())
            self.map_widget.set_user_location(lat, lon, city)
            # refresh driver markers on the map with the latest view
            self.map_widget.set_driver_locations(self.driver_markers)

            if not success:
                QMessageBox.warning(self, "Warning", "Could not sync location to server.")
        except Exception as e:
            print("Error refreshing location:", e)
            self.location_label.setText("Location: unavailable")
            QMessageBox.warning(self, "Error", "Could not determine your location. Please try again.")

    def _coords_for_area(self, area: str | None):
        """Rudimentary area → lat/lon mapping for markers."""
        if not area:
            return None
        area = area.lower()
        presets = {
            "hamra": (33.895, 35.480),
            "achrafieh": (33.886, 35.515),
            "verdun": (33.886, 35.488),
            "jnah": (33.855, 35.491),
            "beirut": (33.8938, 35.5018),
            "zahle": (33.8469, 35.9020),
            "tripoli": (34.4331, 35.8442),
            "saida": (33.5649, 35.3689),
            "tyre": (33.2700, 35.1939),
        }
        # find first matching preset
        for key, coords in presets.items():
            if key in area:
                return coords
        return None

    def _format_rating(self, value) -> str:
        """Return rating with max 2 decimals."""
        try:
            num = float(value)
            return f"{num:.2f}"
        except Exception:
            return str(value if value is not None else "N/A")


    def open_chat(self, row, _):
        selected_driver = self.table.item(row, 0)
        if selected_driver.text() == self.parent.user_data.get("username"):
            QMessageBox.warning(self, "Invalid Action", "You cannot chat with yourself.")
            return

        self.parent.chat_partner = {
            "name": selected_driver.text(),
            "username": self.table.item(row, 1).text(),
            "email": self.table.item(row, 2).text(),
            "area": self.table.item(row, 3).text(),
            "ip": self.table.item(row, 4).text(),
            "rating": self.table.item(row, 5).text()
        }
        self.parent.chat_started = True

        # Notify user that we're waiting for driver acceptance
        QMessageBox.information(self, "Waiting", "Waiting for driver to accept chat...")

        # Wait for server response (driver OK)
        # ensure stale P2P is closed before establishing new one
        self.controller.close_p2p()
        P2Pcon = waitForChatApproval(self.controller.conn)
        if not P2Pcon:
            QMessageBox.warning(self, "Chat Failed", "No response from driver or server.")
            return
        self.controller.set_p2p_socket(P2Pcon)
        self.parent.goto_page("chat")


# ---------------------------- CHAT PAGE ---------------------------- #
class ChatPage(QWidget):
    """Chat page adapts based on role (Driver gets split view, Passenger sees only chat)"""
    incoming_payload = pyqtSignal(dict)

    def __init__(self, parent, controller:AUBusController):
        super().__init__()
        self.parent = parent
        self.controller = controller
        self.receiver_started = False
        self.recv_buffer = b""
        self.audio_recorder = QAudioRecorder() if QAudioRecorder else None
        self.media_player = QMediaPlayer() if QMediaPlayer else None
        self.current_record_path = ""
        self.last_recorded_path = ""
        self.is_recording = False
        self.active_p2p_socket = None
        self.incoming_payload.connect(self.handle_incoming_payload)
        # Left panel: Chat
        self.header = QLabel("No active chat")
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setStyleSheet("background-color:#781414; color:white; padding:12px; border-radius:8px;")

        self.chat_box = QTextEdit()
        self.chat_box.setReadOnly(True)

        # Voice notes area
        self.voice_layout = QVBoxLayout()
        self.voice_layout.setSpacing(6)
        voice_widget = QWidget()
        voice_widget.setLayout(self.voice_layout)
        voice_scroll = QScrollArea()
        voice_scroll.setWidgetResizable(True)
        voice_scroll.setWidget(voice_widget)
        voice_label = QLabel("Voice notes")
        voice_label.setAlignment(Qt.AlignLeft)
        voice_label.setStyleSheet("font-weight:bold; color:#444; margin-top:6px;")

        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Type message...")
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_message)

        # Voice controls
        self.record_btn = QPushButton("Record Voice")
        self.record_btn.clicked.connect(self.toggle_recording)
        self.send_voice_btn = QPushButton("Send Voice Note")
        self.send_voice_btn.clicked.connect(self.send_voice_note)
        self.send_voice_btn.setEnabled(False)
        self.record_status = QLabel("Ready to record")
        self.record_status.setStyleSheet("color:#555; font-size:12px;")
        if not self.audio_recorder:
            self.record_btn.setEnabled(False)
            self.send_voice_btn.setEnabled(False)
            self.record_status.setText("Audio recording not available on this device.")

        msg_layout = QHBoxLayout()
        msg_layout.addWidget(self.msg_input)
        msg_layout.addWidget(send_btn)

        voice_controls = QHBoxLayout()
        voice_controls.addWidget(self.record_btn)
        voice_controls.addWidget(self.send_voice_btn)
        voice_controls.addStretch()

        self.rate_btn = QPushButton("Rate")
        self.rate_btn.clicked.connect(self.open_rating)

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.header)
        left_layout.addWidget(self.chat_box)
        left_layout.addWidget(voice_label)
        left_layout.addWidget(voice_scroll)
        left_layout.addLayout(msg_layout)
        left_layout.addLayout(voice_controls)
        left_layout.addWidget(self.record_status)
        left_layout.addWidget(self.rate_btn, alignment=Qt.AlignRight)

        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        # Right panel (only for drivers): Passenger list
        self.passenger_table = QTableWidget(0, 6)
        self.passenger_table.setHorizontalHeaderLabels(["Passenger", "Username", "Email", "Area", "IP", "Rating"])
        self.passenger_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.passenger_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.passenger_table.cellDoubleClicked.connect(self.select_passenger)

        right_widget = self.create_right_panel()

        # Split layout (driver sees both halves)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(right_widget)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)

    def populate_passenger_table(self):
        """Temporary mock data — replace later with controller call"""
        self.passengers = []
        self.passengers = self.controller.getOther(target="passengers") or []
        if not isinstance(self.passengers, list):
            self.passengers = []

        # Clear and refill table
        self.passenger_table.setRowCount(len(self.passengers))
        for i, driver in enumerate(self.passengers):
            if not isinstance(driver, dict):
                continue
            name = str(driver.get("name", "N/A"))
            username = str(driver.get("username", "N/A"))
            email = str(driver.get("email", "N/A"))
            area = str(driver.get("area", driver.get("location", "N/A")))
            ip = str(driver.get("ip", ""))
            rating = self._fmt_rating(driver.get("rating_avg", driver.get("rating", "N/A")))

            for j, val in enumerate([name, username, email, area, ip, rating]):
                self.passenger_table.setItem(i, j, QTableWidgetItem(val))

    def create_right_panel(self):
        """Creates the right panel with the passenger table and refresh button"""
        right_layout = QVBoxLayout()

        title = QLabel("<h3 style='color:#781414;'>Ride Requests</h3>")
        title.setAlignment(Qt.AlignCenter)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #781414;
                color: white;
                border-radius: 5px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #a21d1d;
            }
        """)
        refresh_btn.clicked.connect(self.populate_passenger_table)

        right_layout.addWidget(title)
        right_layout.addWidget(refresh_btn, alignment=Qt.AlignCenter)
        right_layout.addWidget(self.passenger_table)

        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        return right_widget

    

    def select_passenger(self, row, _):
        """Driver double-clicks passenger to open chat"""
        # Ensure list is valid
        if not hasattr(self, "passengers") or row >= len(self.passengers):
            QMessageBox.warning(self, "Error", "No passenger data found.")
            return

        passenger = self.passengers[row]

        # Prevent chatting with yourself
        if passenger.get("name") == self.parent.user_data.get("username"):
            QMessageBox.warning(self, "Invalid", "You cannot chat with yourself.")
            return
        # Close any previous P2P before starting a new chat
        self.controller.close_p2p()

        # Mark chat state
        self.parent.chat_partner = passenger
        self.parent.chat_started = True

        # Update chat header and clear previous chat
        self.chat_box.clear()
        rating_val = self._fmt_rating(passenger.get("rating") or passenger.get("rating_avg") or "N/A")
        self.header.setText(
            f"Chatting with: <b>{passenger.get('name')}</b> | "
            f"Area: {passenger.get('location', passenger.get('area','N/A'))} | "
            f"Rating: {rating_val}"
        )

        sendChatOK(self.controller.conn, passenger["username"])

        # Provide initial system message
        self.chat_box.append(f"🟢 Connected to {passenger.get('name')}.\nYou can start messaging now.")
        # Ensure background receiver starts once P2P socket is available
        if self.controller.p2pcon:
            self.start_receiver()

    def refresh_chat_header(self):
        role = self.parent.user_data.get("role")
        partner = self.parent.chat_partner
        if not partner:
            self.header.setText("No active chat")
        else:
            area = partner.get("area", partner.get("location", "N/A"))
            rating = self._fmt_rating(partner.get("rating") or partner.get("rating_avg") or "N/A")
            name = partner.get("name", "Unknown")
            self.header.setText(
                f"Chatting with: <b>{name}</b> | Area: {area} | Rating: {rating}"
            )

        # Hide right side for passengers
        role = self.parent.user_data.get("role")
        is_driver = (role == "driver")
        self.splitter.widget(1).setVisible(is_driver)

        # register callback so when P2P socket becomes ready we start listening
        self.controller.on_p2p_ready = self.start_receiver
        # ✅ Start background receiver once P2P socket is active
        if self.controller.p2pcon:
            self.start_receiver()

    def send_message(self):
        msg = self.msg_input.text().strip()
        if not msg:
            return

        self.chat_box.append(f"You: {msg}")
        self.msg_input.clear()
        payload = {"type": "text", "message": msg}
        if not self.send_payload(payload):
            QMessageBox.warning(self, "No Connection", "P2P connection not established yet.")

    def send_payload(self, payload: dict) -> bool:
        # Send through P2P socket as newline-delimited JSON
        try:
            if self.controller.p2pcon:
                data = (json.dumps(payload) + "\n").encode("utf-8")
                self.controller.p2pcon.sendall(data)
                return True
            return False
        except Exception as e:
            QMessageBox.warning(self, "Send Failed", f"Error: {e}")
            return False

    def toggle_recording(self):
        if not self.audio_recorder:
            QMessageBox.warning(self, "Unavailable", "Audio recording is not available.")
            return
        if not self.is_recording:
            # start recording
            try:
                fd, path = tempfile.mkstemp(prefix="aubus_voice_", suffix=".wav")
                os.close(fd)
                self.current_record_path = path
                settings = QAudioEncoderSettings()
                settings.setCodec("audio/pcm")
                settings.setSampleRate(44100)
                settings.setChannelCount(1)
                settings.setBitRate(128000)
                if QMultimedia:
                    settings.setQuality(QMultimedia.HighQuality)
                self.audio_recorder.setAudioSettings(settings)
                self.audio_recorder.setOutputLocation(QUrl.fromLocalFile(path))
                self.audio_recorder.record()
                self.is_recording = True
                self.record_btn.setText("Stop Recording")
                self.record_status.setText("Recording... speak now")
                self.send_voice_btn.setEnabled(False)
            except Exception as e:
                QMessageBox.warning(self, "Record Failed", f"Could not start recording: {e}")
        else:
            try:
                self.audio_recorder.stop()
                self.is_recording = False
                self.record_btn.setText("Record Voice")
                self.last_recorded_path = self.current_record_path
                if self.last_recorded_path and os.path.exists(self.last_recorded_path):
                    self.record_status.setText(f"Recorded: {os.path.basename(self.last_recorded_path)}")
                    self.send_voice_btn.setEnabled(True)
                else:
                    self.record_status.setText("No recording captured")
                    self.send_voice_btn.setEnabled(False)
            except Exception as e:
                QMessageBox.warning(self, "Record Failed", f"Could not stop recording: {e}")

    def send_voice_note(self):
        if not self.last_recorded_path or not os.path.exists(self.last_recorded_path):
            QMessageBox.warning(self, "No Recording", "Record a voice note first.")
            return
        try:
            with open(self.last_recorded_path, "rb") as f:
                audio_bytes = f.read()
            payload = {
                "type": "voice",
                "filename": os.path.basename(self.last_recorded_path),
                "data": base64.b64encode(audio_bytes).decode("ascii"),
            }
            if self.send_payload(payload):
                self.chat_box.append("You sent a voice note.")
                self.add_voice_note_ui("You", self.last_recorded_path)
                self.send_voice_btn.setEnabled(False)
            else:
                QMessageBox.warning(self, "No Connection", "P2P connection not established yet.")
        except Exception as e:
            QMessageBox.warning(self, "Send Failed", f"Could not send voice note: {e}")
    def start_receiver(self):
        """
        Starts a background thread that continuously listens for incoming chat messages.
        """
        if not self.controller.p2pcon:
            return
        # allow restart if socket changed
        if self.receiver_started and self.active_p2p_socket is self.controller.p2pcon:
            return
        if self.receiver_started and self.active_p2p_socket is not self.controller.p2pcon:
            self.receiver_started = False
        self.receiver_started = True
        self.active_p2p_socket = self.controller.p2pcon

        def listen_for_messages():
            while True:
                try:
                    data = self.controller.p2pcon.recv(4096)
                    if not data:
                        break
                    self.recv_buffer += data
                    while b"\n" in self.recv_buffer:
                        raw, self.recv_buffer = self.recv_buffer.split(b"\n", 1)
                        if not raw:
                            continue
                        try:
                            payload = json.loads(raw.decode("utf-8"))
                            self.incoming_payload.emit(payload)
                        except Exception:
                            try:
                                msg = raw.decode("utf-8", errors="ignore")
                                self.incoming_payload.emit({"type": "plain", "message": msg})
                            except Exception:
                                pass
                            continue
                except Exception as e:
                    print("Receiver stopped:", e)
                    break

            self.controller.close_p2p()
            self.receiver_started = False
            self.active_p2p_socket = None

        threading.Thread(target=listen_for_messages, daemon=True).start()

    def open_rating(self):
        if not self.parent.chat_started or not self.parent.chat_partner:
            QMessageBox.warning(self, "No Chat", "You must chat with someone before rating.")
            return
        self.parent.goto_page("rating")

    def handle_incoming_payload(self, payload: dict):
        msg_type = payload.get("type")
        if msg_type == "text":
            self.chat_box.append(f"Peer: {payload.get('message','')}")
        elif msg_type == "voice":
            b64 = payload.get("data")
            filename = payload.get("filename", "voice_note.wav")
            try:
                audio_bytes = base64.b64decode(b64) if b64 else b""
                save_path = os.path.join(tempfile.gettempdir(), f"peer_{int(time.time())}_{filename}")
                with open(save_path, "wb") as f:
                    f.write(audio_bytes)
                self.chat_box.append("Peer sent a voice note.")
                self.add_voice_note_ui("Peer", save_path)
            except Exception as e:
                self.chat_box.append(f"Failed to process incoming voice note: {e}")
        elif msg_type == "plain":
            self.chat_box.append(f"Peer: {payload.get('message','')}")
        else:
            # fallback if peer sends plain message structure
            self.chat_box.append(f"Peer: {payload}")

    def _fmt_rating(self, value) -> str:
        try:
            num = float(value)
            return f"{num:.2f}"
        except Exception:
            return str(value if value is not None else "N/A")

    def add_voice_note_ui(self, sender: str, filepath: str):
        row_widget = QWidget()
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(f"{sender} voice: {os.path.basename(filepath)}")
        play_btn = QPushButton("Play")
        play_btn.clicked.connect(lambda _, p=filepath: self.play_audio(p))
        row_layout.addWidget(label)
        row_layout.addWidget(play_btn)
        row_layout.addStretch()
        row_widget.setLayout(row_layout)
        self.voice_layout.addWidget(row_widget)

    def play_audio(self, filepath: str):
        if self.media_player:
            self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(filepath)))
            self.media_player.play()
        else:
            QMessageBox.information(self, "Voice Note", f"Saved at {filepath}")


# ---------------------------- XO PAGE ---------------------------- #
class XOPage(QWidget):
    """Simple tic-tac-toe game against a light bot."""
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.board = [""] * 9
        self.game_over = False
        self.buttons: list[QPushButton] = []

        layout = QVBoxLayout()
        title = QLabel("<h1 style='color:#781414;'>Play XO</h1>")
        title.setAlignment(Qt.AlignCenter)
        self.status_label = QLabel("You are X. Make your move!")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color:#333; font-size:14px;")

        grid = QGridLayout()
        for r in range(3):
            for c in range(3):
                idx = r * 3 + c
                btn = QPushButton("")
                btn.setFixedSize(90, 90)
                btn.setStyleSheet("font-size:32px; font-weight:bold;")
                btn.clicked.connect(lambda _, i=idx: self.player_move(i))
                self.buttons.append(btn)
                grid.addWidget(btn, r, c)

        reset_btn = QPushButton("Reset Game")
        reset_btn.clicked.connect(self.reset_board)

        layout.addWidget(title)
        layout.addWidget(self.status_label)
        layout.addLayout(grid)
        layout.addWidget(reset_btn, alignment=Qt.AlignCenter)
        layout.addStretch()
        self.setLayout(layout)
        self.reset_board()

    def reset_board(self):
        self.board = [""] * 9
        self.game_over = False
        self.status_label.setText("You are X. Make your move!")
        for btn in self.buttons:
            btn.setText("")
            btn.setEnabled(True)

    def player_move(self, idx: int):
        if self.game_over or self.board[idx]:
            return
        self.place_mark(idx, "X")
        if self.check_and_finish("X", "You win! 🎉"):
            return
        self.bot_move()

    def bot_move(self):
        if self.game_over:
            return
        move = self.choose_bot_move()
        if move is None:
            return
        self.place_mark(move, "O")
        self.check_and_finish("O", "Bot wins this round.")

    def place_mark(self, idx: int, mark: str):
        self.board[idx] = mark
        btn = self.buttons[idx]
        btn.setText(mark)
        btn.setEnabled(False)

    def check_and_finish(self, mark: str, win_message: str) -> bool:
        if self.is_winner(mark):
            self.end_game(win_message)
            return True
        if not self.available_moves():
            self.end_game("It's a draw.")
            return True
        if mark == "X":
            self.status_label.setText("Bot is thinking...")
        else:
            self.status_label.setText("Your turn. Aim for three in a row!")
        return False

    def end_game(self, message: str):
        self.game_over = True
        self.status_label.setText(message)
        for btn in self.buttons:
            btn.setEnabled(False)

    def choose_bot_move(self) -> int | None:
        moves = self.available_moves()
        if not moves:
            return None

        # Try to win immediately
        for move in moves:
            self.board[move] = "O"
            if self.is_winner("O"):
                self.board[move] = ""
                return move
            self.board[move] = ""

        # Block player's next win
        for move in moves:
            self.board[move] = "X"
            if self.is_winner("X"):
                self.board[move] = ""
                return move
            self.board[move] = ""

        # Prefer center, then corners, then any edge
        if 4 in moves:
            return 4
        corners = [i for i in [0, 2, 6, 8] if i in moves]
        if corners:
            return random.choice(corners)
        return random.choice(moves)

    def available_moves(self):
        return [i for i, v in enumerate(self.board) if not v]

    def is_winner(self, mark: str) -> bool:
        wins = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
            (0, 3, 6), (1, 4, 7), (2, 5, 8),  # cols
            (0, 4, 8), (2, 4, 6)              # diagonals
        ]
        return any(all(self.board[i] == mark for i in line) for line in wins)

# ---------------------------- RATING PAGE ---------------------------- #
class RatingPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        layout = QVBoxLayout()
        self.title = QLabel("<h1 style='color:#781414;'>Rate Your Ride</h1>")
        self.title.setAlignment(Qt.AlignCenter)
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignCenter)
        self.stars = []
        star_layout = QHBoxLayout()
        for i in range(5):
            star = QPushButton("⭐")
            star.setStyleSheet("font-size:30px; background:none; border:none; color:#bbb;")
            star.clicked.connect(lambda _, x=i: self.set_rating(x + 1))
            self.stars.append(star)
            star_layout.addWidget(star, alignment=Qt.AlignCenter)
        layout.addStretch()
        layout.addWidget(self.title)
        layout.addLayout(star_layout)
        layout.addWidget(self.info_label)
        layout.addStretch()
        self.setLayout(layout)

    def refresh_role(self):
        role = self.parent.user_data.get("role")
        partner = self.parent.chat_partner
        if not partner:
            self.info_label.setText("No chat partner available for rating.")
            return
        if role == "driver":
            self.info_label.setText(f"Rate your passenger: {partner['name']}")
        else:
            self.info_label.setText(f"Rate your driver: {partner['name']}")

    def set_rating(self, value):
        if not self.parent.chat_started:
            QMessageBox.warning(self, "Invalid", "Start a chat before rating.")
            return
        for i, s in enumerate(self.stars):
            s.setStyleSheet(f"font-size:30px; background:none; border:none; color:{'#FFD700' if i < value else '#bbb'};")
        self.parent.user_data["rating"] = value
        partner = self.parent.chat_partner or {}
        target_username = partner.get("username")
        success = False
        if target_username:
            success = self.parent.controller.rate_partner(target_username, value, "")
        QMessageBox.information(self, "Thank You", f"{'Saved' if success else 'Failed to save'} rating: {value} stars")
        self.parent.goto_page("dashboard")


# ---------------------------- MAIN APP ---------------------------- #
class AUBusApp(QMainWindow):
    def __init__(self, conn: socket.socket):
        super().__init__()
        self.setWindowTitle("AUBus - Ride Sharing for AUB Students")
        self.setGeometry(200, 100, 950, 600)
        self.user_data = {}
        self.chat_partner = None
        self.chat_started = False
        self.controller = AUBusController(conn)
        # track last active p2p socket for restart handling
        self.active_p2p_socket = None

        container = QWidget()
        layout = QHBoxLayout(container)

        # Sidebar
        nav = QFrame()
        nav.setObjectName("sidebar")
        nav.setFixedWidth(200)
        nav.setStyleSheet("background-color:#781414; color:white;")
        nav_layout = QVBoxLayout(nav)
        nav_layout.addWidget(QLabel("<h2 style='color:white;'>AUBus</h2>"))

        self.buttons = {
            "Auth": "auth",
            "Profile": "profile",
            "Schedule": "schedule",
            "Dashboard": "dashboard",
            "Chat": "chat",
            "Rating": "rating",
            "XO": "xo",
        }

        for name, page in self.buttons.items():
            btn = QPushButton(name)
            btn.setStyleSheet("""
                QPushButton {color:white; background:none; border:none; text-align:left; padding:8px;}
                QPushButton:hover {color:#FFD700;}
            """)
            btn.clicked.connect(lambda _, p=page: self.goto_page(p))
            nav_layout.addWidget(btn)
        nav_layout.addStretch()

        # Emergency action available to all users
        emergency_btn = QPushButton("Emergency")
        emergency_btn.setStyleSheet("""
            QPushButton {
                color: white;
                background-color: #c0392b;
                border: 1px solid #a93226;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #e74c3c; }
        """)
        emergency_btn.clicked.connect(self.trigger_emergency)
        nav_layout.addWidget(emergency_btn)

        # Stacked pages
        self.stack = QStackedWidget()
        self.pages = {
            "auth": AuthPage(self, self.controller),
            "profile": ProfilePage(self, self.controller),
            "schedule": SchedulePage(self,self.controller),
            "dashboard": DashboardPage(self, self.controller),
            "chat": ChatPage(self, self.controller),
            "rating": RatingPage(self),
            "xo": XOPage(self),
        }
        for p in self.pages.values():
            self.stack.addWidget(p)

        layout.addWidget(nav)
        layout.addWidget(self.stack, stretch=1)

        layout.addWidget(nav)
        layout.addWidget(self.stack, stretch=1)

        # Create weather label INSIDE sidebar (at the bottom)
        self.weather_label = QLabel("🌤️ 23°C in Beirut")
        self.weather_label.setText(self.controller.get_weather(self.user_data.get('area','') if self.user_data.get("area") in self.user_data else "Beirut"))
        self.weather_label.setAlignment(Qt.AlignCenter)
        self.weather_label.setStyleSheet("""
            color: white;
            padding: 8px;
            font-size: 13px;
            border-top: 1px solid #a21d1d;
        """)

        # Add the weather label after all buttons (bottom of sidebar)
        nav_layout.addStretch()
        nav_layout.addWidget(self.weather_label)

        self.setCentralWidget(container)

        self.goto_page("auth")

        # Styling
        self.setStyleSheet("""
            QWidget {
                background-color: #f4f6fb;
                font-family: 'Arial', 'Helvetica', sans-serif;
                color: #1f2933;
            }
            QFrame#sidebar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #7f1d1d, stop:1 #5b0d0d);
            }
            QLabel { font-size: 16px; }
            QPushButton {
                background-color: #7f1d1d;
                color: white;
                border-radius: 8px;
                padding: 10px 14px;
                border: 1px solid #6b1111;
            }
            QPushButton:hover { background-color: #a12424; }
            QPushButton:pressed { background-color: #5f0f0f; }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #fff;
                border: 1px solid #cfd6e4;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                color: #1f2933;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border: 1px solid #a12424;
            }
            QTextEdit, QScrollArea {
                background-color: #ffffff;
                border: 1px solid #e3e8f0;
                border-radius: 10px;
            }
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e3e8f0;
                border-radius: 10px;
                gridline-color: #e3e8f0;
            }
            QHeaderView::section {
                background-color: #f5f7fb;
                color: #1f2933;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #e3e8f0;
            }
            QTableWidget::item:selected {
                background-color: #fde0e0;
                color: #1f2933;
            }
        """)

    def goto_page(self, name):
        """Navigate safely (block only before authentication)"""

        # Prevent accessing any page except Auth before login/register
        if not self.user_data.get("authenticated", False) and name != "auth":
            QMessageBox.warning(self, "Access Denied", "Please log in or register first.")
            return

        # Once authenticated, all pages are allowed
        if name == "profile":
            self.pages["profile"].refresh_info()
        elif name == "chat":
            self.pages["chat"].refresh_chat_header()
        elif name == "rating":
            self.pages["rating"].refresh_role()
        elif name == "schedule":
            if self.user_data.get("role") != "driver":
                QMessageBox.warning(self, "Access Denied", "Only drivers can access Schedule.")
                return
            self.pages["schedule"].load_schedule()

        self.stack.setCurrentWidget(self.pages[name])

    def trigger_emergency(self):
        """Send an emergency report with the richest context we have."""
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "user": dict(self.user_data),
            "chat_partner": dict(self.chat_partner) if self.chat_partner else {},
            "chat_started": self.chat_started,
            "role": self.user_data.get("role"),
            "p2p_connected": bool(self.controller.p2pcon),
        }
        success = self.controller.send_emergency_report(payload)
        if success:
            QMessageBox.information(self, "Emergency Sent", "Emergency alert sent to server.")
        else:
            QMessageBox.warning(self, "Failed", "Could not send emergency alert. Check connection.")
# ---------------------------- RUN APP ---------------------------- #
if __name__ == "__main__":
    ip: str = (input("enter IP: "))
    connection : socket.socket = connectToServer(ip)
    app = QApplication(sys.argv)
    window = AUBusApp(connection)
    window.show()
    sys.exit(app.exec_())
