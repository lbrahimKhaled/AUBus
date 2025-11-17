import socket
import requests
import sys
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox,
    QVBoxLayout, QHBoxLayout, QStackedWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QMainWindow, QFrame, QRadioButton, QMessageBox, QSpinBox, QSplitter
)
from PyQt5.QtCore import Qt
from backend.connections.client.client import * #connectToServer, sendCredentials, requestOther, receiveOther, changeMsg, 
from backend.DB.db import get_user_by_username

# ---------------------------- CONTROLLER ---------------------------- #
#for practical reasons and so that we don't let the pages block each other we will have a common controller to glue the GUI to the backend
class AUBusController:
    def __init__(self, conn: socket.socket):
        self.conn = conn
        self.p2pcon = None
        self.on_p2p_ready = None

    def set_p2p_socket(self, sock: socket.socket):
        """Store the active P2P socket and notify any listener."""
        self.p2pcon = sock
        if callable(self.on_p2p_ready):
            self.on_p2p_ready()

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

    def getOther(self):
        requestOther(self.conn)
        drivers: list[dict] = receiveOther(self.conn)
        return drivers
    
    def get_weather(self, location: str)->str:
        # try:
        #     api_key = "34b53f4628054c4bbf2154149251611"
        #     url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={location}&aqi=no"
        #     response = requests.get(url)
        #     data = response.json()
        #     temp = data["current"]["temp_c"]
        #     description = data["current"]["condition"]["text"].capitalize()
        #     return f"🌤️ {temp:.1f}°C, {description} in {location}"
        # except Exception:
            return "🌤️ Weather unavailable"

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

    def sendSchedule(self, weekday: int, depart_time: int, direction: str)->None:
        send_schedule_to_server(self.conn, weekday, str(depart_time), direction)



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
        self.controller = controller
        layout = QVBoxLayout()
        title = QLabel("<h1 style='color:#781414;'>Your Schedule</h1>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.day_select = QComboBox()
        self.day_select.addItems(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])

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

    def add_schedule(self):
        day = self.day_select.currentText()
        dep_home = self.home_depart.value()
        dep_aub = self.aub_depart.value()
        row = self.table.rowCount()
        self.table.insertRow(row)
        for c, v in enumerate([day, str(dep_home), str(dep_aub)]):
            self.table.setItem(row, c, QTableWidgetItem(v))
        
        self.controller.sendSchedule(self.day_select.currentIndex(), dep_home, "toAUB")
        # self.controller.sendSchedule(self.day_select.currentIndex(), dep_aub, "fromAUB")


# ---------------------------- DASHBOARD PAGE ---------------------------- #
class DashboardPage(QWidget):
    def __init__(self, parent, controller: AUBusController):
        super().__init__()
        self.controller = controller
        self.parent = parent
        layout = QVBoxLayout()
        title = QLabel("<h1 style='color:#781414;'>Dashboard</h1>")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Request a ride and view available drivers")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color:#555; font-size:14px;")

        self.area_box = QComboBox()
        self.area_box.addItems(["Select Area", "Hamra", "Achrafieh", "Verdun", "Jnah", "Other"])

        self.time_spin = QSpinBox()
        self.time_spin.setRange(0, 23)
        self.time_spin.setPrefix("Pickup Hour (0-23): ")

        req_btn = QPushButton("Send Ride Request")
        req_btn.clicked.connect(self.show_drivers)

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
        layout.addWidget(self.time_spin)
        layout.addWidget(req_btn)
        layout.addSpacing(20)
        layout.addWidget(self.table)
        layout.addStretch()
        self.setLayout(layout)

    def show_drivers(self):
        drivers : list[dict] = self.controller.getOther()
        print(drivers)
        self.table.setRowCount(len(drivers))
        for i, driver in enumerate(drivers):
            name = str(driver.get("name", "N/A"))
            username = str(driver.get("username", "N/A"))
            email = str(driver.get("email", "N/A"))
            area = str(driver.get("area", driver.get("location", "N/A")))
            ip = str(driver.get("ip", ""))
            rating = str(driver.get("rating_avg", driver.get("rating", "N/A")))
            for j, val in enumerate([name, username, email, area, ip, rating]):
                self.table.setItem(i, j, QTableWidgetItem(val))
        self.table.setVisible(True)


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
        P2Pcon = waitForChatApproval(self.controller.conn)
        if not P2Pcon:
            QMessageBox.warning(self, "Chat Failed", "No response from driver or server.")
            return
        self.controller.set_p2p_socket(P2Pcon)
        self.parent.goto_page("chat")


# ---------------------------- CHAT PAGE ---------------------------- #
class ChatPage(QWidget):
    """Chat page adapts based on role (Driver gets split view, Passenger sees only chat)"""
    def __init__(self, parent, controller:AUBusController):
        super().__init__()
        self.parent = parent
        self.controller = controller
        self.receiver_started = False
        # Left panel: Chat
        self.header = QLabel("No active chat")
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setStyleSheet("background-color:#781414; color:white; padding:10px;")

        self.chat_box = QTextEdit()
        self.chat_box.setReadOnly(True)

        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Type message...")
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_message)

        msg_layout = QHBoxLayout()
        msg_layout.addWidget(self.msg_input)
        msg_layout.addWidget(send_btn)

        self.rate_btn = QPushButton("Rate")
        self.rate_btn.clicked.connect(self.open_rating)

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.header)
        left_layout.addWidget(self.chat_box)
        left_layout.addLayout(msg_layout)
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
        self.passengers = self.controller.getOther()

        # Clear and refill table
        self.passenger_table.setRowCount(len(self.passengers))
        for i, driver in enumerate(self.passengers):
            name = str(driver.get("name", "N/A"))
            username = str(driver.get("username", "N/A"))
            email = str(driver.get("email", "N/A"))
            area = str(driver.get("area", driver.get("location", "N/A")))
            ip = str(driver.get("ip", ""))
            rating = str(driver.get("rating_avg", driver.get("rating", "N/A")))

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

        # Mark chat state
        self.parent.chat_partner = passenger
        self.parent.chat_started = True

        # Update chat header and clear previous chat
        self.chat_box.clear()
        self.header.setText(
            f"Chatting with: <b>{passenger.get('name')}</b> | "
            f"Area: {passenger.get('location', passenger.get('area','N/A'))} | "
            f"Rating: {passenger.get('rating','N/A')}"
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
            self.header.setText(
                f"Chatting with: <b>{partner['name']}</b> | Area: {partner['area']} | Rating: {partner['rating']}"
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

        # Send through P2P socket
        try:
            if self.controller.p2pcon:
                self.controller.p2pcon.sendall(msg.encode('utf-8'))
            else:
                QMessageBox.warning(self, "No Connection", "P2P connection not established yet.")
        except Exception as e:
            QMessageBox.warning(self, "Send Failed", f"Error: {e}")

    def start_receiver(self):
        """
        Starts a background thread that continuously listens for incoming chat messages.
        """
        if not self.controller.p2pcon:
            return
        if self.receiver_started:
            return
        self.receiver_started = True

        def listen_for_messages():
            while True:
                try:
                    data = self.controller.p2pcon.recv(1024)
                    if not data:
                        break
                    msg = data.decode('utf-8')
                    self.chat_box.append(f"Peer: {msg}")
                except Exception as e:
                    print("Receiver stopped:", e)
                    break

        threading.Thread(target=listen_for_messages, daemon=True).start()

    def open_rating(self):
        if not self.parent.chat_started or not self.parent.chat_partner:
            QMessageBox.warning(self, "No Chat", "You must chat with someone before rating.")
            return
        self.parent.goto_page("rating")

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

        container = QWidget()
        layout = QHBoxLayout(container)

        # Sidebar
        nav = QFrame()
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
            "Rating": "rating"
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

        # Stacked pages
        self.stack = QStackedWidget()
        self.pages = {
            "auth": AuthPage(self, self.controller),
            "profile": ProfilePage(self, self.controller),
            "schedule": SchedulePage(self,self.controller),
            "dashboard": DashboardPage(self, self.controller),
            "chat": ChatPage(self, self.controller),
            "rating": RatingPage(self)
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
            QWidget { background-color: #fdfdfd; font-family: 'Segoe UI'; color: #222; }
            QLabel { font-size: 16px; }
            QPushButton {
                background-color: #781414;
                color: white;
                border-radius: 5px;
                padding: 8px 12px;
            }
            QPushButton:hover { background-color: #a21d1d; }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #fff;
                border: 1px solid #bbb;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
                color: #222;
            }
            QTableWidget { background-color: white; border: 1px solid #bbb; }
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
        elif name == "schedule" and self.user_data.get("role") != "driver":
            QMessageBox.warning(self, "Access Denied", "Only drivers can access Schedule.")
            return

        self.stack.setCurrentWidget(self.pages[name])
# ---------------------------- RUN APP ---------------------------- #
if __name__ == "__main__":
    ip: str = "192.168.1.142" #(input("enter IP: "))
    connection : socket.socket = connectToServer(ip)
    app = QApplication(sys.argv)
    window = AUBusApp(connection)
    window.show()
    sys.exit(app.exec_())
