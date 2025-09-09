import socket
import struct
import threading
import io
import subprocess
from PIL import Image
from PyQt5.QtGui import QImage


class SocketManager:
    def __init__(self, host="0.0.0.0", port=8080):
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.lock = threading.Lock()

        # Callbacks instead of StateFlow
        self.on_image = None
        self.on_distance = None
        self.on_point3d = None  # callback for 3D points

        # Storage for matching corners
        self.pending_points = []

    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        print(f"📡 Listening on {self.host}:{self.port}...")

        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        while True:
            client, addr = self.server_socket.accept()
            self.client_socket = client
            print(f"📥 Client connected: {addr}")
            threading.Thread(target=self._listen_for_messages, daemon=True).start()

    def _listen_for_messages(self):
        try:
            while True:
                msg_type_data = self._recv_exact(4)
                if not msg_type_data:
                    break
                msg_type = struct.unpack(">i", msg_type_data)[0]

                if msg_type == 1:
                    size = struct.unpack("<i", self._recv_exact(4))[0]  # little-endian
                    payload = self._recv_exact(size)

                    # Extract intrinsics + JPEG bytes
                    jpeg_bytes = payload[24:]  # skip first 24 bytes
                    img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")

                    # Convert PIL Image → QImage
                    qimg = QImage(img.tobytes(), img.width, img.height, QImage.Format_RGB888)

                    # Call the callback
                    if self.on_image:
                        self.on_image(qimg)

                elif msg_type == 2:
                    # distance (simple float return)
                    x, y, z = struct.unpack(">fff", self._recv_exact(12))
                    print(f"📏 Vector: ({x:.2f}, {y:.2f}, {z:.2f})")
                    print(f"📏 Distance: {z:.2f} m")
                    if self.on_distance:
                        self.on_distance(z)

                elif msg_type == 3:
                    # phone responded with 3D coordinates
                    x, y, z = struct.unpack(">fff", self._recv_exact(12))
                    #print(f"📲 Phone returned 3D point: ({x:.2f}, {y:.2f}, {z:.2f})")

                    if self.pending_points:
                        label = self.pending_points.pop(0)
                        if self.on_point3d:
                            self.on_point3d(label, (x, y, z))

                else:
                    print(f"⚠ Unknown msg type: {msg_type}")
        except Exception as e:
            print(f"⚠ Connection lost: {e}")
        finally:
            if self.client_socket:
                self.client_socket.close()
            self.client_socket = None

    def send_touch(self, x: int, y: int, label="point"):
        """Send touch coordinates back to Android (msgType=3)."""
        if not self.client_socket:
            print("⚠ No client connected")
            return
        try:
            with self.lock:
                # msgType=3, payload=8, then x and y
                data = struct.pack(">iiii", 3, 8, x, y)
                self.client_socket.sendall(data)
                self.pending_points.append(label)
                #print(f"👆 Sent touch {label} to phone: ({x}, {y})")
        except Exception as e:
            print(f"❌ Failed to send touch: {e}")

    def _recv_exact(self, size: int) -> bytes:
        buf = b""
        while len(buf) < size:
            data = self.client_socket.recv(size - len(buf))
            if not data:
                return None
            buf += data
        return buf
