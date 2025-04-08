import json
import os
from PyQt5.QtCore import QObject, pyqtSignal


class SettingsManager(QObject):
    settings_changed = pyqtSignal(dict)

    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_file='settings.json'):
        if self._initialized:
            return
        super().__init__()
        self._settings = {}
        self.config_file = config_file
        self.load_defaults()
        self.load_from_file()
        self._initialized = True

    def load_defaults(self):
        self._settings = {
            "ostov_size": 3,
            "p_dop": 0.1,
            "time_sleep": 0.2,
            "use_filter": True,
            "is_webcam": True,
            "rtsp_or_path": ""
        }

    @property
    def settings(self):
        return self._settings.copy()

    def load_from_file(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    self._settings.update(json.load(f))
            else:
                self.save_to_file()
                print(f"Created new config file: {self.config_file}")
        except Exception as e:
            print(f"Error loading settings: {e}")
            self.save_to_file()
            print("Recreated config file with default settings")

    def save_to_file(self):
        try:
            with open(self.config_file, "w") as f:
                json.dump(self._settings, f, indent=4)
            self.settings_changed.emit(self.settings)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def update_settings(self, new_settings):
        self._settings.update(new_settings)
        self.save_to_file()


settings_manager = SettingsManager()