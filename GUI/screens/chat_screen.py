# GUI/screens/chat_screen.py
import tkinter as tk
from tkinter import messagebox
from typing import Any, Dict, List
from datetime import datetime


class ChatScreen(tk.Frame):
    """
    Simple chat screen using the relay backend.

    Uses:
      - client.relay_send(channel_id, text)
      - client.relay_poll(channel_id, last_seq)

    The App must set:
      - master.chat_channel_id
      - master.chat_title (optional)
      - master.current_user (from login)
    before calling show_chat_screen().
    """

    POLL_INTERVAL_MS = 1500  # 1.5 seconds

    def __init__(self, master, client, **kwargs):
        super().__init__(master, **kwargs)
        self.client = client
        self.configure(bg="#333333")

        # Channel info from App
        self.channel_id: str = getattr(
            master, "chat_channel_id", "") or "unknown"
        self.chat_title: str = getattr(
            master, "chat_title", "") or f"Channel: {self.channel_id}"

        # User info to show "You" vs "User <id>"
        self.user_info: Dict[str, Any] | None = getattr(
            master, "current_user", None)
        self.user_id = None
        if self.user_info is not None:
            self.user_id = self.user_info.get("id")

        self.last_seq: int = 0
        self._polling_active: bool = True

        self._build_widgets()
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
            text=self.chat_title,
            font=("Arial", 16, "bold"),
            bg="#333333",
            fg="white",
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 5))

        subtitle = tk.Label(
            card,
            text=f"Channel ID: {self.channel_id}",
            font=("Arial", 10),
            bg="#333333",
            fg="#cccccc",
        )
        subtitle.grid(row=0, column=0, sticky="e", pady=(0, 5))

        # Messages area (Text widget)
        self.text_area = tk.Text(
            card,
            width=70,
            height=15,
            state="disabled",
            bg="#222222",
            fg="white",
            wrap="word",
        )
        self.text_area.grid(row=1, column=0, sticky="nsew", pady=(5, 5))

        # Input row
        input_frame = tk.Frame(card, bg="#333333")
        input_frame.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        input_frame.columnconfigure(0, weight=1)

        self.entry_msg = tk.Entry(input_frame)
        self.entry_msg.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.entry_msg.bind("<Return>", lambda event: self._on_send_clicked())

        btn_send = tk.Button(
            input_frame,
            text="Send",
            command=self._on_send_clicked,
            highlightthickness=0,
            borderwidth=1,
            width=8,
        )
        btn_send.grid(row=0, column=1)

        # Bottom row: back + status
        bottom_frame = tk.Frame(card, bg="#333333")
        bottom_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
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
        self.label_status.grid(row=4, column=0, pady=(5, 0))

    # ---- Message display helpers ----

    def _append_message(self, sender_id: int, text: str, timestamp: str) -> None:
        # Decide label for sender
        if self.user_id is not None and sender_id == self.user_id:
            sender_label = "You"
        else:
            sender_label = f"User {sender_id}"

        # Simple time formatting
        try:
            dt = datetime.fromisoformat(timestamp)
            time_str = dt.strftime("%H:%M")
        except Exception:
            time_str = timestamp

        line = f"[{time_str}] {sender_label}: {text}\n"

        self.text_area.configure(state="normal")
        self.text_area.insert("end", line)
        self.text_area.see("end")
        self.text_area.configure(state="disabled")

    # ---- Polling loop ----

    def _poll_loop(self) -> None:
        if not self._polling_active:
            return

        # If this widget has been destroyed, don't continue
        if not self.winfo_exists():
            return

        try:
            resp = self.client.relay_poll(self.channel_id, self.last_seq)
        except Exception:
            # Don't spam errors; just show one line and continue
            self.label_status.config(text="Warning: failed to poll messages.")
        else:
            if resp["type"] == "relay_poll_ok":
                msgs = resp["payload"].get("messages", [])
                for msg in msgs:
                    seq = msg.get("seq", 0)
                    sender_id = msg.get("sender_id", -1)
                    text = msg.get("text", "")
                    timestamp = msg.get("timestamp", "")
                    self._append_message(sender_id, text, timestamp)
                    if seq > self.last_seq:
                        self.last_seq = seq

        # Schedule next poll
        self.after(self.POLL_INTERVAL_MS, self._poll_loop)

    # ---- Button callbacks ----

    def _on_send_clicked(self) -> None:
        text = self.entry_msg.get().strip()
        if not text:
            return

        try:
            resp = self.client.relay_send(self.channel_id, text)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send message:\n{e}")
            return

        if resp["type"] != "relay_send_ok":
            err = resp["payload"].get("error", "SEND_FAILED")
            self.label_status.config(text=f"Send failed: {err}")
            return

        # Server accepted message; we can optimistically show it
        msg = resp["payload"].get("message", {})
        seq = msg.get("seq", 0)
        sender_id = msg.get("sender_id", self.user_id or -1)
        timestamp = msg.get(
            "timestamp", datetime.now().isoformat(timespec="minutes"))

        self._append_message(sender_id, text, timestamp)
        if seq > self.last_seq:
            self.last_seq = seq

        self.entry_msg.delete(0, tk.END)
        self.label_status.config(text="")

    def _on_back_clicked(self) -> None:
        self._polling_active = False
        self.master.show_home_screen(self.master.current_user)
