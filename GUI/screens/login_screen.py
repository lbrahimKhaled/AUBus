import tkinter as tk
from tkinter import messagebox
from typing import Any, Dict


class LoginScreen(tk.Frame):
    """
    Simple login form.

    Uses AubusClient (passed from App) to call backend.login().
    On success, it asks the App to switch to the HomeScreen.
    """

    def __init__(self, master, client, **kwargs):
        super().__init__(master, **kwargs)

        # Optional: match dark background if you like
        self.configure(bg="#333333")

        self.client = client  # AubusClient instance from App

        self._build_widgets()

    def _build_widgets(self) -> None:
        # This outer frame fills the window
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Inner "card" frame that is centered
        card = tk.Frame(self, bg="#333333")
        card.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=2)

        # Add some empty rows top/bottom to center vertically
        for r in range(6):
            card.rowconfigure(r, weight=0)
        card.rowconfigure(0, weight=1)   # top spacer
        card.rowconfigure(5, weight=1)   # bottom spacer

        title = tk.Label(
            card,
            text="AUBus Login",
            font=("Arial", 18, "bold"),
            bg="#333333",
            fg="white",
        )
        title.grid(row=1, column=0, columnspan=2, pady=(0, 20))

        # Username
        tk.Label(
            card,
            text="Username:",
            bg="#333333",
            fg="white"
        ).grid(row=2, column=0, sticky="e", padx=10, pady=5)

        self.entry_username = tk.Entry(card, width=25)
        self.entry_username.grid(row=2, column=1, sticky="w", padx=10, pady=5)

        # Password
        tk.Label(
            card,
            text="Password:",
            bg="#333333",
            fg="white"
        ).grid(row=3, column=0, sticky="e", padx=10, pady=5)

        self.entry_password = tk.Entry(card, show="*", width=25)
        self.entry_password.grid(row=3, column=1, sticky="w", padx=10, pady=5)

        # Buttons row
        btn_login = tk.Button(
            card,
            text="Login",
            command=self._on_login_clicked,
            highlightthickness=0,
            borderwidth=1,
            width=10,
        )
        btn_login.grid(row=4, column=0, columnspan=2, pady=(15, 5))

        btn_register = tk.Button(
            card,
            text="Register",
            command=self._on_register_clicked,
            highlightthickness=0,
            borderwidth=1,
            width=10,
        )
        btn_register.grid(row=5, column=0, columnspan=2, pady=(0, 10))

        # Status label (for errors)
        self.label_status = tk.Label(
            card,
            text="",
            fg="#ffcccc",
            bg="#333333",
        )
        self.label_status.grid(row=6, column=0, columnspan=2, pady=(5, 0))

    def _on_login_clicked(self) -> None:
        username = self.entry_username.get().strip()
        password = self.entry_password.get().strip()

        if not username or not password:
            self.label_status.config(
                text="Please enter username and password.")
            return

        try:
            resp = self.client.login(username, password)
        except Exception as e:
            messagebox.showerror("Connection error",
                                 f"Failed to talk to server:\n{e}")
            return

        if resp["type"] != "login_ok":
            # Show backend error (e.g. INVALID_CREDENTIALS)
            error_code = resp["payload"].get("error", "UNKNOWN_ERROR")
            self.label_status.config(text=f"Login failed: {error_code}")
            return

        # Login successful: payload has user info
        user_info: Dict[str, Any] = resp["payload"]

        # Ask the main App to show the home screen
        self.master.show_home_screen(user_info)

    def _on_register_clicked(self) -> None:
        # Ask the main App to show the register screen
        self.master.show_register_screen()
