# motion-control

### Контроль движения в видеопотоке с помощью удаленного видео-анализа 


#### Функционал: 

```angular2html
1) Создание зоны интереса 
2) Функционал настройки параметров 
3) Захват кадров: rtsp-поток или путь к видео-файлу 
4) Уведомление о движении в области зоны интереса
```

#### Настраиваемые параметры:

```angular2html
alpha - коэффициент забывания для фоновой модели (0, 1)
activity_alpha - коэффициент забывания для карты активности
activity_threshold - порог бинаризации для карты активности

detection_threshold - процент активных пикселей в ROI для детекции
min_object_area - минимальная площадь контура для учета 
use_filter - флаг для применения морфологической фильтрации
```

### Примеры детекции движения
![Обнаружение движения](case_1.png)
![Обнаружение движения](case_2.png)


#### Если нужно изменить ui:

```angular2html
pyuic5 .\main.ui -o main.py
pyuic5 .\settings.ui -o settings.py
```

```angular2html
pyrcc5 res.qrc -o res_rc.py
```

```angular2html
import views.ui.res_rc
```