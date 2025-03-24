


class DataModel(object):
    def __init__(self):
        self._alpha: float = 0.95
        self._activity_alpha: float = 0.9
        self._activity_threshold: float = 0.3
        self._min_object_area: int = 500
        self.rtsp_or_path = None
        self.is_webcam: bool = False

    def change_settings(self, _alpha, _activity_alpha, _activity_threshold, _min_object_area):
        self._alpha = _alpha
        self._activity_alpha = _activity_alpha
        self._activity_threshold = _activity_threshold
        self._min_object_area = _min_object_area

    def get_model_settings(self):
        return self._alpha, self._activity_alpha, self._activity_threshold, self._min_object_area
