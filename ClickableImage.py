from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt


class ClickableImage(QLabel):
    def __init__(self, socket_manager, parent=None):
        super().__init__(parent)
        self.socket_mgr = socket_manager
        self.setAlignment(Qt.AlignCenter)
        self.setText("Waiting for video...")
        self.setMinimumSize(640, 480)
        self.clicks = []

    def update_frame(self, qimg):
        pixmap = QPixmap.fromImage(qimg)
        self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def mousePressEvent(self, event):
        """
        Robust mapping of a click on the desktop preview to normalized (0..1) image coords.
        Sends normalized coords (relative to original frame pixels) to the phone via socket_mgr.
        """
        pix = self.pixmap()
        if pix is None:
            super().mousePressEvent(event)
            return

        # widget (label) logical size
        label_w = float(self.width())
        label_h = float(self.height())

        # original frame dimensions (must be provided by the phone)
        try:
            frame_w = float(self.socket_mgr.current_width)
            frame_h = float(self.socket_mgr.current_height)
            if frame_w <= 0 or frame_h <= 0:
                raise ValueError("invalid frame size")
        except Exception:
            # cannot map without the original frame size
            print("ERROR: missing/invalid frame dimensions from socket_mgr")
            super().mousePressEvent(event)
            return

        # --- determine the actual displayed image size inside the label ---
        # Use the pixmap logical size if available (handles cases where you set a scaled pixmap).
        # Account for devicePixelRatio for high-DPI displays.
        try:
            pdr = pix.devicePixelRatio()
        except Exception:
            pdr = 1.0
        pix_logical_w = pix.width() / max(1.0, pdr)
        pix_logical_h = pix.height() / max(1.0, pdr)

        # If the pixmap logical size is reasonable (non-zero), assume it is the displayed size (or close to it).
        # Otherwise compute a "fit" of the original frame into the label keeping aspect ratio.
        if pix_logical_w > 0 and pix_logical_h > 0:
            # pixmap may already be scaled to the display size; compute fit scale to avoid overflow
            scale = min(label_w / pix_logical_w, label_h / pix_logical_h, 1.0)
            display_w = pix_logical_w * scale
            display_h = pix_logical_h * scale
        else:
            # fallback: compute display area by fitting the original frame (keep aspect ratio)
            frame_ratio = frame_w / frame_h
            label_ratio = label_w / label_h
            if frame_ratio > label_ratio:
                display_w = label_w
                display_h = label_w / frame_ratio
            else:
                display_h = label_h
                display_w = label_h * frame_ratio

        # offsets (startX, startY) of the displayed preview inside the label
        start_x = (label_w - display_w) / 2.0
        start_y = (label_h - display_h) / 2.0

        # clicked point (logical label coords)
        click_x = float(event.pos().x())
        click_y = float(event.pos().y())

        # ignore clicks outside the displayed image area (black bars)
        if not (start_x <= click_x <= start_x + display_w and
                start_y <= click_y <= start_y + display_h):
            return

        # Map the click to pixel coordinates in the ORIGINAL frame (frame_w x frame_h).
        # This handles any scaling that happened on the desktop side.
        img_x = (click_x - start_x) * (frame_w / display_w)
        img_y = (click_y - start_y) * (frame_h / display_h)

        # If your phone sends rotated frames, handle rotation here (see notes below).
        # For now we assume the phone sent the frame upright. If rotation metadata exists,
        # prefer to send (img_x,img_y,rotation) to the phone and let it un-rotate there.

        # Normalize to [0..1]
        norm_x = max(0.0, min(1.0, img_x / frame_w))
        norm_y = max(0.0, min(1.0, img_y / frame_h))

        print(f"Normalized coordinates: ({norm_x:.6f}, {norm_y:.6f}), "
              f"display area start=({start_x:.1f},{start_y:.1f}) size=({display_w:.1f},{display_h:.1f})")

        # collect / transmit
        self.clicks.append((norm_x, norm_y))
        if len(self.clicks) == 2:
            # send normalized coordinates to phone
            # IMPORTANT: the phone must know frame_w/frame_h and rotation/displayMode
            self.socket_mgr.get_object_distance(self.clicks)
            self.clicks.clear()

        super().mousePressEvent(event)
