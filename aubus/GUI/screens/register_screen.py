# gui/screens/register_screen.py
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from ..net import AubusClientError

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


class RegisterScreen(ttk.Frame):
    def __init__(self, master: tk.Widget, app: "App") -> None:
        super().__init__(master, style="Aubus.TFrame")
        self.app = app

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        card = ttk.Frame(self, style="Aubus.Card.TFrame", padding=24)
        card.grid(row=0, column=0, sticky="nsew", padx=80, pady=40)
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        title = ttk.Label(card, text="Create your AUBus account",
                          style="Aubus.Heading.TLabel")
        title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 16))

        self.name_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.area_var = tk.StringVar(value=AREAS_PRESETS[0])
        self.is_driver_var = tk.BooleanVar(value=False)

        def label(row: int, text: str):
            ttk.Label(card, text=text, style="Aubus.Body.TLabel").grid(
                row=row, column=0, columnspan=2, sticky="w", pady=(8, 2)
            )

        label(1, "Full name")
        ttk.Entry(card, textvariable=self.name_var, style="Aubus.TEntry").grid(
            row=2, column=0, columnspan=2, sticky="ew"
        )

        label(3, "AUB email")
        ttk.Entry(card, textvariable=self.email_var, style="Aubus.TEntry").grid(
            row=4, column=0, columnspan=2, sticky="ew"
        )

        label(5, "Username")
        ttk.Entry(card, textvariable=self.username_var, style="Aubus.TEntry").grid(
            row=6, column=0, columnspan=2, sticky="ew"
        )

        label(7, "Password")
        ttk.Entry(card, textvariable=self.password_var, style="Aubus.TEntry", show="•").grid(
            row=8, column=0, columnspan=2, sticky="ew"
        )

        label(9, "Home area")
        area_combo = ttk.Combobox(
            card,
            textvariable=self.area_var,
            values=AREAS_PRESETS,
            state="readonly",
        )
        area_combo.grid(row=10, column=0, sticky="ew", padx=(0, 12))

        ttk.Checkbutton(
            card,
            text="I want to drive (Driver account)",
            variable=self.is_driver_var,
            style="TCheckbutton",
        ).grid(row=10, column=1, sticky="w")

        btn_back = ttk.Button(
            card,
            text="Back to login",
            style="Aubus.Secondary.TButton",
            command=self.app.show_login_screen,
        )
        btn_back.grid(row=12, column=0, sticky="w", pady=(16, 0))

        btn_create = ttk.Button(
            card,
            text="Create account",
            style="Aubus.Primary.TButton",
            command=self._on_register,
        )
        btn_create.grid(row=12, column=1, sticky="e", pady=(16, 0))

    def _on_register(self) -> None:
        name = self.name_var.get().strip()
        email = self.email_var.get().strip()
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        area = self.area_var.get().strip()
        is_driver = bool(self.is_driver_var.get())

        if not (name and email and username and password and area):
            self.app.show_error("Please fill in all fields.")
            return

        try:
            self.app.client.register(
                name=name,
                email=email,
                username=username,
                password=password,
                area=area,
                is_driver=is_driver,
            )
        except AubusClientError as e:
            msg = "Registration failed. Username or email may already exist." if e.code == "REGISTER_FAILED" else f"Registration failed: {e.code}"
            self.app.show_error(msg)
            return

        self.app.show_info("Account created. You can now log in.")
        self.app.show_login_screen()
