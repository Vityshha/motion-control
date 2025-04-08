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
        self.ui.p_dop.setValue(settings["p_dop"])
        self.ui.ostov_size.setValue(settings["ostov_size"])
        self.ui.time_sleep.setValue(settings["time_sleep"])
        self.ui.cb_filter.setChecked(settings["use_filter"])

    def _save_settings(self):
        new_settings = {
            "p_dop": self.ui.p_dop.value(),
            "ostov_size": self.ui.ostov_size.value(),
            "time_sleep": self.ui.time_sleep.value(),
            "use_filter": self.ui.cb_filter.isChecked()
        }
        settings_manager.update_settings(new_settings)
        self.close()