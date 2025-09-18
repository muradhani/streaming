import socket
import struct
import threading
import io
from typing import List

import numpy as np
from PIL import Image
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, pyqtSignal, QObject, QByteArray, Qt



class SocketManager(QObject):
    # Define signals for thread-safe communication
    image_received = pyqtSignal(QImage)
    distance_received = pyqtSignal(float)

    def __init__(self, host="0.0.0.0", port=8080):
        super().__init__()
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.lock = threading.Lock()
        self.pending_points = []

        # For memory reuse
        self.current_width = 0
        self.current_height = 0
        self.image_buffer = None
        self.qimage = None
        self.byte_array = None

    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        print(f"📡 Listening on {self.host}:{self.port}...")

        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        while True:
            try:
                client, addr = self.server_socket.accept()
                self.client_socket = client
                print(f"📥 Client connected: {addr}")
                threading.Thread(target=self._listen_for_messages, daemon=True).start()
            except Exception as e:
                print(f"⚠ Accept error: {e}")
                break

    def _listen_for_messages(self):
        try:
            while True:
                msg_type_data = self._recv_exact(4)
                if not msg_type_data:
                    break
                msg_type = struct.unpack(">i", msg_type_data)[0]

                if msg_type == 1:  # Image + intrinsics
                    # Read payload size (big-endian)
                    size_data = self._recv_exact(4)
                    if not size_data:
                        break
                    size = struct.unpack(">i", size_data)[0]

                    # Read full payload
                    payload = self._recv_exact(size)
                    if not payload:
                        break

                    # Extract intrinsics (first 24 bytes, little-endian)
                    fx, fy, cx, cy = struct.unpack("<ffff", payload[:16])
                    width, height = struct.unpack("<ii", payload[16:24])

                    # Extract JPEG bytes (rest of payload)
                    jpeg_bytes = payload[24:]

                    # Convert JPEG bytes to PIL Image
                    try:
                        # Convert JPEG bytes to PIL Image
                        img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
                        np_img = np.array(img)

                        # Ensure buffer matches incoming image size
                        if self.image_buffer is None or self.image_buffer.shape != np_img.shape:
                            self.image_buffer = np.empty_like(np_img)

                        # Copy image data into buffer
                        np.copyto(self.image_buffer, np_img)

                        # Create or update QImage
                        self.qimage = QImage(
                            self.image_buffer.data,
                            np_img.shape[1],
                            np_img.shape[0],
                            np_img.shape[1] * 3,  # bytes per line
                            QImage.Format_RGB888
                        )

                        # Emit a copy for thread safety
                        self.image_received.emit(self.qimage.copy())
                    # Create a copy for thread safety

                    except Exception as e:
                        print(f"⚠ Failed to process image: {e}")

                elif msg_type == 2:  # Distance data
                    data = self._recv_exact(16)  # 4 floats
                    if not data:
                        break
                    distance, dx, dy, dz = struct.unpack("<ffff", data)
                    print(f"📏 Distance → {distance:.2f} m, dx={dx:.2f}, dy={dy:.2f}, dz={dz:.2f}")
                    self.distance_received.emit(distance)
                elif msg_type == 5 :
                    data = self._recv_exact(4)  # one float = 4 bytes
                    if not data:
                        break
                    distance = struct.unpack(">f", data)[0]
                    print(f"📏 (Type 5) Distance only → {distance:.2f} m")
                    self.distance_received.emit(distance)

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
                print(f"👆 Sent touch {label} to phone: ({x}, {y})")
        except Exception as e:
            print(f"❌ Failed to send touch: {e}")

    def _recv_exact(self, size: int) -> bytes:
        if not self.client_socket:
            return None

        buf = b""
        while len(buf) < size:
            try:
                data = self.client_socket.recv(size - len(buf))
                if not data:
                    return None
                buf += data
            except socket.error as e:
                print(f"⚠ Socket error in _recv_exact: {e}")
                return None
        return buf

    def get_object_distance(self,click:List[int]):
        """Send touch coordinates back to Android (msgType=3)."""
        if not self.client_socket:
            print("⚠ No client connected")
            return
        try:
            with self.lock:
                # msgType=4, payload=16, then x and y
                x1, y1 = click[0]
                x2, y2 = click[1]
                data = struct.pack(">iiffff", 4, 16, x1, y1,x2,y2)
                self.client_socket.sendall(data)
                print(f"👆 Sent touch to phone: ({x1}, {y1}) ({x2}, {y2})")
        except Exception as e:
            print(f"❌ Failed to send touch: {e}")