# gui/screens/schedules_screen.py
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, List, Dict, Any

from .base import BaseScreen
from ..net import AubusClientError

if TYPE_CHECKING:
    from ..app import App


WEEKDAYS = [
    ("Monday", 0),
    ("Tuesday", 1),
    ("Wednesday", 2),
    ("Thursday", 3),
    ("Friday", 4),
    ("Saturday", 5),
    ("Sunday", 6),
]

DIRECTIONS = [
    ("To AUB", "toAUB"),
    ("From AUB", "fromAUB"),
]


class SchedulesScreen(BaseScreen):
    def __init__(self, master: tk.Widget, app: "App") -> None:
        super().__init__(master, app, title="My schedules")

        self.weekday_var = tk.StringVar(value=WEEKDAYS[0][0])
        self.time_var = tk.StringVar()
        self.direction_var = tk.StringVar(value=DIRECTIONS[0][0])

        # Form row
        form = ttk.Frame(self.body, style="Aubus.Card.TFrame")
        form.grid(row=1, column=0, sticky="ew", pady=(8, 12))
        form.columnconfigure(3, weight=1)

        ttk.Label(form, text="Weekday", style="Aubus.Body.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.weekday_cb = ttk.Combobox(
            form,
            textvariable=self.weekday_var,
            values=[w[0] for w in WEEKDAYS],
            state="readonly",
        )
        self.weekday_cb.grid(row=1, column=0, sticky="ew", padx=(0, 8))

        ttk.Label(form, text="Time (HH:MM)", style="Aubus.Body.TLabel").grid(
            row=0, column=1, sticky="w"
        )
        ttk.Entry(form, textvariable=self.time_var, style="Aubus.TEntry").grid(
            row=1, column=1, sticky="ew", padx=(0, 8)
        )

        ttk.Label(form, text="Direction", style="Aubus.Body.TLabel").grid(
            row=0, column=2, sticky="w"
        )
        self.dir_cb = ttk.Combobox(
            form,
            textvariable=self.direction_var,
            values=[d[0] for d in DIRECTIONS],
            state="readonly",
        )
        self.dir_cb.grid(row=1, column=2, sticky="ew", padx=(0, 8))

        ttk.Button(
            form,
            text="Add schedule",
            style="Aubus.Primary.TButton",
            command=self._on_add,
        ).grid(row=1, column=3, sticky="ew")

        # Table
        table_frame = ttk.Frame(self.body, style="Aubus.Card.TFrame")
        table_frame.grid(row=2, column=0, sticky="nsew")
        self.body.rowconfigure(2, weight=1)

        columns = ("weekday", "time", "direction")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="Aubus.Treeview",
            selectmode="browse",
        )
        self.tree.heading("weekday", text="Weekday")
        self.tree.heading("time", text="Time")
        self.tree.heading("direction", text="Direction")
        self.tree.column("weekday", width=120, anchor="center")
        self.tree.column("time", width=100, anchor="center")
        self.tree.column("direction", width=120, anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # Delete button
        ttk.Button(
            self.body,
            text="Delete selected",
            style="Aubus.Secondary.TButton",
            command=self._on_delete,
        ).grid(row=3, column=0, sticky="w", pady=(8, 0))

        self._load_schedules()

    # ---------- helpers ----------

    def _weekday_to_int(self, name: str) -> int:
        for label, idx in WEEKDAYS:
            if label == name:
                return idx
        return 0

    def _weekday_label(self, idx: int) -> str:
        for label, i in WEEKDAYS:
            if i == idx:
                return label
        return str(idx)

    def _direction_label(self, code: str) -> str:
        for label, c in DIRECTIONS:
            if c == code:
                return label
        return code

    def _load_schedules(self) -> None:
        self.tree.delete(*self.tree.get_children())
        try:
            payload = self.app.client.list_schedules()
        except AubusClientError as e:
            self.app.show_error(f"Failed to load schedules: {e.code}")
            return

        for sched in payload.get("schedules", []):
            sched_id = sched["id"]
            weekday_label = self._weekday_label(sched["weekday"])
            time_str = sched["depart_time"]
            direction_label = self._direction_label(sched["direction"])
            self.tree.insert(
                "",
                "end",
                iid=str(sched_id),
                values=(weekday_label, time_str, direction_label),
            )

    # ---------- actions ----------

    def _on_add(self) -> None:
        weekday = self._weekday_to_int(self.weekday_var.get())
        time_str = self.time_var.get().strip()
        dir_label = self.direction_var.get()
        direction_code = next(
            (code for label, code in DIRECTIONS if label == dir_label),
            "toAUB",
        )

        if not time_str:
            self.app.show_error("Please enter a time (HH:MM).")
            return

        try:
            self.app.client.add_schedule(weekday, time_str, direction_code)
        except AubusClientError as e:
            self.app.show_error(f"Failed to add schedule: {e.code}")
            return

        self.time_var.set("")
        self._load_schedules()

    def _on_delete(self) -> None:
        sel = self.tree.selection()
        if not sel:
            self.app.show_error("Select a schedule to delete.")
            return
        sched_id = int(sel[0])

        try:
            self.app.client.delete_schedule(sched_id)
        except AubusClientError as e:
            self.app.show_error(f"Failed to delete: {e.code}")
            return

        self._load_schedules()
