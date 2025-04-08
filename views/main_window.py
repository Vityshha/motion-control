import numpy as np
from PyQt5.QtGui import QImage, QPixmap, QPainter, QFont, QPen, QFontMetrics
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QEvent, QRect

from views.ui.main import Ui_MainWindow
from views.settings_dialog import SettingsDialog
from models.settings_manager import settings_manager
from views.drawing_widget import DrawingWidget


class MainWindow(QMainWindow):
    signal_run = pyqtSignal(bool)
    signal_send_rect = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.dialog = SettingsDialog(self)
        self.drawing_widget = None
        self.current_scaled_rect = None
        self.scale_factors = (1.0, 1.0)
        self.detect = []

        self.init_ui()
        self.init_signals()
        self.setup_drawing_widget()

    # region Initialization
    def init_ui(self):
        self.ui.setupUi(self)
        self.setup_frame_labels()
        self._update_ui_settings(settings_manager.settings)

    def setup_frame_labels(self):
        for label in [self.ui.lbl_frame, self.ui.lbl_bin]:
            label.setScaledContents(False)
            label.setAlignment(Qt.AlignCenter)

    def setup_drawing_widget(self):
        self.drawing_widget = DrawingWidget(self.ui.lbl_frame)
        self.drawing_widget.setGeometry(0, 0,
                                        self.ui.lbl_frame.width(),
                                        self.ui.lbl_frame.height()
                                        )
        self.drawing_widget.rectangle_drawn.connect(self.handle_rectangle)
        self.drawing_widget.clear_rectangles.connect(self.handle_rectangle)
        self.drawing_widget.hide()
        self.ui.lbl_frame.installEventFilter(self)

    def init_signals(self):
        self.ui.btn_settings.clicked.connect(self.dialog.show)
        self.ui.cb_webcam.clicked.connect(self._handle_webcam_change)
        self.ui.btn_start.clicked.connect(self.run)
        self.ui.lbl_path.textChanged.connect(self._handle_path_change)
        settings_manager.settings_changed.connect(self._update_ui_settings)

    # endregion

    # region Video Processing
    @pyqtSlot(np.ndarray, np.ndarray)
    def put_frame(self, rgb_frame, bin_frame):
        self.process_rgb_frame(rgb_frame)
        self.process_bin_frame(bin_frame)
        self.update_scaling_factors(rgb_frame.shape)
        self.drawing_widget.show()

    def process_rgb_frame(self, frame):
        pixmap = self.create_pixmap(frame, self.ui.lbl_frame.size())
        if len(self.detect) > 0:
            self.add_detection_text(pixmap, self.detect)
        self.ui.lbl_frame.setPixmap(pixmap)

    def process_bin_frame(self, frame):
        pixmap = self.create_pixmap(frame, self.ui.lbl_bin.size())
        self.ui.lbl_bin.setPixmap(pixmap)

    def create_pixmap(self, frame, target_size):
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(q_img).scaled(
            target_size.width(),
            target_size.height(),
            Qt.KeepAspectRatio
        )

    def add_detection_text(self, pixmap, detections):
        painter = QPainter(pixmap)
        try:
            painter.setRenderHint(QPainter.Antialiasing)

            for detection in detections:
                if detection['activity'] <= 0:
                    continue

                status_move = 'Не допустимое' if detection['detected'] else 'Допустимое'
                text = f"{status_move}: p={detection['activity']:.1%}"

                x = int(detection['roi'][0] / self.scale_factors[0])
                y = int(detection['roi'][1] / self.scale_factors[1])
                w = int(detection['roi'][2] / self.scale_factors[0])
                h = int(detection['roi'][3] / self.scale_factors[1])

                # Рисуем красную рамку (сначала, чтобы фон текста её не перекрывал)
                painter.setPen(QPen(Qt.red, 2))
                painter.setBrush(Qt.NoBrush)  # Убедимся, что заливка отключена
                painter.drawRect(x, y, w, h)

                # Настройки шрифта
                font = QFont()
                font.setBold(True)
                painter.setFont(font)

                # Параметры отступов
                padding = 5
                margin = 2
                max_text_width = w - 2 * padding
                max_text_height = h // 3  # Увеличим допустимую высоту

                # Подбираем размер шрифта
                font_size = 12
                while font_size >= 8:
                    font.setPointSize(font_size)
                    metrics = QFontMetrics(font)
                    text_width = metrics.horizontalAdvance(text)
                    text_height = metrics.height()

                    if text_width <= max_text_width and text_height <= max_text_height:
                        break
                    font_size -= 1

                # Вычисляем позицию текста и фона
                text_x = x + padding
                text_y = y + padding + metrics.ascent()

                # Размеры фона (с учётом margin)
                bg_width = metrics.horizontalAdvance(text) + 2 * margin
                bg_height = metrics.height() + 2 * margin
                bg_x = text_x - margin
                bg_y = text_y - metrics.ascent() - margin

                # Рисуем фон (только вокруг текста!)
                painter.setBrush(Qt.white)
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(bg_x, bg_y, bg_width, bg_height, 3, 3)

                # Рисуем текст
                painter.setPen(Qt.black)
                painter.drawText(text_x, text_y, text)

                # Сбрасываем кисть и перо для следующей итерации
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(Qt.red, 2))

        finally:
            painter.end()

    # endregion

    # region ROI Handling
    @pyqtSlot(list)
    def handle_rectangle(self, rectangles):
        valid_rects = [self.convert_rect(rect) for rect in rectangles]
        self.signal_send_rect.emit(valid_rects)

    def convert_rect(self, rect):
        if not self.current_scaled_rect:
            return None

        intersected = rect.intersected(self.current_scaled_rect)
        if not intersected.isValid():
            return None

        x = (intersected.x() - self.current_scaled_rect.x()) * self.scale_factors[0]
        y = (intersected.y() - self.current_scaled_rect.y()) * self.scale_factors[1]
        width = intersected.width() * self.scale_factors[0]
        height = intersected.height() * self.scale_factors[1]

        return [
            int(round(x)),
            int(round(y)),
            int(round(width)),
            int(round(height))
        ]

    def eventFilter(self, source, event):
        if source == self.ui.lbl_frame and event.type() == QEvent.Resize:
            self.drawing_widget.setGeometry(0, 0,
                                            source.width(),
                                            source.height()
                                            )
        return super().eventFilter(source, event)

    # endregion

    # region Settings and Resources
    def _update_ui_settings(self, settings):
        self.ui.cb_webcam.setChecked(settings["is_webcam"])
        self.ui.lbl_path.setText(settings["rtsp_or_path"])
        self.ui.lbl_path.setEnabled(not settings["is_webcam"])

    def _handle_webcam_change(self):
        settings_manager.update_settings({
            "is_webcam": self.ui.cb_webcam.isChecked()
        })

    def _handle_path_change(self):
        settings_manager.update_settings({
            "rtsp_or_path": self.ui.lbl_path.text()
        })

    # endregion

    # region Detection Control
    @pyqtSlot()
    def run(self):
        self.signal_run.emit(self.ui.btn_start.isChecked())

    @pyqtSlot(list)
    def put_detect_status(self, detect):
        self.detect = detect
        print(f'Detection status: {detect}')

    # endregion

    # region Utility Methods
    def update_scaling_factors(self, frame_shape):
        frame_w, frame_h = frame_shape[1], frame_shape[0]
        label_w = self.ui.lbl_frame.width()
        label_h = self.ui.lbl_frame.height()

        ratio = frame_w / frame_h
        if label_w / label_h > ratio:
            scaled_w = int(label_h * ratio)
            scaled_h = label_h
        else:
            scaled_w = label_w
            scaled_h = int(label_w / ratio)

        self.current_scaled_rect = QRect(
            (label_w - scaled_w) // 2,
            (label_h - scaled_h) // 2,
            scaled_w,
            scaled_h
        )

        self.scale_factors = (
            frame_w / scaled_w,
            frame_h / scaled_h
        )

    def clear_holst(self):
        self.ui.lbl_frame.clear()
        self.ui.lbl_bin.clear()
    # endregion