# GUI/app.py
import tkinter as tk
from tkinter import messagebox
from typing import Any, Dict

from .net import AubusClient
from .screens.login_screen import LoginScreen
from .screens.home_screen import HomeScreen
from .screens.register_screen import RegisterScreen
from .screens.schedules_screen import SchedulesScreen
from .screens.ride_request_screen import RideRequestScreen
from .screens.chat_screen import ChatScreen
from .screens.ratings_screen import RatingsScreen
from .screens.rider_requests_screen import RiderRequestsScreen
from .screens.driver_requests_screen import DriverRequestsScreen


class App(tk.Tk):
    """
    Main Tkinter window for AUBus GUI.

    Responsibilities:
      - Create and own a single AubusClient instance.
      - Connect to the backend at startup (and run health check).
      - Hold the current user info.
      - Switch between simple screens (LoginScreen, HomeScreen, etc.).
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.title("AUBus")
        self.geometry("600x400")

        # Networking client shared by all screens
        self.client = AubusClient()

        # Currently logged-in user (after login_ok)
        self.current_user: Dict[str, Any] | None = None

        # Current screen (tk.Frame)
        self.current_screen: tk.Frame | None = None

        # Chat parameters (used by ChatScreen)
        self.chat_channel_id: str | None = None
        self.chat_title: str | None = None

        # Try to connect to backend
        if not self._init_connection():
            # If connection fails, close the app
            self.destroy()
            return

        # Start on login screen
        self.show_login_screen()

    def _init_connection(self) -> bool:
        """
        Connect to the backend server and run health check.
        Shows a messagebox on failure.
        Returns True on success, False on failure.
        """
        try:
            self.client.connect()
        except Exception as e:
            messagebox.showerror(
                "Connection error",
                f"Could not connect to AUBus server:\n{e}",
            )
            return False

        # Optional: use the health handler we added
        try:
            ok = self.client.health()
        except Exception as e:
            messagebox.showerror(
                "Connection error",
                f"Failed to talk to server after connect():\n{e}",
            )
            return False

        if not ok:
            messagebox.showerror(
                "Connection error",
                "Server responded but health check failed.",
            )
            return False

        return True

    # ----------------------------
    # Screen switching helpers
    # ----------------------------

    def _switch_screen(self, screen_class):
        """
        Destroy current screen and create a new one of the given class.
        """
        if self.current_screen is not None:
            self.current_screen.destroy()

        frame = screen_class(self, self.client)
        frame.pack(fill="both", expand=True)
        self.current_screen = frame
        return frame

    def show_login_screen(self) -> None:
        self.current_user = None
        self._switch_screen(LoginScreen)

    def show_home_screen(self, user_info: Dict[str, Any]) -> None:
        self.current_user = user_info
        frame: HomeScreen = self._switch_screen(HomeScreen)  # type: ignore
        frame.set_user(user_info)

    def show_register_screen(self) -> None:
        self._switch_screen(RegisterScreen)

    def show_schedules_screen(self) -> None:
        # We assume current_user is already set after login
        self._switch_screen(SchedulesScreen)

    def show_ride_request_screen(self) -> None:
        self._switch_screen(RideRequestScreen)

    def show_chat_screen(self, channel_id: str, title: str | None = None) -> None:
        """
        Open a chat screen bound to a specific relay channel.
        Later we'll call this with channel_id = ride_request_id.
        """
        self.chat_channel_id = channel_id
        self.chat_title = title or f"Chat ({channel_id})"
        self._switch_screen(ChatScreen)

    def show_ratings_screen(self) -> None:
        self._switch_screen(RatingsScreen)

    def show_rider_requests_screen(self) -> None:
        self._switch_screen(RiderRequestsScreen)

    def show_driver_requests_screen(self) -> None:
        self._switch_screen(DriverRequestsScreen)


if __name__ == "__main__":
    app = App()
    app.mainloop()
