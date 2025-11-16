# gui/app.py
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Dict, Optional

from .net import AubusClient, AubusClientError
from .screens.login_screen import LoginScreen
from .screens.home_screen import HomeScreen
from .screens.register_screen import RegisterScreen
from .screens.schedules_screen import SchedulesScreen
from .screens.ride_request_screen import RideRequestScreen
from .screens.chat_screen import ChatScreen
from .screens.ratings_screen import RatingsScreen
from .screens.rider_requests_screen import RiderRequestsScreen
from .screens.driver_requests_screen import DriverRequestsScreen


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("AUBus – AUB Commuter")
        self.geometry("1100x700")
        self.minsize(900, 600)

        # Allow dark, “card” style layout
        self.configure(bg="#020617")  # slate-950

        self.client = AubusClient()
        self.current_user: Optional[Dict[str, Any]] = None
        self.current_screen: Optional[tk.Frame] = None

        self._setup_style()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.show_login_screen()

    # ---------- global style ----------

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        BG = "#020617"
        CARD_BG = "#020617"
        NAV_BG = "#020617"
        ACCENT = "#38bdf8"      # sky-400
        ACCENT_SOFT = "#0ea5e9"  # sky-500
        TEXT = "#e5e7eb"        # gray-200
        MUTED = "#9ca3af"       # gray-400

        # Frames
        style.configure("Aubus.TFrame", background=BG)
        style.configure("Aubus.Nav.TFrame", background=NAV_BG)
        style.configure("Aubus.Card.TFrame", background=CARD_BG, relief="flat")

        # Labels
        style.configure(
            "Aubus.Heading.TLabel",
            background=CARD_BG,
            foreground=TEXT,
            font=("SF Pro Display", 22, "bold"),
        )
        style.configure(
            "Aubus.Body.TLabel",
            background=CARD_BG,
            foreground=TEXT,
            font=("SF Pro Text", 11),
        )
        style.configure(
            "Aubus.Muted.TLabel",
            background=CARD_BG,
            foreground=MUTED,
            font=("SF Pro Text", 10),
        )
        style.configure(
            "Aubus.Brand.TLabel",
            background=NAV_BG,
            foreground=ACCENT,
            font=("SF Pro Display", 20, "bold"),
        )
        style.configure(
            "Aubus.NavText.TLabel",
            background=NAV_BG,
            foreground=TEXT,
            font=("SF Pro Text", 10),
        )

        # Buttons
        style.configure(
            "Aubus.Primary.TButton",
            padding=8,
            font=("SF Pro Text", 11, "bold"),
            foreground="#0b1120",
            background=ACCENT,
        )
        style.map(
            "Aubus.Primary.TButton",
            background=[("active", ACCENT_SOFT)],
        )
        style.configure(
            "Aubus.Secondary.TButton",
            padding=7,
            font=("SF Pro Text", 10),
            foreground=TEXT,
            background="#111827",
        )
        style.map(
            "Aubus.Secondary.TButton",
            background=[("active", "#1f2937")],
        )
        style.configure(
            "Aubus.Link.TButton",
            padding=0,
            relief="flat",
            foreground=ACCENT,
            background=BG,
            font=("SF Pro Text", 10, "underline"),
        )

        # Entries
        style.configure(
            "Aubus.TEntry",
            fieldbackground="#020617",
            foreground=TEXT,
            insertcolor=TEXT,
        )

        # Treeview
        style.configure(
            "Aubus.Treeview",
            background="#020617",
            foreground=TEXT,
            fieldbackground="#020617",
            rowheight=26,
        )
        style.map(
            "Aubus.Treeview",
            background=[("selected", "#1e293b")],
        )
        style.configure(
            "Aubus.Treeview.Heading",
            background="#0f172a",
            foreground=TEXT,
            font=("SF Pro Text", 10, "bold"),
        )

    # ---------- helpers ----------

    def set_user(self, user_info: Dict[str, Any]) -> None:
        self.current_user = user_info

    def get_user(self) -> Optional[Dict[str, Any]]:
        return self.current_user

    def show_error(self, message: str) -> None:
        messagebox.showerror("AUBus", message, parent=self)

    def show_info(self, message: str) -> None:
        messagebox.showinfo("AUBus", message, parent=self)

    def _switch_screen(self, screen_cls, *args, **kwargs) -> None:
        if self.current_screen is not None:
            self.current_screen.destroy()

        frame = screen_cls(self, self, *args, **kwargs)
        frame.pack(fill="both", expand=True)
        self.current_screen = frame

    # ---------- navigation targets ----------

    def show_login_screen(self) -> None:
        self._switch_screen(LoginScreen)

    def show_home_screen(self) -> None:
        self._switch_screen(HomeScreen)

    def show_register_screen(self) -> None:
        self._switch_screen(RegisterScreen)

    def show_schedules_screen(self) -> None:
        user = self.get_user()
        if not user or not user.get("is_driver"):
            self.show_error("Only driver accounts can manage schedules.")
            return
        self._switch_screen(SchedulesScreen)

    def show_ride_request_screen(self) -> None:
        self._switch_screen(RideRequestScreen)

    def show_chat_screen(self, channel_id: str, title: str | None = None) -> None:
        self._switch_screen(
            ChatScreen, channel_id=channel_id, chat_title=title)

    def show_ratings_screen(self) -> None:
        self._switch_screen(RatingsScreen)

    def show_rider_requests_screen(self) -> None:
        self._switch_screen(RiderRequestsScreen)

    def show_driver_requests_screen(self) -> None:
        self._switch_screen(DriverRequestsScreen)

    def logout(self) -> None:
        self.current_user = None
        # we keep same connection; next login will overwrite user_id on server
        self.show_login_screen()

    def _on_close(self) -> None:
        try:
            self.client.close()
        finally:
            self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
