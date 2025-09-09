import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from ClickableImage import ClickableImage
from SocketManager import  SocketManager


class App(QWidget):
    def __init__(self, socket_mgr: SocketManager):
        super().__init__()

        layout = QVBoxLayout()
        self.image_widget = ClickableImage(None)  # will set socket later
        layout.addWidget(self.image_widget)
        self.setLayout(layout)

        self.setWindowTitle("Depthgram UI (Python)")

        # Start server with callback that updates the widget
        self.socket_manager = socket_mgr
        self.image_widget.socket_manager = self.socket_manager
        self.socket_manager.start_server()

    def on_new_frame(self, qimg):
        # This is called from a background thread → use signal/slot or invokeLater
        self.image_widget.update_frame(qimg)


if __name__ == "__main__":
    mgr = SocketManager(port=8080)
    app = QApplication(sys.argv)
    window = App(mgr)
    mgr.on_image = window.on_new_frame
    window.show()
    sys.exit(app.exec_())

