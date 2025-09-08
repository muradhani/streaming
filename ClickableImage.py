from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt


class ClickableImage(QLabel):
    def __init__(self, image_path, socket_manager):
        super().__init__()
        self.socket_manager = socket_manager

        pixmap = QPixmap(image_path)
        self.setPixmap(pixmap)
        self.setScaledContents(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = event.x()
            y = event.y()
            print(f"Clicked at: {x}, {y}")
            self.socket_manager.send_touch_coordinates(x, y)