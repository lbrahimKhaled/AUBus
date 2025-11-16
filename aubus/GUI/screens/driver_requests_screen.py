# gui/screens/driver_requests_screen.py
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from .base import BaseScreen
from ..net import AubusClientError

if TYPE_CHECKING:
    from ..app import App


class DriverRequestsScreen(BaseScreen):
    def __init__(self, master: tk.Widget, app: "App") -> None:
        super().__init__(master, app, title="Incoming rider requests")

        table_frame = ttk.Frame(self.body, style="Aubus.Card.TFrame")
        table_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.body.rowconfigure(1, weight=1)

        columns = ("id", "rider", "area", "time", "direction", "status")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="Aubus.Treeview",
            selectmode="browse",
        )
        for col, width in [
            ("id", 60),
            ("rider", 160),
            ("area", 140),
            ("time", 120),
            ("direction", 110),
            ("status", 110),
        ]:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=width, anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # Buttons
        btns = ttk.Frame(self.body, style="Aubus.Card.TFrame")
        btns.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        ttk.Button(
            btns,
            text="Accept",
            style="Aubus.Primary.TButton",
            command=self._accept,
        ).grid(row=0, column=0, padx=(0, 8))

        ttk.Button(
            btns,
            text="Decline",
            style="Aubus.Secondary.TButton",
            command=self._decline,
        ).grid(row=0, column=1, padx=(0, 8))

        ttk.Button(
            btns,
            text="Open chat",
            style="Aubus.Secondary.TButton",
            command=self._open_chat,
        ).grid(row=0, column=2, padx=(0, 8))

        ttk.Button(
            btns,
            text="Refresh",
            style="Aubus.Secondary.TButton",
            command=self._load_requests,
        ).grid(row=0, column=3)

        self._load_requests()

    def _load_requests(self) -> None:
        self.tree.delete(*self.tree.get_children())
        try:
            payload = self.app.client.list_driver_requests()
        except AubusClientError as e:
            self.app.show_error(f"Failed to load driver requests: {e.code}")
            return

        for req in payload.get("requests", []):
            req_id = req["id"]
            area = req["area"]
            time_str = req["target_time"]
            direction = req["direction"]
            status = req["status"]
            rider_name = req.get("rider_name") or "-"
            self.tree.insert(
                "",
                "end",
                iid=str(req_id),
                values=(req_id, rider_name, area, time_str, direction, status),
            )

    def _selected_request_id(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            self.app.show_error("Select a request first.")
            return None
        return int(sel[0])

    def _accept(self) -> None:
        req_id = self._selected_request_id()
        if req_id is None:
            return

        try:
            self.app.client.driver_accept(req_id)
        except AubusClientError as e:
            self.app.show_error(f"Could not accept request: {e.code}")
            return

        self._load_requests()

    def _decline(self) -> None:
        req_id = self._selected_request_id()
        if req_id is None:
            return

        try:
            self.app.client.driver_decline(req_id)
        except AubusClientError as e:
            self.app.show_error(f"Could not decline request: {e.code}")
            return

        self._load_requests()

    def _open_chat(self) -> None:
        req_id = self._selected_request_id()
        if req_id is None:
            return
        channel_id = str(req_id)
        self.app.show_chat_screen(
            channel_id=channel_id,
            title=f"Ride #{req_id} chat",
        )
