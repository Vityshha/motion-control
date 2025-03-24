from PyQt5.QtCore import QRect, QPoint, Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPen

class DrawingWidget(QWidget):
    rectangle_drawn = pyqtSignal(QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.drawing = False
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.current_rect = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.current_rect = None
            self.update()

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            self.current_rect = QRect(self.start_point, self.end_point).normalized()
            self.rectangle_drawn.emit(self.current_rect)
            self.update()

    def paintEvent(self, event):
        if self.drawing or self.current_rect:
            painter = QPainter(self)
            painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
            rect = self.current_rect if self.current_rect else QRect(self.start_point, self.end_point).normalized()
            painter.drawRect(rect)