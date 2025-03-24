from models.data_model import DataModel
from views.main_window import MainWindow
from utils.detect import MotionDetector


class MainController:
    def __init__(self, model: DataModel, views: MainWindow):
        self.model = model
        self.views = views
        self.detector = MotionDetector()

        self.connect()

    def connect(self):
        self.views.dialog.ui.btn_save.clicked.connect(self.save_settings)
        self.views.signal_run.connect(self.algo_run)
        self.detector.signal_send_frame.connect(self.views.put_frame)
        self.detector.signal_send_binary_frame.connect(self.views.put_bin_frame)
        self.views.signal_send_rect.connect(self.detector.set_detection_roi)
        self.detector.worker.detection_signal.connect(self.detect_move_in_frame)

    def save_settings(self):
        alpha, activity_alpha, activity_threshold, detection_threshold, min_object_area = self.views.dialog.get_settings()
        self.model.change_settings(alpha, activity_alpha, activity_threshold, detection_threshold, min_object_area)
        self.change_settings()

    def algo_run(self, launch):
        if launch:
            self.detector.start()
        else:
            self.detector.stop()
            self.views.clear_holst()

    def change_settings(self):
        alpha, activity_alpha, activity_threshold, detection_threshold, min_object_area = self.model.get_model_settings()
        self.detector.update_settings(alpha, activity_alpha, activity_threshold, detection_threshold, min_object_area)

    def detect_move_in_frame(self, detect: bool):
        self.views.put_detect_status(detect)