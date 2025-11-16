# gui/screens/home_screen.py
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from .base import BaseScreen

if TYPE_CHECKING:
    from ..app import App


class HomeScreen(BaseScreen):
    def __init__(self, master: tk.Widget, app: "App") -> None:
        super().__init__(master, app, title="Dashboard")

        user = app.get_user() or {}
        is_driver = bool(user.get("is_driver"))
        name = user.get("name", "AUB user")

        # Greeting
        subtitle = ttk.Label(
            self.body,
            text=f"Good to see you, {name}.",
            style="Aubus.Body.TLabel",
        )
        subtitle.grid(row=1, column=0, sticky="w")

        # Layout cards
        cards = ttk.Frame(self.body, style="Aubus.Card.TFrame")
        cards.grid(row=2, column=0, sticky="nsew", pady=(16, 0))
        cards.columnconfigure(0, weight=1)
        cards.columnconfigure(1, weight=1)
        cards.columnconfigure(2, weight=1)

        # Card 1 – Next action
        c1 = ttk.Frame(cards, style="Aubus.Card.TFrame", padding=16)
        c1.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ttk.Label(c1, text="Today’s commute", style="Aubus.Body.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        if is_driver:
            subtitle_text = "Set your driver schedule and accept matching rides."
        else:
            subtitle_text = "Request a ride that matches your time and area."

        ttk.Label(
            c1,
            text=subtitle_text,
            style="Aubus.Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 12))

        row = 2
        if is_driver:
            ttk.Button(
                c1,
                text="Manage schedules",
                style="Aubus.Primary.TButton",
                command=self.app.show_schedules_screen,
            ).grid(row=row, column=0, sticky="w")
            row += 1
            ttk.Button(
                c1,
                text="Request a ride",
                style="Aubus.Secondary.TButton",
                command=self.app.show_ride_request_screen,
            ).grid(row=row, column=0, sticky="w", pady=(8, 0))
        else:
            # Riders: only ride requests, no schedules
            ttk.Button(
                c1,
                text="Request a ride",
                style="Aubus.Primary.TButton",
                command=self.app.show_ride_request_screen,
            ).grid(row=row, column=0, sticky="w")

        # Card 2 – Role-based
        c2 = ttk.Frame(cards, style="Aubus.Card.TFrame", padding=16)
        c2.grid(row=0, column=1, sticky="nsew", padx=8)

        if is_driver:
            ttk.Label(c2, text="Incoming ride requests", style="Aubus.Body.TLabel").grid(
                row=0, column=0, sticky="w"
            )
            ttk.Label(
                c2,
                text="See riders that match your schedule and accept rides.",
                style="Aubus.Muted.TLabel",
            ).grid(row=1, column=0, sticky="w", pady=(4, 12))
            ttk.Button(
                c2,
                text="Open driver requests",
                style="Aubus.Primary.TButton",
                command=self.app.show_driver_requests_screen,
            ).grid(row=2, column=0, sticky="w")
        else:
            ttk.Label(c2, text="Your ride requests", style="Aubus.Body.TLabel").grid(
                row=0, column=0, sticky="w"
            )
            ttk.Label(
                c2,
                text="Track your ride requests, status, and chats with drivers.",
                style="Aubus.Muted.TLabel",
            ).grid(row=1, column=0, sticky="w", pady=(4, 12))
            ttk.Button(
                c2,
                text="View my requests",
                style="Aubus.Primary.TButton",
                command=self.app.show_rider_requests_screen,
            ).grid(row=2, column=0, sticky="w")

        # Card 3 – Ratings
        c3 = ttk.Frame(cards, style="Aubus.Card.TFrame", padding=16)
        c3.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

        rating = user.get("rating_avg", 0.0)
        count = user.get("rating_count", 0)

        ttk.Label(c3, text="Your reputation", style="Aubus.Body.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            c3,
            text=f"{rating:.1f}★ from {count} rating(s)",
            style="Aubus.Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 8))

        ttk.Button(
            c3,
            text="View ratings",
            style="Aubus.Secondary.TButton",
            command=self.app.show_ratings_screen,
        ).grid(row=2, column=0, sticky="w")
