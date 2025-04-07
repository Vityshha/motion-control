import sys
from PyQt5.QtWidgets import QApplication
from views.main_window import MainWindow
from controllers.main_controller import MainController


class Application:
    def __init__(self):
        self.view = MainWindow()
        self.controller = MainController(self.view)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    application = Application()
    application.view.show()
    sys.exit(app.exec_())


