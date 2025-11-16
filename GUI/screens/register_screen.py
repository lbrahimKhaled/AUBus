# GUI/screens/register_screen.py
import tkinter as tk
from tkinter import messagebox


class RegisterScreen(tk.Frame):
    """
    Simple registration form.

    Uses AubusClient.register() to create a new user.
    On success, it returns to the LoginScreen.
    """

    def __init__(self, master, client, **kwargs):
        super().__init__(master, **kwargs)
        self.client = client

        # Match login background
        self.configure(bg="#333333")

        self._build_widgets()

    def _build_widgets(self) -> None:
        # Outer frame fills the window
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Centered inner "card"
        card = tk.Frame(self, bg="#333333")
        card.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=2)

        # Some row weights for spacing
        for r in range(10):
            card.rowconfigure(r, weight=0)
        card.rowconfigure(0, weight=1)   # top spacer
        card.rowconfigure(9, weight=1)   # bottom spacer

        title = tk.Label(
            card,
            text="Create AUBus Account",
            font=("Arial", 18, "bold"),
            bg="#333333",
            fg="white",
        )
        title.grid(row=1, column=0, columnspan=2, pady=(0, 15))

        # Name
        tk.Label(card, text="Name:", bg="#333333", fg="white").grid(
            row=2, column=0, sticky="e", padx=10, pady=3
        )
        self.entry_name = tk.Entry(card, width=28)
        self.entry_name.grid(row=2, column=1, sticky="w", padx=10, pady=3)

        # Email
        tk.Label(card, text="Email:", bg="#333333", fg="white").grid(
            row=3, column=0, sticky="e", padx=10, pady=3
        )
        self.entry_email = tk.Entry(card, width=28)
        self.entry_email.grid(row=3, column=1, sticky="w", padx=10, pady=3)

        # Username
        tk.Label(card, text="Username:", bg="#333333", fg="white").grid(
            row=4, column=0, sticky="e", padx=10, pady=3
        )
        self.entry_username = tk.Entry(card, width=28)
        self.entry_username.grid(row=4, column=1, sticky="w", padx=10, pady=3)

        # Password
        tk.Label(card, text="Password:", bg="#333333", fg="white").grid(
            row=5, column=0, sticky="e", padx=10, pady=3
        )
        self.entry_password = tk.Entry(card, show="*", width=28)
        self.entry_password.grid(row=5, column=1, sticky="w", padx=10, pady=3)

        # Area
        tk.Label(card, text="Area:", bg="#333333", fg="white").grid(
            row=6, column=0, sticky="e", padx=10, pady=3
        )
        self.entry_area = tk.Entry(card, width=28)
        self.entry_area.grid(row=6, column=1, sticky="w", padx=10, pady=3)
        # If you want no default, just comment the next line
        # self.entry_area.insert(0, "Hamra")

        # Is driver checkbox
        self.is_driver_var = tk.BooleanVar(value=False)
        chk_driver = tk.Checkbutton(
            card,
            text="I am a driver",
            variable=self.is_driver_var,
            bg="#333333",
            fg="white",
            activebackground="#333333",
            activeforeground="white",
            selectcolor="#333333",
        )
        chk_driver.grid(row=7, column=0, columnspan=2, pady=(5, 10))

        # Buttons
        btn_register = tk.Button(
            card,
            text="Create account",
            command=self._on_register_clicked,
            highlightthickness=0,
            borderwidth=1,
            width=14,
        )
        btn_register.grid(row=8, column=0, columnspan=2, pady=(5, 5))

        btn_back = tk.Button(
            card,
            text="Back to login",
            command=self._on_back_clicked,
            highlightthickness=0,
            borderwidth=1,
            width=14,
        )
        btn_back.grid(row=9, column=0, columnspan=2, pady=(0, 10))

        # Status label
        self.label_status = tk.Label(
            card,
            text="",
            fg="#ffcccc",
            bg="#333333",
        )
        self.label_status.grid(row=10, column=0, columnspan=2, pady=(5, 0))

    def _on_register_clicked(self) -> None:
        name = self.entry_name.get().strip()
        email = self.entry_email.get().strip()
        username = self.entry_username.get().strip()
        password = self.entry_password.get().strip()
        area = self.entry_area.get().strip()
        is_driver = self.is_driver_var.get()

        if not (name and email and username and password and area):
            self.label_status.config(text="Please fill all fields.")
            return

        try:
            resp = self.client.register(
                name=name,
                email=email,
                username=username,
                password=password,
                area=area,
                is_driver=is_driver,
            )
        except Exception as e:
            messagebox.showerror("Connection error",
                                 f"Failed to talk to server:\n{e}")
            return

        if resp["type"] != "register_ok":
            error_code = resp["payload"].get("error", "REGISTER_FAILED")
            self.label_status.config(text=f"Registration failed: {error_code}")
            return

        messagebox.showinfo(
            "Registration successful",
            "Your account has been created. You can now log in.",
        )
        self.master.show_login_screen()

    def _on_back_clicked(self) -> None:
        self.master.show_login_screen()
