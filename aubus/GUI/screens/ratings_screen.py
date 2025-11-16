# gui/screens/ratings_screen.py
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from .base import BaseScreen
from ..net import AubusClientError

if TYPE_CHECKING:
    from ..app import App


class RatingsScreen(BaseScreen):
    def __init__(self, master: tk.Widget, app: "App") -> None:
        super().__init__(master, app, title="Ratings")

        self.body.rowconfigure(1, weight=1)

        # Table of received ratings
        table_frame = ttk.Frame(self.body, style="Aubus.Card.TFrame")
        table_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 8))

        columns = ("stars", "comment", "from", "date")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="Aubus.Treeview",
        )
        for col, width in [
            ("stars", 60),
            ("comment", 380),
            ("from", 180),
            ("date", 160),
        ]:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=width,
                             anchor="w" if col == "comment" else "center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # Simple form to rate another user (by id)
        form = ttk.Frame(self.body, style="Aubus.Card.TFrame")
        form.grid(row=2, column=0, sticky="ew")
        for c in range(4):
            form.columnconfigure(c, weight=0)
        form.columnconfigure(2, weight=1)

        ttk.Label(form, text="Rate user ID", style="Aubus.Muted.TLabel").grid(
            row=0, column=0, sticky="w", pady=(4, 2)
        )
        self.ratee_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.ratee_var, width=6, style="Aubus.TEntry").grid(
            row=1, column=0, sticky="w"
        )

        ttk.Label(form, text="Stars (1–5)", style="Aubus.Muted.TLabel").grid(
            row=0, column=1, sticky="w", padx=(8, 0)
        )
        self.stars_var = tk.StringVar(value="5")
        ttk.Entry(form, textvariable=self.stars_var, width=4, style="Aubus.TEntry").grid(
            row=1, column=1, sticky="w", padx=(8, 0)
        )

        ttk.Label(form, text="Comment", style="Aubus.Muted.TLabel").grid(
            row=0, column=2, sticky="w", padx=(8, 0)
        )
        self.comment_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.comment_var, style="Aubus.TEntry").grid(
            row=1, column=2, sticky="ew", padx=(8, 8)
        )

        ttk.Button(
            form,
            text="Submit rating",
            style="Aubus.Secondary.TButton",
            command=self._rate,
        ).grid(row=1, column=3, sticky="e")

        self._load_ratings()

    def _load_ratings(self) -> None:
        self.tree.delete(*self.tree.get_children())
        try:
            payload = self.app.client.list_ratings()
        except AubusClientError as e:
            self.app.show_error(f"Failed to load ratings: {e.code}")
            return

        for r in payload.get("ratings", []):
            stars = r["stars"]
            comment = r["comment"]
            from_who = f"{r.get('rater_name')} (#{r.get('rater_id')})"
            created = r["created_at"]
            self.tree.insert(
                "",
                "end",
                values=(f"{stars}★", comment, from_who, created),
            )

    def _rate(self) -> None:
        try:
            ratee_id = int(self.ratee_var.get())
            stars = int(self.stars_var.get())
        except ValueError:
            self.app.show_error("Ratee ID and stars must be numbers.")
            return
        comment = self.comment_var.get().strip()

        if not comment:
            self.app.show_error("Please provide a short comment.")
            return

        try:
            payload = self.app.client.rate_user(ratee_id, stars, comment)
        except AubusClientError as e:
            self.app.show_error(f"Could not submit rating: {e.code}")
            return

        # Update local user rating summary if ratee_id == current user?
        self.app.show_info("Rating submitted.")
        self.comment_var.set("")
        self._load_ratings()
