# gui/screens/rider_requests_screen.py
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from .base import BaseScreen
from ..net import AubusClientError

if TYPE_CHECKING:
    from ..app import App


class RiderRequestsScreen(BaseScreen):
    def __init__(self, master: tk.Widget, app: "App") -> None:
        super().__init__(master, app, title="My ride requests")

        table_frame = ttk.Frame(self.body, style="Aubus.Card.TFrame")
        table_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.body.rowconfigure(1, weight=1)

        # Extra hidden column "driver_id" so we know who to rate
        columns = ("id", "area", "time", "direction",
                   "status", "driver", "driver_id")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="Aubus.Treeview",
            selectmode="browse",
        )

        # Visible columns
        self.tree.heading("id", text="ID")
        self.tree.heading("area", text="Area")
        self.tree.heading("time", text="Time")
        self.tree.heading("direction", text="Direction")
        self.tree.heading("status", text="Status")
        self.tree.heading("driver", text="Driver")

        self.tree.column("id", width=60, anchor="center")
        self.tree.column("area", width=140, anchor="center")
        self.tree.column("time", width=120, anchor="center")
        self.tree.column("direction", width=110, anchor="center")
        self.tree.column("status", width=110, anchor="center")
        self.tree.column("driver", width=160, anchor="center")

        # Hidden driver_id column
        self.tree.heading("driver_id", text="")
        self.tree.column("driver_id", width=0, stretch=False, anchor="center")

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
            text="Open chat for selected",
            style="Aubus.Secondary.TButton",
            command=self._open_chat,
        ).grid(row=0, column=0, sticky="w")

        ttk.Button(
            btns,
            text="Rate selected driver",
            style="Aubus.Primary.TButton",
            command=self._rate_driver,
        ).grid(row=0, column=1, sticky="w", padx=(8, 0))

        ttk.Button(
            btns,
            text="Refresh",
            style="Aubus.Secondary.TButton",
            command=self._load_requests,
        ).grid(row=0, column=2, sticky="w", padx=(8, 0))

        self._load_requests()

    def _load_requests(self) -> None:
        self.tree.delete(*self.tree.get_children())
        try:
            payload = self.app.client.list_my_requests()
        except AubusClientError as e:
            self.app.show_error(f"Failed to load requests: {e.code}")
            return

        for req in payload.get("requests", []):
            req_id = req["id"]
            area = req["area"]
            time_str = req["target_time"]
            direction = req["direction"]
            status = req["status"]
            driver_name = req.get("driver_name") or "-"
            # expected from backend; may be None
            driver_id = req.get("driver_id")

            self.tree.insert(
                "",
                "end",
                iid=str(req_id),
                values=(req_id, area, time_str, direction,
                        status, driver_name, driver_id),
            )

    def _open_chat(self) -> None:
        sel = self.tree.selection()
        if not sel:
            self.app.show_error("Select a request first.")
            return
        req_id = int(sel[0])
        channel_id = str(req_id)  # convention used in backend comments
        self.app.show_chat_screen(
            channel_id=channel_id,
            title=f"Ride #{req_id} chat",
        )

    # ---------- quick rating from a ride ----------

    def _rate_driver(self) -> None:
        sel = self.tree.selection()
        if not sel:
            self.app.show_error("Select a completed ride first.")
            return

        item_id = sel[0]
        values = self.tree.item(item_id, "values")

        # values order: (id, area, time, direction, status, driver, driver_id)
        status = values[4]
        driver_name = values[5]
        driver_id_raw = values[6]

        if not driver_id_raw or driver_id_raw in ("", "None"):
            self.app.show_error(
                "This ride has no assigned driver yet to rate.")
            return

        try:
            driver_id = int(driver_id_raw)
        except ValueError:
            self.app.show_error("Could not determine driver ID for this ride.")
            return

        # Optional: only allow rating when ride is completed/accepted
        # tweak this check based on your actual status values
        if status.upper() not in ("ACCEPTED", "COMPLETED", "DONE", "FINISHED"):
            # You can relax this if you want
            self.app.show_error(
                "You can only rate a driver after the ride is accepted / completed.")
            return

        self._open_rating_dialog(driver_id, driver_name)

    def _open_rating_dialog(self, driver_id: int, driver_name: str) -> None:
        top = tk.Toplevel(self)
        top.title("Rate your driver")
        top.configure(bg="#020617")
        top.transient(self)
        top.grab_set()

        frame = ttk.Frame(top, style="Aubus.Card.TFrame", padding=16)
        frame.grid(row=0, column=0, sticky="nsew")
        top.columnconfigure(0, weight=1)
        top.rowconfigure(0, weight=1)

        ttk.Label(
            frame,
            text=f"Rate driver: {driver_name} (ID #{driver_id})",
            style="Aubus.Body.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ttk.Label(frame, text="Stars (1–5)", style="Aubus.Muted.TLabel").grid(
            row=1, column=0, sticky="w"
        )
        stars_var = tk.StringVar(value="5")
        stars_entry = ttk.Entry(
            frame, textvariable=stars_var, width=4, style="Aubus.TEntry")
        stars_entry.grid(row=1, column=1, sticky="w")

        ttk.Label(frame, text="Comment", style="Aubus.Muted.TLabel").grid(
            row=2, column=0, sticky="w", pady=(8, 2)
        )
        comment_var = tk.StringVar()
        comment_entry = ttk.Entry(
            frame, textvariable=comment_var, style="Aubus.TEntry")
        comment_entry.grid(row=3, column=0, columnspan=2, sticky="ew")

        btns = ttk.Frame(frame, style="Aubus.Card.TFrame")
        btns.grid(row=4, column=0, columnspan=2, sticky="e", pady=(10, 0))

        def submit() -> None:
            try:
                stars = int(stars_var.get())
            except ValueError:
                self.app.show_error("Stars must be a number between 1 and 5.")
                return

            if stars < 1 or stars > 5:
                self.app.show_error("Stars must be between 1 and 5.")
                return

            comment = comment_var.get().strip()
            if not comment:
                self.app.show_error("Please add a short comment.")
                return

            try:
                self.app.client.rate_user(driver_id, stars, comment)
            except AubusClientError as e:
                self.app.show_error(f"Could not submit rating: {e.code}")
                return

            self.app.show_info("Rating submitted. Thank you!")
            top.destroy()

        ttk.Button(
            btns,
            text="Cancel",
            style="Aubus.Secondary.TButton",
            command=top.destroy,
        ).grid(row=0, column=0, padx=(0, 8))

        ttk.Button(
            btns,
            text="Submit rating",
            style="Aubus.Primary.TButton",
            command=submit,
        ).grid(row=0, column=1)

        stars_entry.focus_set()
