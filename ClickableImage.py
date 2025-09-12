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
        Minimal version: only compute the actual displayed preview size
        and its top-left offset (start_x, start_y) inside the label.
        """
        pix = self.pixmap()
        if pix is None:
            super().mousePressEvent(event)
            return

        # Widget size
        label_w = float(self.width())
        label_h = float(self.height())

        # Original frame dimensions (from phone)
        try:
            frame_w = float(self.socket_mgr.current_width)
            frame_h = float(self.socket_mgr.current_height)
            if frame_w <= 0 or frame_h <= 0:
                raise ValueError("invalid frame size")
        except Exception:
            print("ERROR: missing/invalid frame dimensions from socket_mgr")
            super().mousePressEvent(event)
            return

        # Aspect ratios
        frame_ratio = frame_w / frame_h
        label_ratio = label_w / label_h

        # Compute displayed preview size (fit inside label, keep aspect ratio)
        if frame_ratio > label_ratio:
            display_w = label_w
            display_h = label_w / frame_ratio
        else:
            display_h = label_h
            display_w = label_h * frame_ratio

        # Compute offsets (where the image starts inside the label)
        start_x = (label_w - display_w) / 2.0
        start_y = (label_h - display_h) / 2.0

        print(f"Preview rect: start=({start_x:.1f},{start_y:.1f}), "
              f"size=({display_w:.1f},{display_h:.1f})")

        super().mousePressEvent(event)

