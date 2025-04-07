from PyQt5.QtWidgets import QDialog
from views.ui.settings import Ui_Dialog
from models.settings_manager import settings_manager


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.ui.btn_save.clicked.connect(self._save_settings)
        self._load_current_settings()

    def _load_current_settings(self):
        settings = settings_manager.settings
        self.ui.alpha.setValue(settings["alpha"])
        self.ui.activity_alpha.setValue(settings["activity_alpha"])
        self.ui.activity_threshold.setValue(settings["activity_threshold"])
        self.ui.detection_threshold.setValue(int(settings["detection_threshold"] * 100))
        self.ui.min_object_area.setValue(settings["min_object_area"])
        self.ui.cb_filter.setChecked(settings["use_filter"])

    def _save_settings(self):
        new_settings = {
            "alpha": self.ui.alpha.value(),
            "activity_alpha": self.ui.activity_alpha.value(),
            "activity_threshold": self.ui.activity_threshold.value(),
            "detection_threshold": self.ui.detection_threshold.value() / 100,
            "min_object_area": self.ui.min_object_area.value(),
            "use_filter": self.ui.cb_filter.isChecked()
        }
        settings_manager.update_settings(new_settings)
        self.close()