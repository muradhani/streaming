from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt


class ClickableImage(QLabel):
    def __init__(self, StreamServer):
        super().__init__()
        self.socket_manager = StreamServer
        self.setScaledContents(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = event.x()
            y = event.y()
            print(f"🖱 Clicked at: {x}, {y}")
            self.socket_manager.send_touch_coordinates(x, y)

    def update_frame(self, qimg):
        pixmap = QPixmap.fromImage(qimg)
        self.setPixmap(pixmap)
