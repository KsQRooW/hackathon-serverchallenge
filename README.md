# hackathon-serverchallenge
Хакатон по поиску и анализу данных от Северстали и McKinsey 2022

> Презентация: presentation.pdf

## Задача
Задача состоит из нескольких блоков:
1. разработка алгоритма для парсинга товаров;
2. исследование возможных данных во внешних источниках;
3. разработка программы подготовки информации в требуемом разрезе (товар vs поставщик vs рейтинг поставщика);

На выходе – воспроизводимый код и презентация сервиса.
## Требования
- Google Chrome 99.0.4844.74
- Python 3.10
- pip 22.0.4
- Библиотеки:
  - requests
  - bs4
  - lxml
  - time
  - openpyxl
  - re
  - datetime
  - string
  - pymorphy3
  - selenium
## Запуск
### Автоматический запуск
Запустить файл `run.bat` в папке проекта
### Ручной запуск через консоль
Перейти в папку проекта, например:
```
cd Documents\GitHub\hackathon-serverchallenge
```
Установить необходимые библиотеки
```
pip install -r requirements.txt
```
Запустить main.py
```
python main.py
```
