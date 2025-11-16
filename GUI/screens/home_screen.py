# GUI/screens/home_screen.py
import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import Any, Dict


class HomeScreen(tk.Frame):
    """
    Very simple home screen.

    Just shows a welcome message and some placeholder buttons
    (we'll add real navigation later: schedules, ride request, etc.).
    """

    def __init__(self, master, client, **kwargs):
        super().__init__(master, **kwargs)
        self.client = client
        self.user_info: Dict[str, Any] | None = None

        self._build_widgets()

    def _build_widgets(self) -> None:
        self.columnconfigure(0, weight=1)

        self.label_title = tk.Label(
            self, text="Welcome to AUBus", font=("Arial", 18, "bold"))
        self.label_title.grid(row=0, column=0, pady=(20, 10))

        self.label_user = tk.Label(self, text="", font=("Arial", 12))
        self.label_user.grid(row=1, column=0, pady=(0, 20))

        # Row 2: Schedules (driver)
        btn_schedules = tk.Button(
            self,
            text="My Schedules (driver)",
            command=self._on_schedules_clicked,
            highlightthickness=0,
            borderwidth=1,
        )
        btn_schedules.grid(row=2, column=0, pady=5)

        # Row 3: Request ride (rider)
        btn_request = tk.Button(
            self,
            text="Request a Ride (rider)",
            command=self._on_request_clicked,
            highlightthickness=0,
            borderwidth=1,
        )
        btn_request.grid(row=3, column=0, pady=5)

        # Row 4: My ride requests (rider)
        btn_my_requests = tk.Button(
            self,
            text="My ride requests (rider)",
            command=self._on_my_requests_clicked,
            highlightthickness=0,
            borderwidth=1,
        )
        btn_my_requests.grid(row=4, column=0, pady=5)

        # Row 5: Incoming ride requests (driver)
        btn_incoming = tk.Button(
            self,
            text="Incoming ride requests (driver)",
            command=self._on_incoming_clicked,
            highlightthickness=0,
            borderwidth=1,
        )
        btn_incoming.grid(row=5, column=0, pady=5)

        # Row 6: Debug chat
        btn_debug_chat = tk.Button(
            self,
            text="Open debug chat",
            command=self._on_debug_chat_clicked,
            highlightthickness=0,
            borderwidth=1,
        )
        btn_debug_chat.grid(row=6, column=0, pady=5)

        # Row 7: My Ratings
        btn_ratings = tk.Button(
            self,
            text="My Ratings",
            command=self._on_ratings_clicked,
            highlightthickness=0,
            borderwidth=1,
        )
        btn_ratings.grid(row=7, column=0, pady=5)

        # Row 8: Logout
        btn_logout = tk.Button(
            self,
            text="Logout",
            command=self._on_logout_clicked,
            highlightthickness=0,
            borderwidth=1,
        )
        btn_logout.grid(row=8, column=0, pady=20)

    def _on_schedules_clicked(self) -> None:
        # Only drivers have schedules in our design
        if not self.user_info:
            messagebox.showinfo("Info", "No user information available.")
            return

        is_driver = self.user_info.get("is_driver", False)
        if not is_driver:
            messagebox.showinfo("Info", "Only drivers can manage schedules.")
            return

        self.master.show_schedules_screen()

    def set_user(self, user_info: Dict[str, Any]) -> None:
        """
        Called by App when we navigate to HomeScreen.
        """
        self.user_info = user_info
        name = user_info.get("name", "User")
        is_driver = user_info.get("is_driver", False)
        role = "Driver" if is_driver else "Rider"

        self.label_user.config(text=f"Logged in as: {name} ({role})")

    def _on_logout_clicked(self) -> None:
        # No backend logout needed for our protocol; just go back to login screen.
        self.master.show_login_screen()

    def _on_request_clicked(self) -> None:
        if not self.user_info:
            messagebox.showinfo("Info", "No user information available.")
            return

        is_driver = self.user_info.get("is_driver", False)
        if is_driver:
            messagebox.showinfo("Info", "Ride requests are for riders only.")
            return

        self.master.show_ride_request_screen()

    def _on_debug_chat_clicked(self) -> None:
        """
        Temporary dev feature: open a chat for any channel id.
        Later, chat will be tied to specific ride requests.
        """
        channel_id = simpledialog.askstring(
            "Chat channel", "Enter channel ID:")
        if not channel_id:
            return

        self.master.show_chat_screen(channel_id)

    def _on_ratings_clicked(self) -> None:
        self.master.show_ratings_screen()

    def _on_my_requests_clicked(self) -> None:
        if not self.user_info:
            messagebox.showinfo("Info", "No user information available.")
            return

        is_driver = self.user_info.get("is_driver", False)
        if is_driver:
            messagebox.showinfo(
                "Info", "My ride requests are for riders only.")
            return

        self.master.show_rider_requests_screen()

    def _on_incoming_clicked(self) -> None:
        if not self.user_info:
            messagebox.showinfo("Info", "No user information available.")
            return

        is_driver = self.user_info.get("is_driver", False)
        if not is_driver:
            messagebox.showinfo(
                "Info", "Incoming ride requests are for drivers only.")
            return

        self.master.show_driver_requests_screen()
