import socket
import struct
import threading
import io
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
                        img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")

                        # Update dimensions if they've changed
                        if width != self.current_width or height != self.current_height:
                            self.current_width = width
                            self.current_height = height
                            # Pre-allocate buffer for image data
                            self.image_buffer = np.empty((height, width, 3), dtype=np.uint8)
                            self.byte_array = QByteArray()
                            self.byte_array.resize(width * height * 3)

                        # Copy image data to our buffer
                        np_img = np.array(img)
                        np.copyto(self.image_buffer, np_img)

                        # Create QImage from buffer without copying data
                        if self.qimage is None or self.qimage.width() != width or self.qimage.height() != height:
                            self.qimage = QImage(
                                self.image_buffer.data,
                                width,
                                height,
                                width * 3,  # bytesPerLine
                                QImage.Format_RGB888
                            )
                        else:
                            # Update existing QImage with new data
                            # Note: This approach is more efficient but requires careful memory management
                            pass

                        # Emit the signal (thread-safe)
                        self.image_received.emit(self.qimage.copy())  # Create a copy for thread safety

                    except Exception as e:
                        print(f"⚠ Failed to process image: {e}")

                elif msg_type == 2:  # Distance data
                    data = self._recv_exact(16)  # 4 floats
                    if not data:
                        break
                    distance, dx, dy, dz = struct.unpack("<ffff", data)
                    print(f"📏 Distance → {distance:.2f} m, dx={dx:.2f}, dy={dy:.2f}, dz={dz:.2f}")
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
