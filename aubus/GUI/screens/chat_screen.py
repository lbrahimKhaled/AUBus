# gui/screens/chat_screen.py
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from .base import BaseScreen
from ..net import AubusClientError

if TYPE_CHECKING:
    from ..app import App


class ChatScreen(BaseScreen):
    POLL_INTERVAL_MS = 1500

    def __init__(
        self,
        master: tk.Widget,
        app: "App",
        channel_id: str,
        chat_title: str | None = None,
    ) -> None:
        title = chat_title or f"Chat – channel {channel_id}"
        super().__init__(master, app, title=title)

        self.channel_id = channel_id
        self.last_seq = 0

        # Chat layout
        self.body.rowconfigure(1, weight=1)

        chat_frame = ttk.Frame(self.body, style="Aubus.Card.TFrame")
        chat_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 8))
        chat_frame.rowconfigure(0, weight=1)
        chat_frame.columnconfigure(0, weight=1)

        self.text = tk.Text(
            chat_frame,
            height=16,
            wrap="word",
            bg="#020617",
            fg="#e5e7eb",
            insertbackground="#e5e7eb",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#1f2937",
        )
        vsb = ttk.Scrollbar(chat_frame, orient="vertical",
                            command=self.text.yview)
        self.text.configure(yscrollcommand=vsb.set)

        self.text.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # Input row
        input_frame = ttk.Frame(self.body, style="Aubus.Card.TFrame")
        input_frame.grid(row=2, column=0, sticky="ew")
        input_frame.columnconfigure(0, weight=1)

        self.entry_var = tk.StringVar()
        entry = ttk.Entry(
            input_frame, textvariable=self.entry_var, style="Aubus.TEntry")
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=(4, 4))
        entry.bind("<Return>", lambda e: self._send())

        btn_send = ttk.Button(
            input_frame,
            text="Send",
            style="Aubus.Primary.TButton",
            command=self._send,
        )
        btn_send.grid(row=0, column=1, sticky="e", pady=(4, 4))

        self.after(self.POLL_INTERVAL_MS, self._poll)

    # ---------- helpers ----------

    def _append_message(self, sender: str, text: str, timestamp: str | None = None) -> None:
        ts = f"[{timestamp}] " if timestamp else ""
        line = f"{ts}{sender}: {text}\n"
        self.text.insert("end", line)
        self.text.see("end")

    def _poll(self) -> None:
        if not self.winfo_exists():
            return
        try:
            payload = self.app.client.relay_poll(
                self.channel_id, self.last_seq)
        except AubusClientError:
            # don't spam user; just stop polling silently
            return

        for msg in payload.get("messages", []):
            self.last_seq = max(self.last_seq, msg.get("seq", self.last_seq))
            sender_id = msg.get("sender_id", "?")
            ts = msg.get("timestamp")
            text = msg.get("text", "")
            self._append_message(f"User {sender_id}", text, ts)

        self.after(self.POLL_INTERVAL_MS, self._poll)

    def _send(self) -> None:
        text = self.entry_var.get().strip()
        if not text:
            return
        try:
            self.app.client.relay_send(self.channel_id, text)
        except AubusClientError as e:
            self.app.show_error(f"Could not send message: {e.code}")
            return
        self.entry_var.set("")
