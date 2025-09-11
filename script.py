from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
import sys

from ClickableImage import ClickableImage
from SocketManager import SocketManager


class App(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        self.socket_mgr = SocketManager()
        self.image_widget = ClickableImage(self.socket_mgr)
        layout.addWidget(self.image_widget)
        self.setLayout(layout)

        self.setWindowTitle("Depthgram UI (Python)")
        self.resize(800, 600)

        # Connect signals
        self.socket_mgr.image_received.connect(self.on_new_frame)

        # Start server
        self.socket_mgr.start_server()

    def on_new_frame(self, qimg):
        self.image_widget.update_frame(qimg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())