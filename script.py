import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from ClickableImage import ClickableImage
from SocketManager import SocketManager


class App(QWidget):
    def __init__(self, image_path="example.png"):
        super().__init__()
        self.socket_manager = SocketManager()
        self.socket_manager.start_server()

        layout = QVBoxLayout()
        self.image_widget = ClickableImage(image_path, self.socket_manager)
        layout.addWidget(self.image_widget)

        self.setLayout(layout)
        self.setWindowTitle("Depthgram UI (Python)")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App("example.png")
    window.show()
    sys.exit(app.exec_())
