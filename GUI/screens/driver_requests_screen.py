# GUI/screens/driver_requests_screen.py
import tkinter as tk
from tkinter import messagebox
from typing import Any, Dict, List


class DriverRequestsScreen(tk.Frame):
    """
    Shows incoming ride requests for the logged-in driver
    and allows accepting or declining them.
    """

    POLL_INTERVAL_MS = 3000  # 3 seconds

    def __init__(self, master, client, **kwargs):
        super().__init__(master, **kwargs)
        self.client = client
        self.configure(bg="#333333")

        self.user_info: Dict[str, Any] | None = getattr(
            master, "current_user", None)
        self._requests: List[Dict[str, Any]] = []
        self._polling_active = True

        self._build_widgets()
        self.refresh_requests()
        self.after(self.POLL_INTERVAL_MS, self._poll_loop)

    def _build_widgets(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        card = tk.Frame(self, bg="#333333")
        card.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)

        title = tk.Label(
            card,
            text="Incoming Ride Requests",
            font=("Arial", 18, "bold"),
            bg="#333333",
            fg="white",
        )
        title.grid(row=0, column=0, pady=(0, 10))

        self.listbox = tk.Listbox(card, width=80, height=10)
        self.listbox.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        btn_row = tk.Frame(card, bg="#333333")
        btn_row.grid(row=2, column=0, pady=(5, 0))

        btn_accept = tk.Button(
            btn_row,
            text="Accept",
            command=self._on_accept_clicked,
            highlightthickness=0,
            borderwidth=1,
            width=10,
        )
        btn_accept.grid(row=0, column=0, padx=5)

        btn_decline = tk.Button(
            btn_row,
            text="Decline",
            command=self._on_decline_clicked,
            highlightthickness=0,
            borderwidth=1,
            width=10,
        )
        btn_decline.grid(row=0, column=1, padx=5)

        btn_refresh = tk.Button(
            btn_row,
            text="Refresh",
            command=self.refresh_requests,
            highlightthickness=0,
            borderwidth=1,
            width=10,
        )
        btn_refresh.grid(row=0, column=2, padx=5)

        btn_back = tk.Button(
            btn_row,
            text="Back to home",
            command=self._on_back_clicked,
            highlightthickness=0,
            borderwidth=1,
            width=14,
        )
        btn_back.grid(row=0, column=3, padx=5)

        self.label_status = tk.Label(
            card,
            text="",
            fg="#ffcccc",
            bg="#333333",
        )
        self.label_status.grid(row=3, column=0, pady=(5, 0))

    def refresh_requests(self) -> None:
        try:
            resp = self.client.list_driver_requests()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load requests:\n{e}")
            return

        if resp["type"] != "list_driver_requests_ok":
            err = resp["payload"].get("error", "UNKNOWN_ERROR")
            self.label_status.config(text=f"Failed to list requests: {err}")
            return

        self._requests = resp["payload"].get("requests", [])

        self.listbox.delete(0, tk.END)
        if not self._requests:
            self.label_status.config(text="No incoming requests right now.")
            return
        else:
            self.label_status.config(text="")

        for r in self._requests:
            req_id = r.get("id", "?")
            rider_name = r.get("rider_name", "Unknown rider")
            area = r.get("area", "?")
            when = r.get("target_time", "?")
            direction = r.get("direction", "?")
            status = r.get("status", "pending")

            line = f"[id={req_id}] {when} ({direction}) — {rider_name} from {area}, status: {status}"
            self.listbox.insert(tk.END, line)

    def _get_selected_request(self) -> Dict[str, Any] | None:
        selection = self.listbox.curselection()
        if not selection:
            self.label_status.config(text="Select a request first.")
            return None
        index = selection[0]
        return self._requests[index]

    def _on_accept_clicked(self) -> None:
        req = self._get_selected_request()
        if not req:
            return
        req_id = req.get("id")
        if req_id is None:
            self.label_status.config(text="Missing request id.")
            return

        try:
            resp = self.client.driver_accept(req_id)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to accept request:\n{e}")
            return

        if resp["type"] != "driver_accept_ok":
            err = resp["payload"].get("error", "ACCEPT_FAILED")
            self.label_status.config(text=f"Accept failed: {err}")
            return

        self.refresh_requests()

    def _on_decline_clicked(self) -> None:
        req = self._get_selected_request()
        if not req:
            return
        req_id = req.get("id")
        if req_id is None:
            self.label_status.config(text="Missing request id.")
            return

        try:
            resp = self.client.driver_decline(req_id)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to decline request:\n{e}")
            return

        if resp["type"] != "driver_decline_ok":
            err = resp["payload"].get("error", "DECLINE_FAILED")
            self.label_status.config(text=f"Decline failed: {err}")
            return

        self.refresh_requests()

    def _poll_loop(self) -> None:
        if not self._polling_active or not self.winfo_exists():
            return
        self.refresh_requests()
        self.after(self.POLL_INTERVAL_MS, self._poll_loop)

    def _on_back_clicked(self) -> None:
        self._polling_active = False
        self.master.show_home_screen(self.master.current_user)
