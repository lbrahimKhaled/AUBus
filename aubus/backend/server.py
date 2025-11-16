# server.py
import socket
import threading
from typing import Dict, Any, Tuple

from config import SERVER_HOST, SERVER_PORT
from db import init_db
from protocol import read_message, send_message, make_error
import handlers


ClientContext = Dict[str, Any]


class AubusServer:
    """
    Simple multithreaded TCP server for AUBus.

    Responsibilities:
      - Bind and listen on a host/port.
      - Accept incoming client connections.
      - For each client, start a new thread that:
          - reads JSON-line messages
          - hands them to handlers.handle_request
          - sends back the response
    """

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._server_socket: socket.socket | None = None

    def start(self) -> None:
        """
        Start the server: bind, listen, accept loop.
        Ctrl+C (KeyboardInterrupt) will stop the server.
        """
        # 1) Create a TCP socket
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow quick restart on the same port
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # 2) Bind to host:port and start listening
        server_sock.bind((self.host, self.port))
        server_sock.listen()

        self._server_socket = server_sock

        print(f"[SERVER] AUBus server listening on {self.host}:{self.port}")

        try:
            while True:
                # 3) Accept a new client
                client_sock, addr = server_sock.accept()
                print(f"[SERVER] New connection from {addr}")

                # Create a per-client context; we will store user_id here after login
                context: ClientContext = {
                    "addr": addr,
                    "user_id": None,
                }

                # 4) Start a new thread for this client
                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, context),
                    daemon=True,  # daemon=True so threads end when main program ends
                )
                thread.start()
        except KeyboardInterrupt:
            print("\n[SERVER] Shutting down (KeyboardInterrupt).")
        finally:
            server_sock.close()
            print("[SERVER] Socket closed.")

    def _handle_client(self, client_sock: socket.socket, context: ClientContext) -> None:
        """
        Per-client thread function.

        Continuously reads messages from this client, dispatches them, and
        sends back responses, until the client disconnects or an error occurs.
        """
        addr: Tuple[str, int] = context["addr"]
        try:
            while True:
                msg = read_message(client_sock)
                if msg is None:
                    # Client disconnected or sent invalid JSON
                    print(f"[CLIENT {addr}] Disconnected.")
                    break

                # Debug print (you can later replace with proper logging)
                print(f"[CLIENT {addr}] Received: {msg}")

                try:
                    response = handlers.handle_request(msg, context)
                except Exception as e:
                    # If handler crashes, log and send a generic error
                    print(f"[CLIENT {addr}] Handler error: {e}")
                    response = make_error(msg, "INTERNAL_SERVER_ERROR")

                # Send the response (unless handlers return something else, but for now they always do)
                if response is not None:
                    print(f"[CLIENT {addr}] Sending: {response}")
                    send_message(client_sock, response)

        finally:
            client_sock.close()
            print(f"[CLIENT {addr}] Socket closed.")


if __name__ == "__main__":
    # Ensure DB schema exists before starting the server
    init_db()
    server = AubusServer(SERVER_HOST, SERVER_PORT)
    server.start()
