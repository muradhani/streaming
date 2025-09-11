from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt


class ClickableImage(QLabel):
    def __init__(self, socket_manager, parent=None):
        super().__init__(parent)
        self.socket_mgr = socket_manager
        self.setAlignment(Qt.AlignCenter)
        self.setText("Waiting for image...")
        self.setMinimumSize(640, 480)

    def update_frame(self, qimg):
        pixmap = QPixmap.fromImage(qimg)
        self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def mousePressEvent(self, event):
        if self.pixmap():
            # Calculate the actual image position considering scaling
            pixmap = self.pixmap()
            label_size = self.size()
            pixmap_size = pixmap.size()

            # Calculate offsets if the pixmap is smaller than the label
            x_offset = (label_size.width() - pixmap_size.width()) / 2
            y_offset = (label_size.height() - pixmap_size.height()) / 2

            # Calculate the position in the original image
            x_ratio = pixmap_size.width() / self.socket_mgr.current_width
            y_ratio = pixmap_size.height() / self.socket_mgr.current_height

            x = int((event.pos().x() - x_offset) / x_ratio)
            y = int((event.pos().y() - y_offset) / y_ratio)

            # Ensure coordinates are within bounds
            x = max(0, min(x, self.socket_mgr.current_width - 1))
            y = max(0, min(y, self.socket_mgr.current_height - 1))

            self.socket_mgr.send_touch(x, y, "point")
        super().mousePressEvent(event)
