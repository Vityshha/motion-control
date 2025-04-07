from PyQt5.QtCore import QRect, QPoint, Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPen


class DrawingWidget(QWidget):
    rectangle_drawn = pyqtSignal(list)
    clear_rectangles = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.drawing = False
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.rectangles = []
        self.current_rect = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.update()
        elif event.button() == Qt.RightButton:
            self.rectangles.clear()
            self.current_rect = None
            self.clear_rectangles.emit([])
            self.update()

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            rect = QRect(self.start_point, self.end_point).normalized()
            if rect.isValid():
                self.rectangles.append(rect)
                self.rectangle_drawn.emit(self.rectangles)
            self.current_rect = None
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))

        for rect in self.rectangles:
            painter.drawRect(rect)

        if self.drawing:
            rect = QRect(self.start_point, self.end_point).normalized()
            painter.drawRect(rect)