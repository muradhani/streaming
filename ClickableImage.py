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
        if self.pixmap():
            # Get the displayed pixmap and its dimensions
            pixmap = self.pixmap()
            label_size = self.size()
            pixmap_size = pixmap.size()

            # Calculate the aspect ratios
            phone_ratio = self.socket_mgr.current_width / self.socket_mgr.current_height
            label_ratio = label_size.width() / label_size.height()

            # Calculate the actual displayed image area and offsets
            if phone_ratio > label_ratio:
                # Image is wider than label - black bars on top and bottom
                display_width = label_size.width()
                display_height = label_size.width() / phone_ratio
                x_offset = 0
                y_offset = (label_size.height() - display_height) / 2
            else:
                # Image is taller than label - black bars on sides
                display_height = label_size.height()
                display_width = label_size.height() * phone_ratio
                x_offset = (label_size.width() - display_width) / 2
                y_offset = 0

            # Check if click is outside the image area (in black bars)
            if (event.pos().x() < x_offset or
                    event.pos().x() > x_offset + display_width or
                    event.pos().y() < y_offset or
                    event.pos().y() > y_offset + display_height):
                # Click is in the black bars, ignore it
                return

            # Calculate normalized coordinates (0 to 1)
            x_normalized = (event.pos().x() - x_offset) / display_width
            y_normalized = (event.pos().y() - y_offset) / display_height

            # Ensure coordinates are within bounds (0 to 1)
            x_normalized = max(0.0, min(1.0, x_normalized))
            y_normalized = max(0.0, min(1.0, y_normalized))

            # Debug output
            print(f"Normalized coordinates: ({x_normalized:.3f}, {y_normalized:.3f})")

            self.clicks.append((x_normalized, y_normalized))

            if len(self.clicks) == 2:
                self.socket_mgr.get_object_distance(self.clicks)
                self.clicks = []

        super().mousePressEvent(event)