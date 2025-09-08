import socket
import threading


class SocketManager:
    def __init__(self, host="127.0.0.1", port=9999):
        self.host = host
        self.port = port
        self.sock = None
        self.running = False

    def start_server(self):
        """Start a TCP server to receive/send data."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.host, self.port))
        self.sock.listen(1)
        self.running = True
        print(f"Server started on {self.host}:{self.port}")

        threading.Thread(target=self.accept_client, daemon=True).start()

    def accept_client(self):
        conn, addr = self.sock.accept()
        print(f"Client connected: {addr}")
        while self.running:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                print(f"Received: {data.decode()}")
            except:
                break
        conn.close()

    def send_touch_coordinates(self, x, y):
        """Send touch coordinates to the connected client."""
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((self.host, self.port))
            client.sendall(f"{x},{y}".encode())
            client.close()
        except Exception as e:
            print("Send failed:", e)