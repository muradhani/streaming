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
        scaled_pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        # calculate where it sits inside the QLabel (offset = black borders)
        self.start_x = (self.width() - scaled_pixmap.width()) / 2
        self.start_y = (self.height() - scaled_pixmap.height()) / 2

        # store the displayed size of the preview
        self.display_w = scaled_pixmap.width()
        self.display_h = scaled_pixmap.height()
        # displaying the real width and height
        print(f"Preview displayed size: {self.display_w} x {self.display_h}")

        # this is the space between the image and the real previewing image
        print(f"Preview offset inside widget: {self.start_x}, {self.start_y}")

        self.setPixmap(scaled_pixmap)

    def mousePressEvent(self, event):
        click_x = event.pos().x()
        click_y = event.pos().y()
        real_x = event.pos().x() - self.start_x
        real_y = event.pos().y() - self.start_y

        normalized_x = real_x / self.display_w
        normalized_y = real_y / self.display_h

        print(f"Click at: ({normalized_x:.1f}, {normalized_y:.1f})")
        self.socket_manager.send_touch_coordinates(normalized_x, normalized_y)
        super().mousePressEvent(event)

