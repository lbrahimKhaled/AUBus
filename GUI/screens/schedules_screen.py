# GUI/screens/schedules_screen.py
import tkinter as tk
from tkinter import messagebox
from typing import Any, Dict, List


WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


class SchedulesScreen(tk.Frame):
    """
    Screen that shows the current user's schedules (for drivers)
    and allows adding/removing schedules.
    """

    def __init__(self, master, client, **kwargs):
        super().__init__(master, **kwargs)
        self.client = client
        self.configure(bg="#333333")

        self._schedules: List[Dict[str, Any]] = []

        self._build_widgets()
        self.refresh_schedules()

    def _build_widgets(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        card = tk.Frame(self, bg="#333333")
        card.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)

        title = tk.Label(
            card,
            text="My Schedules",
            font=("Arial", 18, "bold"),
            bg="#333333",
            fg="white",
        )
        title.grid(row=0, column=0, pady=(0, 10))

        # Listbox to show schedules
        self.listbox = tk.Listbox(card, width=60, height=10)
        self.listbox.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        # Buttons row
        btn_row = tk.Frame(card, bg="#333333")
        btn_row.grid(row=2, column=0, pady=(5, 0))

        btn_add = tk.Button(
            btn_row,
            text="Add schedule",
            command=self._on_add_clicked,
            highlightthickness=0,
            borderwidth=1,
            width=14,
        )
        btn_add.grid(row=0, column=0, padx=5)

        btn_delete = tk.Button(
            btn_row,
            text="Delete selected",
            command=self._on_delete_clicked,
            highlightthickness=0,
            borderwidth=1,
            width=14,
        )
        btn_delete.grid(row=0, column=1, padx=5)

        btn_refresh = tk.Button(
            btn_row,
            text="Refresh",
            command=self.refresh_schedules,
            highlightthickness=0,
            borderwidth=1,
            width=10,
        )
        btn_refresh.grid(row=0, column=2, padx=5)

        btn_back = tk.Button(
            card,
            text="Back to home",
            command=self._on_back_clicked,
            highlightthickness=0,
            borderwidth=1,
            width=14,
        )
        btn_back.grid(row=3, column=0, pady=(10, 0))

        self.label_status = tk.Label(
            card,
            text="",
            fg="#ffcccc",
            bg="#333333",
        )
        self.label_status.grid(row=4, column=0, pady=(5, 0))

    # ---- Data handling ----

    def refresh_schedules(self) -> None:
        """Fetch schedules from backend and update the listbox."""
        try:
            resp = self.client.list_schedules()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load schedules:\n{e}")
            return

        if resp["type"] != "list_schedules_ok":
            err = resp["payload"].get("error", "UNKNOWN_ERROR")
            self.label_status.config(text=f"Failed to list schedules: {err}")
            return

        self._schedules = resp["payload"].get("schedules", [])

        self.listbox.delete(0, tk.END)
        for sched in self._schedules:
            weekday_idx = sched.get("weekday", 0)
            weekday_name = WEEKDAYS[
                weekday_idx] if 0 <= weekday_idx < 7 else f"Day{weekday_idx}"
            depart_time = sched.get("depart_time", "?")
            direction = sched.get("direction", "?")
            sched_id = sched.get("id", "?")

            text = f"[id={sched_id}] {weekday_name} at {depart_time} ({direction})"
            self.listbox.insert(tk.END, text)

        if not self._schedules:
            self.label_status.config(
                text="No schedules yet. Click 'Add schedule' to create one.")
        else:
            self.label_status.config(text="")

    # ---- Button callbacks ----

    def _on_add_clicked(self) -> None:
        AddScheduleDialog(self, self.client)

    def _on_delete_clicked(self) -> None:
        selection = self.listbox.curselection()
        if not selection:
            self.label_status.config(text="Select a schedule to delete.")
            return

        index = selection[0]
        sched = self._schedules[index]
        sched_id = sched.get("id")

        if sched_id is None:
            self.label_status.config(
                text="Cannot delete: missing schedule id.")
            return

        if not messagebox.askyesno("Confirm delete", "Delete this schedule?"):
            return

        try:
            resp = self.client.delete_schedule(sched_id)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete schedule:\n{e}")
            return

        if resp["type"] != "delete_schedule_ok":
            err = resp["payload"].get("error", "DELETE_FAILED")
            self.label_status.config(text=f"Delete failed: {err}")
            return

        self.refresh_schedules()

    def _on_back_clicked(self) -> None:
        self.master.show_home_screen(self.master.current_user)
        # current_user is managed by App


class AddScheduleDialog(tk.Toplevel):
    """
    Popup dialog to add a new schedule.
    """

    def __init__(self, parent: SchedulesScreen, client, **kwargs):
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.client = client

        self.title("Add schedule")
        self.configure(bg="#333333")

        # Make it behave like a modal dialog
        self.transient(parent)
        self.grab_set()

        self._build_widgets()

        # Center over parent
        self.update_idletasks()
        x = parent.winfo_rootx() + parent.winfo_width() // 2 - self.winfo_width() // 2
        y = parent.winfo_rooty() + parent.winfo_height() // 2 - self.winfo_height() // 2
        self.geometry(f"+{x}+{y}")

    def _build_widgets(self) -> None:
        frame = tk.Frame(self, bg="#333333")
        frame.grid(row=0, column=0, padx=15, pady=15)

        # Weekday
        tk.Label(frame, text="Weekday:", bg="#333333", fg="white").grid(
            row=0, column=0, sticky="e", padx=5, pady=3
        )
        self.weekday_var = tk.StringVar(value=WEEKDAYS[0])
        weekday_menu = tk.OptionMenu(frame, self.weekday_var, *WEEKDAYS)
        weekday_menu.config(width=12)
        weekday_menu.grid(row=0, column=1, sticky="w", padx=5, pady=3)

        # Time
        tk.Label(frame, text="Time (HH:MM):", bg="#333333", fg="white").grid(
            row=1, column=0, sticky="e", padx=5, pady=3
        )
        self.time_entry = tk.Entry(frame, width=10)
        self.time_entry.grid(row=1, column=1, sticky="w", padx=5, pady=3)
        self.time_entry.insert(0, "07:30")

        # Direction
        tk.Label(frame, text="Direction:", bg="#333333", fg="white").grid(
            row=2, column=0, sticky="e", padx=5, pady=3
        )
        self.direction_var = tk.StringVar(value="toAUB")
        rb1 = tk.Radiobutton(
            frame,
            text="To AUB",
            variable=self.direction_var,
            value="toAUB",
            bg="#333333",
            fg="white",
            selectcolor="#333333",
        )
        rb2 = tk.Radiobutton(
            frame,
            text="From AUB",
            variable=self.direction_var,
            value="fromAUB",
            bg="#333333",
            fg="white",
            selectcolor="#333333",
        )
        rb1.grid(row=2, column=1, sticky="w", padx=5, pady=2)
        rb2.grid(row=3, column=1, sticky="w", padx=5, pady=2)

        # Buttons
        btn_row = tk.Frame(frame, bg="#333333")
        btn_row.grid(row=4, column=0, columnspan=2, pady=(10, 0))

        btn_save = tk.Button(
            btn_row,
            text="Save",
            command=self._on_save_clicked,
            highlightthickness=0,
            borderwidth=1,
            width=8,
        )
        btn_save.grid(row=0, column=0, padx=5)

        btn_cancel = tk.Button(
            btn_row,
            text="Cancel",
            command=self.destroy,
            highlightthickness=0,
            borderwidth=1,
            width=8,
        )
        btn_cancel.grid(row=0, column=1, padx=5)

        self.label_status = tk.Label(
            frame,
            text="",
            fg="#ffcccc",
            bg="#333333",
        )
        self.label_status.grid(row=5, column=0, columnspan=2, pady=(5, 0))

    def _on_save_clicked(self) -> None:
        weekday_name = self.weekday_var.get()
        time_str = self.time_entry.get().strip()
        direction = self.direction_var.get()

        if not time_str:
            self.label_status.config(text="Time is required.")
            return

        # Simple validation: HH:MM
        if len(time_str) != 5 or time_str[2] != ":":
            self.label_status.config(text="Time format must be HH:MM.")
            return

        try:
            hour = int(time_str[:2])
            minute = int(time_str[3:])
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError
        except ValueError:
            self.label_status.config(text="Invalid time.")
            return

        try:
            weekday_idx = WEEKDAYS.index(weekday_name)
        except ValueError:
            self.label_status.config(text="Invalid weekday.")
            return

        try:
            resp = self.client.add_schedule(
                weekday=weekday_idx,
                depart_time=time_str,
                direction=direction,
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add schedule:\n{e}")
            return

        if resp["type"] != "add_schedule_ok":
            err = resp["payload"].get("error", "ADD_FAILED")
            self.label_status.config(text=f"Add failed: {err}")
            return

        # Success: refresh list and close dialog
        self.parent.refresh_schedules()
        self.destroy()
