# GUI/screens/ride_request_screen.py
import tkinter as tk
from tkinter import messagebox
from typing import Any, Dict
from datetime import datetime

WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


class RideRequestScreen(tk.Frame):
    """
    Screen for riders to request a ride.

    Supports:
      - Instant request (uses current datetime)
      - Scheduled request (user enters date + time)
    """

    def __init__(self, master, client, **kwargs):
        super().__init__(master, **kwargs)
        self.client = client
        self.configure(bg="#333333")

        # We'll read user info from master.current_user
        self.user_info: Dict[str, Any] | None = getattr(
            master, "current_user", None)

        self._build_widgets()

    def _build_widgets(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        card = tk.Frame(self, bg="#333333")
        card.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=0)
        card.rowconfigure(1, weight=1)
        card.rowconfigure(2, weight=1)
        card.rowconfigure(3, weight=0)

        title = tk.Label(
            card,
            text="Request a Ride",
            font=("Arial", 18, "bold"),
            bg="#333333",
            fg="white",
        )
        title.grid(row=0, column=0, pady=(0, 15))

        # Show current user area (and allow changing)
        user_area = ""
        if self.user_info:
            user_area = self.user_info.get("area", "")

        area_frame = tk.Frame(card, bg="#333333")
        area_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        area_frame.columnconfigure(1, weight=1)

        tk.Label(
            area_frame,
            text="Your area:",
            bg="#333333",
            fg="white"
        ).grid(row=0, column=0, sticky="e", padx=5, pady=3)

        self.entry_area = tk.Entry(area_frame, width=30)
        self.entry_area.grid(row=0, column=1, sticky="w", padx=5, pady=3)
        self.entry_area.insert(0, user_area)

        # --- Instant request section ---
        instant_frame = tk.LabelFrame(
            card,
            text="Instant request (now)",
            bg="#333333",
            fg="white",
            labelanchor="n",
        )
        instant_frame.grid(row=2, column=0, sticky="ew",
                           pady=(5, 10), ipadx=5, ipady=5)
        instant_frame.columnconfigure(0, weight=1)
        instant_frame.columnconfigure(1, weight=1)

        tk.Label(
            instant_frame,
            text="Direction:",
            bg="#333333",
            fg="white",
        ).grid(row=0, column=0, sticky="e", padx=5, pady=3)

        self.instant_dir_var = tk.StringVar(value="toAUB")
        rb_to = tk.Radiobutton(
            instant_frame,
            text="To AUB",
            variable=self.instant_dir_var,
            value="toAUB",
            bg="#333333",
            fg="white",
            selectcolor="#333333",
        )
        rb_from = tk.Radiobutton(
            instant_frame,
            text="From AUB",
            variable=self.instant_dir_var,
            value="fromAUB",
            bg="#333333",
            fg="white",
            selectcolor="#333333",
        )
        rb_to.grid(row=0, column=1, sticky="w", padx=5, pady=3)
        rb_from.grid(row=1, column=1, sticky="w", padx=5, pady=3)

        btn_instant = tk.Button(
            instant_frame,
            text="Request now",
            command=self._on_instant_request,
            highlightthickness=0,
            borderwidth=1,
            width=14,
        )
        btn_instant.grid(row=2, column=0, columnspan=2, pady=(8, 3))

        # --- Scheduled request section ---
        sched_frame = tk.LabelFrame(
            card,
            text="Schedule for later",
            bg="#333333",
            fg="white",
            labelanchor="n",
        )
        sched_frame.grid(row=3, column=0, sticky="ew",
                         pady=(5, 10), ipadx=5, ipady=5)
        sched_frame.columnconfigure(1, weight=1)

        tk.Label(
            sched_frame,
            text="Weekday:",
            bg="#333333",
            fg="white",
        ).grid(row=0, column=0, sticky="e", padx=5, pady=3)

        self.sched_weekday_var = tk.StringVar(value=WEEKDAYS[0])
        weekday_menu = tk.OptionMenu(
            sched_frame,
            self.sched_weekday_var,
            *WEEKDAYS,
        )
        weekday_menu.config(bg="#444444", fg="white")
        weekday_menu.grid(row=0, column=1, sticky="w", padx=5, pady=3)

        tk.Label(
            sched_frame,
            text="Time (HH:MM):",
            bg="#333333",
            fg="white",
        ).grid(row=1, column=0, sticky="e", padx=5, pady=3)

        self.entry_time = tk.Entry(sched_frame, width=8)
        self.entry_time.grid(row=1, column=1, sticky="w", padx=5, pady=3)
        self.entry_time.insert(0, "08:00")

        tk.Label(
            sched_frame,
            text="Direction:",
            bg="#333333",
            fg="white",
        ).grid(row=2, column=0, sticky="e", padx=5, pady=3)

        self.sched_dir_var = tk.StringVar(value="toAUB")
        rb2_to = tk.Radiobutton(
            sched_frame,
            text="To AUB",
            variable=self.sched_dir_var,
            value="toAUB",
            bg="#333333",
            fg="white",
            selectcolor="#333333",
        )
        rb2_from = tk.Radiobutton(
            sched_frame,
            text="From AUB",
            variable=self.sched_dir_var,
            value="fromAUB",
            bg="#333333",
            fg="white",
            selectcolor="#333333",
        )
        rb2_to.grid(row=2, column=1, sticky="w", padx=5, pady=3)
        rb2_from.grid(row=3, column=1, sticky="w", padx=5, pady=3)

        btn_sched = tk.Button(
            sched_frame,
            text="Request for later",
            command=self._on_scheduled_request,
            highlightthickness=0,
            borderwidth=1,
            width=14,
        )
        btn_sched.grid(row=4, column=0, columnspan=2, pady=(8, 3))

        # Back + status
        bottom_frame = tk.Frame(card, bg="#333333")
        bottom_frame.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        bottom_frame.columnconfigure(0, weight=1)

        btn_back = tk.Button(
            bottom_frame,
            text="Back to home",
            command=self._on_back_clicked,
            highlightthickness=0,
            borderwidth=1,
            width=14,
        )
        btn_back.grid(row=0, column=0, pady=(0, 5))

        self.label_status = tk.Label(
            card,
            text="",
            fg="#ffcccc",
            bg="#333333",
        )
        self.label_status.grid(row=5, column=0, pady=(5, 0))

    # ---- Helper to call backend ----

    def _submit_request(self, area: str, weekday: int, target_time: str, direction: str) -> None:
        if not area.strip():
            self.label_status.config(text="Area is required.")
            return

        try:
            resp = self.client.post_ride_request(
                area=area.strip(),
                weekday=weekday,
                target_time=target_time,
                direction=direction,
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send request:\n{e}")
            return

        if resp.get("type") != "post_ride_request_ok":
            err = resp.get("payload", {}).get("error", "REQUEST_FAILED")
            self.label_status.config(text=f"Request failed: {err}")
            return

        payload = resp.get("payload", {})
        match = payload.get("match")

        if match:
            driver_name = match.get("driver_name", "a driver")
            depart_time = match.get("depart_time") or target_time
            self.label_status.config(
                text=f"Matched with {driver_name} at {depart_time}."
            )
        else:
            self.label_status.config(
                text="Request created. No driver matched yet; you'll be notified when one accepts."
            )

    # ---- Button callbacks ----

    def _on_instant_request(self) -> None:
        area = self.entry_area.get()
        direction = self.instant_dir_var.get()

        now = datetime.now()
        weekday = now.weekday()              # 0..6 (Mon=0)
        target_time = now.strftime("%H:%M")  # "HH:MM"

        self._submit_request(area, weekday, target_time, direction)

    def _on_scheduled_request(self) -> None:
        area = self.entry_area.get()
        direction = self.sched_dir_var.get()
        weekday_name = self.sched_weekday_var.get()
        time_str = self.entry_time.get().strip()

        if not time_str:
            self.label_status.config(text="Time is required.")
            return

        # Validate time format HH:MM
        try:
            hour = int(time_str[:2])
            minute = int(time_str[3:])
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError
        except ValueError:
            self.label_status.config(text="Invalid time.")
            return

        # Convert weekday name -> index 0..6
        try:
            weekday_idx = WEEKDAYS.index(weekday_name)
        except ValueError:
            self.label_status.config(text="Invalid weekday.")
            return

        target_time = time_str  # "HH:MM"
        self._submit_request(area, weekday_idx, target_time, direction)

    def _on_back_clicked(self) -> None:
        self.master.show_home_screen(self.master.current_user)
