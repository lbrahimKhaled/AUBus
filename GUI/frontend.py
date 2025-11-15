import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox,
    QVBoxLayout, QHBoxLayout, QStackedWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QMainWindow, QFrame, QRadioButton, QMessageBox, QSpinBox
)
from PyQt5.QtCore import Qt


# ---------------------------- AUTH PAGE ---------------------------- #
class AuthPage(QWidget):
    """Unified Login & Register Page"""
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
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
        if self.mode == "register":
            if not self.username.text() or not self.password.text():
                QMessageBox.warning(self, "Missing Info", "Please fill in required fields.")
                return
            self.parent.user_data = {
                "name": self.name.text(),
                "email": self.email.text(),
                "username": self.username.text(),
                "area": self.area.currentText(),
                "rating": 0,
                "role": None
            }
        else:
            if not self.username.text():
                QMessageBox.warning(self, "Missing Info", "Please enter your username.")
                return
            self.parent.user_data = {
                "name": self.username.text(),
                "email": "student@aub.edu.lb",
                "username": self.username.text(),
                "area": "Hamra",
                "rating": 0,
                "role": None
            }
        self.parent.goto_page("profile")


# ---------------------------- PROFILE PAGE ---------------------------- #
class ProfilePage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
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
        info = f"""
        <b>Name:</b> {data.get('name','')}<br>
        <b>Username:</b> {data.get('username','')}<br>
        <b>Email:</b> {data.get('email','')}<br>
        <b>Area:</b> {data.get('area','')}
        """
        stars = "⭐" * data.get("rating", 0)
        self.info_label.setText(info)
        self.rating_label.setText(f"<b>Your Rating:</b> {stars if stars else 'Not rated yet'}")

    def set_role(self):
        if self.driver_radio.isChecked():
            self.parent.user_data["role"] = "driver"
            self.parent.goto_page("schedule")
        elif self.passenger_radio.isChecked():
            self.parent.user_data["role"] = "passenger"
            self.parent.goto_page("dashboard")
        else:
            QMessageBox.warning(self, "Selection Required", "Please select Driver or Passenger.")


# ---------------------------- SCHEDULE PAGE ---------------------------- #
class SchedulePage(QWidget):
    def __init__(self, parent):
        super().__init__()
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


# ---------------------------- DASHBOARD PAGE ---------------------------- #
class DashboardPage(QWidget):
    def __init__(self, parent):
        super().__init__()
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

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Driver Name", "Area", "Departure", "Rating"])
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
        drivers = [
            ("Ali Hassan", "Hamra", "08", "⭐⭐⭐⭐"),
            ("Rami Khoury", "Verdun", "09", "⭐⭐⭐"),
            ("Maya Saab", "Achrafieh", "10", "⭐⭐⭐⭐⭐")
        ]
        self.table.setRowCount(len(drivers))
        for i, (n, a, t, r) in enumerate(drivers):
            for j, val in enumerate([n, a, t, r]):
                self.table.setItem(i, j, QTableWidgetItem(val))
        self.table.setVisible(True)

    def open_chat(self, row, _):
        selected_driver = self.table.item(row, 0).text()
        if selected_driver == self.parent.user_data.get("username"):
            QMessageBox.warning(self, "Invalid Action", "You cannot chat with yourself.")
            return
        area = self.table.item(row, 1).text()
        rating = self.table.item(row, 3).text()
        self.parent.chat_partner = {"name": selected_driver, "area": area, "rating": rating}
        self.parent.chat_started = True
        self.parent.goto_page("chat")


# ---------------------------- CHAT PAGE ---------------------------- #
class ChatPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.header = QLabel()
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setStyleSheet("background-color:#781414; color:white; padding:10px;")

        self.chat_box = QTextEdit()
        self.chat_box.setReadOnly(True)
        msg_layout = QHBoxLayout()
        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Type message...")
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(lambda: self.chat_box.append(f"You: {self.msg_input.text()}"))
        msg_layout.addWidget(self.msg_input)
        msg_layout.addWidget(send_btn)

        rate_btn = QPushButton("Rate")
        rate_btn.clicked.connect(self.open_rating)

        layout = QVBoxLayout()
        layout.addWidget(self.header)
        layout.addWidget(self.chat_box)
        layout.addLayout(msg_layout)
        layout.addWidget(rate_btn, alignment=Qt.AlignRight)
        self.setLayout(layout)

    def refresh_chat_header(self):
        partner = self.parent.chat_partner
        if not partner:
            self.header.setText("No active chat")
        else:
            self.header.setText(f"Chatting with: <b>{partner['name']}</b> | Area: {partner['area']} | Rating: {partner['rating']}")

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
        QMessageBox.information(self, "Thank You", f"You rated {value} stars!")
        self.parent.goto_page("profile")


# ---------------------------- MAIN APP ---------------------------- #
class AUBusApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AUBus - Ride Sharing for AUB Students")
        self.setGeometry(200, 100, 950, 600)
        self.user_data = {}
        self.chat_partner = None
        self.chat_started = False

        container = QWidget()
        layout = QHBoxLayout(container)
        nav = QFrame()
        nav.setFixedWidth(200)
        nav.setStyleSheet("background-color:#781414; color:white;")
        nav_layout = QVBoxLayout(nav)
        nav_layout.addWidget(QLabel("<h2 style='color:white;'>AUBus</h2>"))

        buttons = {
            "Auth": "auth",
            "Profile": "profile",
            "Schedule": "schedule",
            "Dashboard": "dashboard",
            "Chat": "chat",
            "Rating": "rating"
        }
        for name, page in buttons.items():
            btn = QPushButton(name)
            btn.setStyleSheet("""
                QPushButton {color:white; background:none; border:none; text-align:left; padding:8px;}
                QPushButton:hover {color:#FFD700;}
            """)
            btn.clicked.connect(lambda _, p=page: self.goto_page(p))
            nav_layout.addWidget(btn)
        nav_layout.addStretch()

        self.stack = QStackedWidget()
        self.pages = {
            "auth": AuthPage(self),
            "profile": ProfilePage(self),
            "schedule": SchedulePage(self),
            "dashboard": DashboardPage(self),
            "chat": ChatPage(self),
            "rating": RatingPage(self)
        }
        for p in self.pages.values():
            self.stack.addWidget(p)

        layout.addWidget(nav)
        layout.addWidget(self.stack, stretch=1)
        self.setCentralWidget(container)
        self.goto_page("auth")

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
        if name == "profile":
            self.pages["profile"].refresh_info()
        if name == "chat":
            self.pages["chat"].refresh_chat_header()
        if name == "rating":
            self.pages["rating"].refresh_role()
        if name == "schedule" and self.user_data.get("role") != "driver":
            QMessageBox.warning(self, "Access Denied", "Only drivers can access Schedule.")
            return
        self.stack.setCurrentWidget(self.pages[name])


# ---------------------------- RUN APP ---------------------------- #
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AUBusApp()
    window.show()
    sys.exit(app.exec_())