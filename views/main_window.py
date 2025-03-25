import numpy as np
from PyQt5.QtGui import QImage, QPixmap, QPainter, QFont, QPen
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QEvent, QRect

from views.ui.main import Ui_MainWindow
from views.settings_dialog import SettingsDialog
from models.data_model import DataModel
from views.drawing_widget import DrawingWidget


class MainWindow(QMainWindow):

    signal_run = pyqtSignal(bool)
    signal_send_rect = pyqtSignal(int, int, int, int)

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

        self.change_resource()

        self.drawing_widget = DrawingWidget(self.ui.lbl_frame)
        self.drawing_widget.setGeometry(0, 0, self.ui.lbl_frame.width(), self.ui.lbl_frame.height())
        self.drawing_widget.rectangle_drawn.connect(self.handle_rectangle)
        self.drawing_widget.hide()
        self.ui.lbl_frame.installEventFilter(self)
        self.current_scaled_rect = None
        self.scale_factor_x = 1.0
        self.scale_factor_y = 1.0

        self.detect = False

    def init_signals(self):
        self.ui.btn_settings.clicked.connect(lambda: self.dialog.show())
        self.ui.cb_webcam.clicked.connect(self.change_resource)
        self.ui.btn_start.clicked.connect(self.run)
        self.ui.lbl_path.textChanged.connect(self.change_path)
        self.dialog.ui.cb_filter.clicked.connect(self.change_filter_status)

    @pyqtSlot(np.ndarray)
    def put_frame(self, frame):
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)

        temp_pixmap = pixmap.scaled(
            self.ui.lbl_frame.width(),
            self.ui.lbl_frame.height(),
            Qt.KeepAspectRatio
        )

        painter = QPainter(temp_pixmap)

        if self.detect:
            font = QFont()
            font.setPointSize(20)
            font.setBold(True)
            painter.setFont(font)

            painter.setPen(QPen(Qt.black, 4))
            painter.drawText(temp_pixmap.rect(), Qt.AlignCenter, "ДВИЖЕНИЕ!")

            painter.setPen(QPen(Qt.red, 2))
            painter.drawText(temp_pixmap.rect(), Qt.AlignCenter, "ДВИЖЕНИЕ!")

        painter.end()

        self.ui.lbl_frame.setPixmap(temp_pixmap)

        frame_width = self.ui.lbl_frame.width()
        frame_height = self.ui.lbl_frame.height()
        ratio = w / h

        if frame_width / frame_height > ratio:
            scaled_w = int(frame_height * ratio)
            scaled_h = frame_height
        else:
            scaled_w = frame_width
            scaled_h = int(frame_width / ratio)

        x_offset = (frame_width - scaled_w) // 2
        y_offset = (frame_height - scaled_h) // 2

        self.current_scaled_rect = QRect(x_offset, y_offset, scaled_w, scaled_h)
        self.scale_factor_x = w / scaled_w
        self.scale_factor_y = h / scaled_h

        self.drawing_widget.show()

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

    def change_path(self):
        self.model.rtsp_or_path = self.ui.lbl_path.text()

    def change_filter_status(self):
        self.model.use_filter = self.dialog.ui.cb_filter.isChecked()
        print('change filter status')

    def run(self):
        if self.ui.btn_start.isChecked():
            self.signal_run.emit(True)
        else:
            self.signal_run.emit(False)

    def clear_holst(self):
        self.ui.lbl_frame.clear()
        self.ui.lbl_bin.clear()

    def eventFilter(self, source, event):
        if source == self.ui.lbl_frame and event.type() == QEvent.Resize:
            self.drawing_widget.setGeometry(0, 0,
                                            source.width(),
                                            source.height()
                                            )
        return super().eventFilter(source, event)

    def handle_rectangle(self, rect):
        if not self.current_scaled_rect:
            return

        intersected = rect.intersected(self.current_scaled_rect)
        if intersected.isValid():
            x = (intersected.x() - self.current_scaled_rect.x()) * self.scale_factor_x
            y = (intersected.y() - self.current_scaled_rect.y()) * self.scale_factor_y
            width = intersected.width() * self.scale_factor_x
            height = intersected.height() * self.scale_factor_y

            x_int = int(round(x))
            y_int = int(round(y))
            width_int = int(round(width))
            height_int = int(round(height))

            print(f"Original coordinates: X={x_int}, Y={y_int}, W={width_int}, H={height_int}")

            self.signal_send_rect.emit(x_int, y_int, width_int, height_int)

    def put_detect_status(self, detect):
        self.detect = detect
