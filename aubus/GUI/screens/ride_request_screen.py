# gui/screens/ride_request_screen.py
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from .base import BaseScreen
from ..net import AubusClientError
from .schedules_screen import WEEKDAYS, DIRECTIONS  # reuse

if TYPE_CHECKING:
    from ..app import App


AREAS_PRESETS = [
    "Hamra",
    "Tayouneh",
    "Hazmieh",
    "Jnah",
    "Dekwaneh",
    "Other",
]


class RideRequestScreen(BaseScreen):
    def __init__(self, master: tk.Widget, app: "App") -> None:
        super().__init__(master, app, title="Request a ride")

        self.area_var = tk.StringVar(value=AREAS_PRESETS[0])
        self.weekday_var = tk.StringVar(value=WEEKDAYS[0][0])
        self.time_var = tk.StringVar()
        self.direction_var = tk.StringVar(value=DIRECTIONS[0][0])

        form = ttk.Frame(self.body, style="Aubus.Card.TFrame")
        form.grid(row=1, column=0, sticky="ew", pady=(8, 4))
        form.columnconfigure(1, weight=1)

        row = 0

        def add_row(label: str, widget: tk.Widget):
            nonlocal row
            ttk.Label(form, text=label, style="Aubus.Body.TLabel").grid(
                row=row, column=0, sticky="w", pady=(6, 2)
            )
            widget.grid(row=row + 1, column=0, columnspan=2, sticky="ew")
            row += 2

        area_cb = ttk.Combobox(
            form, textvariable=self.area_var, values=AREAS_PRESETS, state="readonly"
        )
        add_row("Area", area_cb)

        weekday_cb = ttk.Combobox(
            form,
            textvariable=self.weekday_var,
            values=[w[0] for w in WEEKDAYS],
            state="readonly",
        )
        add_row("Weekday", weekday_cb)

        time_entry = ttk.Entry(
            form, textvariable=self.time_var, style="Aubus.TEntry")
        add_row("Target time (HH:MM)", time_entry)

        direction_cb = ttk.Combobox(
            form,
            textvariable=self.direction_var,
            values=[d[0] for d in DIRECTIONS],
            state="readonly",
        )
        add_row("Direction", direction_cb)

        ttk.Button(
            form,
            text="Post ride request",
            style="Aubus.Primary.TButton",
            command=self._on_post,
        ).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        self.feedback_label = ttk.Label(
            self.body,
            text="",
            style="Aubus.Muted.TLabel",
        )
        self.feedback_label.grid(row=2, column=0, sticky="w", pady=(8, 0))

    def _weekday_to_int(self, name: str) -> int:
        for label, idx in WEEKDAYS:
            if label == name:
                return idx
        return 0

    def _direction_code(self, label: str) -> str:
        for lab, code in DIRECTIONS:
            if lab == label:
                return code
        return "toAUB"

    def _on_post(self) -> None:
        area = self.area_var.get().strip()
        weekday = self._weekday_to_int(self.weekday_var.get())
        time_str = self.time_var.get().strip()
        direction = self._direction_code(self.direction_var.get())

        if not time_str:
            self.app.show_error("Please provide a target time (HH:MM).")
            return

        try:
            payload = self.app.client.post_ride_request(
                area=area,
                weekday=weekday,
                target_time=time_str,
                direction=direction,
            )
        except AubusClientError as e:
            msg = "Matching failed. Try adjusting time or area." if e.code == "MATCHING_FAILED" else f"Could not post request: {e.code}"
            self.app.show_error(msg)
            return

        req_id = payload.get("ride_request_id")
        candidates = payload.get("candidates", [])
        msg = f"Ride request #{req_id} created. Found {len(candidates)} candidate driver(s)."
        self.feedback_label.config(text=msg)
        self.time_var.set("")
