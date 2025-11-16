# gui/screens/base.py
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..app import App


class BaseScreen(ttk.Frame):
    """
    Base screen with:
      - top navigation bar
      - central "card" body
    """

    def __init__(
        self,
        master: tk.Widget,
        app: "App",
        title: str,
        show_nav: bool = True,
    ) -> None:
        super().__init__(master, style="Aubus.TFrame")
        self.app = app
        self._title = title

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)

        if show_nav:
            self._build_navbar()

        self.body = ttk.Frame(self, style="Aubus.Card.TFrame", padding=24)
        self.body.grid(row=1, column=0, sticky="nsew", padx=32, pady=(16, 24))
        self.body.columnconfigure(0, weight=1)

        header = ttk.Label(self.body, text=title, style="Aubus.Heading.TLabel")
        header.grid(row=0, column=0, sticky="w", pady=(0, 12))

    # ---------- navbar ----------

    def _build_navbar(self) -> None:
        bar = ttk.Frame(self, style="Aubus.Nav.TFrame", padding=(24, 10))
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(2, weight=1)

        user = self.app.get_user()
        is_driver = bool(user and user.get("is_driver"))

        brand = ttk.Label(bar, text="AUBus", style="Aubus.Brand.TLabel")
        brand.grid(row=0, column=0, sticky="w")

        summary_text = ""
        if user:
            role = "Driver" if is_driver else "Rider"
            rating = user.get("rating_avg", 0.0)
            count = user.get("rating_count", 0)
            summary_text = f"{user.get('name', '')} · {role} · {rating:.1f}★ ({count}) · {user.get('area', '')}"

        summary = ttk.Label(bar, text=summary_text,
                            style="Aubus.NavText.TLabel")
        summary.grid(row=0, column=1, padx=16, sticky="w")

        nav_btns = ttk.Frame(bar, style="Aubus.Nav.TFrame")
        nav_btns.grid(row=0, column=2, sticky="e")

        def nav_button(text: str, cmd) -> ttk.Button:
            return ttk.Button(
                nav_btns,
                text=text,
                style="Aubus.Secondary.TButton",
                command=cmd,
            )

        # Build buttons dynamically so riders don't see "Schedules"
        buttons = [
            ("Home", self.app.show_home_screen),
        ]

        if is_driver:
            buttons.append(("Schedules", self.app.show_schedules_screen))

        buttons.extend([
            ("Ride", self.app.show_ride_request_screen),
            ("Requests", self._go_requests),
            ("Ratings", self.app.show_ratings_screen),
            ("Logout", self.app.logout),
        ])

        for i, (label, cmd) in enumerate(buttons):
            b = nav_button(label, cmd)
            b.grid(row=0, column=i, padx=4)

    def _go_requests(self) -> None:
        user = self.app.get_user()
        if user and user.get("is_driver"):
            self.app.show_driver_requests_screen()
        else:
            self.app.show_rider_requests_screen()
