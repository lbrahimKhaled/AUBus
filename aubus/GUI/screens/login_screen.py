# gui/screens/login_screen.py
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from ..net import AubusClientError

if TYPE_CHECKING:
    from ..app import App


class LoginScreen(ttk.Frame):
    def __init__(self, master: tk.Widget, app: "App") -> None:
        super().__init__(master, style="Aubus.TFrame")
        self.app = app

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        container = ttk.Frame(self, style="Aubus.TFrame", padding=40)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)

        # Left hero section
        left = ttk.Frame(container, style="Aubus.TFrame",
                         padding=(0, 40, 24, 40))
        left.grid(row=0, column=0, sticky="nsew")
        left.columnconfigure(0, weight=1)

        title = ttk.Label(
            left,
            text="Welcome to AUBus",
            style="Aubus.Heading.TLabel",
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(
            left,
            text="Smart, simple rides between home and AUB.\nLog in to see your schedules, rides, and chats.",
            style="Aubus.Body.TLabel",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(8, 24))

        bullet = ttk.Label(
            left,
            text="• One place for all your daily commutes\n• Drivers and riders matched by area & time\n• Built for the AUB community",
            style="Aubus.Muted.TLabel",
        )
        bullet.grid(row=2, column=0, sticky="w")

        # Right login card
        card = ttk.Frame(container, style="Aubus.Card.TFrame", padding=24)
        card.grid(row=0, column=1, sticky="nsew")
        card.columnconfigure(0, weight=1)

        heading = ttk.Label(card, text="Sign in", style="Aubus.Heading.TLabel")
        heading.grid(row=0, column=0, sticky="w", pady=(0, 12))

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        def field(row: int, label: str, var: tk.StringVar, show: str | None = None):
            l = ttk.Label(card, text=label, style="Aubus.Body.TLabel")
            l.grid(row=row, column=0, sticky="w", pady=(8, 2))
            e = ttk.Entry(card, textvariable=var,
                          style="Aubus.TEntry", show=show or "")
            e.grid(row=row + 1, column=0, sticky="ew")
            return e

        user_entry = field(1, "Username", self.username_var)
        pass_entry = field(3, "Password", self.password_var, show="•")

        user_entry.focus_set()

        btn_login = ttk.Button(
            card,
            text="Sign in",
            style="Aubus.Primary.TButton",
            command=self._on_login,
        )
        btn_login.grid(row=5, column=0, sticky="ew", pady=(16, 8))

        extra = ttk.Frame(card, style="Aubus.Card.TFrame")
        extra.grid(row=6, column=0, sticky="ew", pady=(4, 0))
        extra.columnconfigure(0, weight=1)

        lbl = ttk.Label(extra, text="New to AUBus?",
                        style="Aubus.Muted.TLabel")
        lbl.grid(row=0, column=0, sticky="w")

        btn_register = ttk.Button(
            extra,
            text="Create an account",
            style="Aubus.Link.TButton",
            command=self.app.show_register_screen,
        )
        btn_register.grid(row=0, column=1, sticky="e")

    def _on_login(self) -> None:
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()

        if not username or not password:
            self.app.show_error("Please enter both username and password.")
            return

        try:
            payload = self.app.client.login(username, password)
        except AubusClientError as e:
            msg = "Invalid credentials." if e.code == "INVALID_CREDENTIALS" else f"Login failed: {e.code}"
            self.app.show_error(msg)
            return

        user_info = {
            "user_id": payload["user_id"],
            "name": payload["name"],
            "area": payload["area"],
            "is_driver": payload["is_driver"],
            "rating_avg": payload["rating_avg"],
            "rating_count": payload["rating_count"],
            "username": username,
        }
        self.app.set_user(user_info)
        self.app.show_home_screen()
