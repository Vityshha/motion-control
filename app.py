import sys
from PyQt5.QtWidgets import QApplication
from models.data_model import DataModel
from views.main_window import MainWindow
from controllers.main_controller import MainController


class Application:
    def __init__(self):
        self.model = DataModel()
        self.view = MainWindow(self.model)
        self.controller = MainController(self.model, self.view)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    application = Application()
    application.view.show()
    sys.exit(app.exec_())


