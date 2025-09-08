import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from StreamServer import StreamServer
from ClickableImage import ClickableImage


class App(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        self.image_widget = ClickableImage(None)  # will set socket later
        layout.addWidget(self.image_widget)
        self.setLayout(layout)

        self.setWindowTitle("Depthgram UI (Python)")

        # Start server with callback that updates the widget
        self.socket_manager = StreamServer(on_frame=self.on_new_frame)
        self.image_widget.socket_manager = self.socket_manager
        self.socket_manager.start_server()

    def on_new_frame(self, qimg):
        # This is called from a background thread → use signal/slot or invokeLater
        self.image_widget.update_frame(qimg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())

