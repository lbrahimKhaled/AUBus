# GUI/screens/ratings_screen.py
import tkinter as tk
from tkinter import messagebox
from typing import Any, Dict, List


class RatingsScreen(tk.Frame):
    """
    Screen to view your received ratings and rate other users.

    Uses:
      - client.list_ratings()
      - client.rate_user(ratee_id, stars, comment)
    """

    def __init__(self, master, client, **kwargs):
        super().__init__(master, **kwargs)
        self.client = client
        self.configure(bg="#333333")

        self.user_info: Dict[str, Any] | None = getattr(
            master, "current_user", None)
        self._ratings: List[Dict[str, Any]] = []

        self._build_widgets()
        self.refresh_ratings()

    def _build_widgets(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        card = tk.Frame(self, bg="#333333")
        card.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)

        title = tk.Label(
            card,
            text="Ratings",
            font=("Arial", 18, "bold"),
            bg="#333333",
            fg="white",
        )
        title.grid(row=0, column=0, pady=(0, 10))

        # --- Top: summary + list of received ratings ---

        top_frame = tk.Frame(card, bg="#333333")
        top_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        top_frame.columnconfigure(0, weight=1)
        top_frame.rowconfigure(1, weight=1)

        self.label_summary = tk.Label(
            top_frame,
            text="",
            bg="#333333",
            fg="#cccccc",
            font=("Arial", 11),
        )
        self.label_summary.grid(row=0, column=0, sticky="w", pady=(0, 5))

        self.listbox = tk.Listbox(top_frame, width=70, height=8)
        self.listbox.grid(row=1, column=0, sticky="nsew")

        # --- Middle: rate someone manually ---

        sep = tk.Frame(card, bg="#555555", height=1)
        sep.grid(row=2, column=0, sticky="ew", pady=(5, 5))

        rate_frame = tk.Frame(card, bg="#333333")
        rate_frame.grid(row=3, column=0, sticky="ew", pady=(5, 5))
        rate_frame.columnconfigure(1, weight=1)

        tk.Label(
            rate_frame,
            text="Rate user by ID:",
            bg="#333333",
            fg="white",
        ).grid(row=0, column=0, sticky="e", padx=5, pady=3)

        self.entry_ratee = tk.Entry(rate_frame, width=8)
        self.entry_ratee.grid(row=0, column=1, sticky="w", padx=5, pady=3)

        tk.Label(
            rate_frame,
            text="Stars (1–5):",
            bg="#333333",
            fg="white",
        ).grid(row=1, column=0, sticky="e", padx=5, pady=3)

        self.entry_stars = tk.Entry(rate_frame, width=4)
        self.entry_stars.grid(row=1, column=1, sticky="w", padx=5, pady=3)
        self.entry_stars.insert(0, "5")

        tk.Label(
            rate_frame,
            text="Comment:",
            bg="#333333",
            fg="white",
        ).grid(row=2, column=0, sticky="ne", padx=5, pady=3)

        self.entry_comment = tk.Text(rate_frame, width=40, height=3)
        self.entry_comment.grid(row=2, column=1, sticky="w", padx=5, pady=3)

        btn_rate = tk.Button(
            rate_frame,
            text="Submit rating",
            command=self._on_rate_clicked,
            highlightthickness=0,
            borderwidth=1,
            width=14,
        )
        btn_rate.grid(row=3, column=0, columnspan=2, pady=(5, 0))

        # --- Bottom: back + status ---

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

    # ---- Backend interactions ----

    def refresh_ratings(self) -> None:
        """Fetch ratings from backend and update UI."""
        try:
            resp = self.client.list_ratings()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load ratings:\n{e}")
            return

        if resp["type"] != "list_ratings_ok":
            err = resp["payload"].get("error", "UNKNOWN_ERROR")
            self.label_status.config(text=f"Failed to list ratings: {err}")
            return

        payload = resp["payload"]
        self._ratings = payload.get("ratings", [])

        avg = payload.get("avg_stars")
        count = payload.get("count", len(self._ratings))

        if count and avg is not None:
            self.label_summary.config(
                text=f"Your rating: {avg:.1f} stars over {count} rating(s)"
            )
        else:
            self.label_summary.config(text="You have no ratings yet.")

        self.listbox.delete(0, tk.END)

        for r in self._ratings:
            stars = r.get("stars", "?")
            comment = r.get("comment", "")
            rater_id = r.get("rater_id", "?")
            created_at = r.get("created_at", "")

            text = f"[{stars}★] from user {rater_id} — {comment} ({created_at})"
            self.listbox.insert(tk.END, text)

    def _on_rate_clicked(self) -> None:
        ratee_str = self.entry_ratee.get().strip()
        stars_str = self.entry_stars.get().strip()
        comment = self.entry_comment.get("1.0", "end").strip()

        if not ratee_str or not stars_str:
            self.label_status.config(text="Please fill user ID and stars.")
            return

        try:
            ratee_id = int(ratee_str)
        except ValueError:
            self.label_status.config(text="User ID must be a number.")
            return

        try:
            stars = int(stars_str)
        except ValueError:
            self.label_status.config(
                text="Stars must be a number between 1 and 5.")
            return

        if not (1 <= stars <= 5):
            self.label_status.config(text="Stars must be between 1 and 5.")
            return

        try:
            resp = self.client.rate_user(
                ratee_id=ratee_id, stars=stars, comment=comment)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to submit rating:\n{e}")
            return

        if resp["type"] != "rate_user_ok":
            err = resp["payload"].get("error", "RATE_FAILED")
            self.label_status.config(text=f"Rating failed: {err}")
            return

        messagebox.showinfo("Rating submitted",
                            "Your rating has been recorded.")
        self.entry_comment.delete("1.0", "end")
        self.label_status.config(text="")
        # Refresh your own received ratings – in a real app you'd usually rate after a ride
        self.refresh_ratings()

    def _on_back_clicked(self) -> None:
        self.master.show_home_screen(self.master.current_user)
