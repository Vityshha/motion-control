from PyQt5.QtWidgets import QDialog
from views.ui.settings import Ui_Dialog


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.ui.btn_save.clicked.connect(lambda: self.close())

    def get_settings(self):
        return self.ui.alpha.value(), self.ui.activity_alpha.value(), self.ui.activity_threshold.value(), self.ui.detection_threshold.value()/100, self.ui.min_object_area.value()