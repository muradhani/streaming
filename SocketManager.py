import socket
import struct
import threading
import io
import subprocess
from PIL import Image
from PyQt5.QtGui import QImage


class StreamServer:
    def __init__(self, host="127.0.0.1", port=8080, on_frame=None):
        self.host = host
        self.port = port
        self.sock = None
        self.client = None
        self.running = False
        self.on_frame = on_frame
        self.lock = threading.Lock()  # like Kotlin's writeLock

    def run_adb_reverse(self):
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
        self.sock.listen(1)  # only 1 client
        self.running = True
        print(f"📡 Listening on {self.host}:{self.port}...")

        threading.Thread(target=self.accept_client, daemon=True).start()

    def accept_client(self):
        while self.running:
            conn, addr = self.sock.accept()
            self.client = conn
            print(f"📥 Client connected: {addr}")
            threading.Thread(target=self.listen_for_messages, daemon=True).start()

    def recv_exact(self, size):
        buf = b""
        while len(buf) < size:
            chunk = self.client.recv(size - len(buf))
            if not chunk:
                raise ConnectionError("Socket closed")
            buf += chunk
        return buf

    def read_int(self):
        return struct.unpack("<i", self.recv_exact(4))[0]

    def read_float(self):
        return struct.unpack("<f", self.recv_exact(4))[0]

    def listen_for_messages(self):
        try:
            while self.running and self.client:
                header = self.recv_exact(4)
                msg_type = struct.unpack("<i", header)[0]

                if msg_type == 1:  # Image + intrinsics
                    size = struct.unpack("<i", self.recv_exact(4))[0]
                    payload = self.recv_exact(size)

                    fx, fy, cx, cy, width, height = struct.unpack("<ffffii", payload[:24])
                    jpeg_bytes = payload[24:]

                    img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
                    qimg = QImage(img.tobytes(), img.width, img.height, QImage.Format_RGB888)

                    if self.on_frame:
                        self.on_frame(qimg)

                elif msg_type == 2:  # Distance data
                    distance = self.read_float()
                    dx = self.read_float()
                    dy = self.read_float()
                    dz = self.read_float()
                    print(f"📏 Distance → {distance:.2f} m, dx={dx:.2f}, dy={dy:.2f}, dz={dz:.2f}")

                else:
                    print(f"⚠ Unknown msgType: {msg_type}")

        except Exception as e:
            print("⚠ Connection lost:", e)
            self.client = None

    def send_touch_coordinates(self, x, y):
        try:
            if not self.client:
                print("❌ No client connected")
                return

            with self.lock:
                self.client.sendall(struct.pack("<i", 3))  # msgType
                self.client.sendall(struct.pack("<i", 8))  # size
                self.client.sendall(struct.pack("<i", x))  # x
                self.client.sendall(struct.pack("<i", y))  # y
                print(f"📤 Sent touch coordinates: x={x}, y={y}")

        except Exception as e:
            print("❌ Failed to send touch:", e)
