import cv2
import numpy as np

# Параметры
alpha = 0.95               # Коэффициент забывания для накопленной разницы
activity_alpha = 0.9       # Коэффициент забывания для карты активности
activity_threshold = 0.9   # Порог активности (0.3 = 30% кадров в окне)
min_object_area = 500      # Минимальная площадь объекта (для фильтрации шума)

cap = cv2.VideoCapture(0)  # Или путь к видео

# Инициализация
accumulated_diff = None
activity_map = None        # Карта активности (0..1)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Предобработка
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    if accumulated_diff is None:
        accumulated_diff = gray.astype("float32")
        activity_map = np.zeros_like(gray, dtype="float32")
        continue

    # 1. Вычисляем разницу с накопленным кадром
    current_diff = cv2.absdiff(gray, cv2.convertScaleAbs(accumulated_diff))
    _, threshold_diff = cv2.threshold(current_diff.astype("uint8"), 25, 255, cv2.THRESH_BINARY)

    # 2. Обновляем накопленную разницу
    accumulated_diff = alpha * accumulated_diff + (1 - alpha) * gray.astype("float32")

    # 3. Обновляем карту активности (0 = нет изменений, 1 = есть изменения)
    activity_map = activity_alpha * activity_map + (1 - activity_alpha) * (threshold_diff / 255.0)

    # 4. Бинаризация по порогу активности
    _, object_mask = cv2.threshold((activity_map * 255).astype("uint8"),
                                  int(activity_threshold * 255), 255, cv2.THRESH_BINARY)

    # 5. Удаляем мелкие шумы (морфология + площадь)
    object_mask = cv2.morphologyEx(object_mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(object_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    object_mask_filtered = np.zeros_like(object_mask)
    for cnt in contours:
        if cv2.contourArea(cnt) > min_object_area:
            cv2.drawContours(object_mask_filtered, [cnt], -1, 255, -1)

    # Вывод
    cv2.imshow("Original", frame)
    cv2.imshow("Threshold Diff", threshold_diff)
    cv2.imshow("Activity Map", (activity_map * 255).astype("uint8"))
    cv2.imshow("Detected Objects", object_mask_filtered)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()