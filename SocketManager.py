import socket
import struct
import threading
import io
import subprocess
from PIL import Image
from PyQt5.QtGui import QImage


class StreamServer:
    def __init__(self, host="127.0.0.1", port=9999, on_frame=None):
        self.host = host
        self.port = port
        self.sock = None
        self.running = False
        self.on_frame = on_frame  # callback (QImage) -> None

    def run_adb_reverse(self):
        """Run adb reverse so Android can connect to this server."""
        try:
            process = subprocess.Popen(
                ["adb", "reverse", f"tcp:{self.port}", f"tcp:{self.port}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            for line in process.stdout:
                print("ADB:", line.strip())
            process.wait()
            print("✅ adb reverse set up")
        except Exception as e:
            print("❌ Failed to run adb reverse:", e)

    def start_server(self):
        if self.sock:
            print("⚠️ Server already started")
            return

        self.run_adb_reverse()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        self.running = True
        print(f"📡 Server started on {self.host}:{self.port}")

        threading.Thread(target=self.accept_clients, daemon=True).start()

    def accept_clients(self):
        """Accept multiple clients and spawn threads for each."""
        while self.running:
            try:
                conn, addr = self.sock.accept()
                print(f"✅ Client connected: {addr}")
                threading.Thread(
                    target=self.handle_client, args=(conn,), daemon=True
                ).start()
            except Exception as e:
                print("⚠ Accept failed:", e)

    def recv_exact(self, conn, size):
        buf = b""
        while len(buf) < size:
            chunk = conn.recv(size - len(buf))
            if not chunk:
                raise ConnectionError("Socket closed")
            buf += chunk
        return buf

    def send_touch_coordinates(self, x, y):
        """Send normalized click coordinates to the connected client."""
        try:
            if not self.sock:
                raise RuntimeError("Server not running")
            # Connect as a client to send coords
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((self.host, self.port))
            message = f"{x},{y}"
            client.sendall(message.encode("utf-8"))
            client.close()
            print(f"📤 Sent: {message}")
        except Exception as e:
            print("❌ Send failed:", e)

    def handle_client(self, conn):
        """Handle incoming data from Android client."""
        try:
            while self.running:
                header = self.recv_exact(conn, 4)
                msg_type = struct.unpack("<i", header)[0]

                if msg_type == 1:  # Image frame
                    size_bytes = self.recv_exact(conn, 4)
                    size = struct.unpack("<i", size_bytes)[0]

                    payload = self.recv_exact(conn, size)
                    fx, fy, cx, cy, width, height = struct.unpack("<ffffii", payload[:24])
                    jpeg_bytes = payload[24:]

                    # Decode JPEG → QImage
                    img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
                    qimg = QImage(img.tobytes(), img.width, img.height, QImage.Format_RGB888)

                    if self.on_frame:
                        self.on_frame(qimg)

                elif msg_type == 2:  # Distance data
                    floats = self.recv_exact(conn, 16)
                    distance, dx, dy, dz = struct.unpack("<ffff", floats)
                    print(f"📏 Distance: {distance:.2f} m, dx={dx:.2f}, dy={dy:.2f}, dz={dz:.2f}")

                else:
                    print(f"⚠ Unknown msgType: {msg_type}")

        except Exception as e:
            print("⚠ Connection lost:", e)
        finally:
            conn.close()
            print("🔌 Client disconnected")
