import numpy as np
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt

from views.ui.main import Ui_MainWindow
from views.settings_dialog import SettingsDialog
from models.data_model import DataModel


class MainWindow(QMainWindow):

    signal_run = pyqtSignal(bool)

    def __init__(self, model: DataModel):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.model = model
        self.dialog = SettingsDialog(self)
        self.init_ui()
        self.init_signals()

    def init_ui(self):
        self.ui.setupUi(self)
        self.ui.lbl_frame.setScaledContents(False)
        self.ui.lbl_frame.setAlignment(Qt.AlignCenter)

        self.ui.lbl_bin.setScaledContents(False)
        self.ui.lbl_bin.setAlignment(Qt.AlignCenter)

    def init_signals(self):
        self.ui.btn_settings.clicked.connect(lambda: self.dialog.show())
        self.ui.cb_webcam.clicked.connect(self.change_resource)
        self.ui.btn_start.clicked.connect(self.run)

    @pyqtSlot(np.ndarray)
    def put_frame(self, frame):
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.ui.lbl_frame.setPixmap(
            pixmap.scaled(
                self.ui.lbl_frame.width(),
                self.ui.lbl_frame.height(),
                Qt.KeepAspectRatio
            )
        )

    @pyqtSlot(np.ndarray)
    def put_bin_frame(self, frame):
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.ui.lbl_bin.setPixmap(
            pixmap.scaled(
                self.ui.lbl_bin.width(),
                self.ui.lbl_bin.height(),
                Qt.KeepAspectRatio
            )
        )

    def change_resource(self):
        if self.ui.cb_webcam.isChecked():
            self.ui.lbl_path.setEnabled(False)
            self.model.is_webcam = True
        else:
            self.ui.lbl_path.setEnabled(True)
            self.model.is_webcam = False

    def run(self):
        if self.ui.btn_start.isChecked():
            self.signal_run.emit(True)
        else:
            self.signal_run.emit(False)