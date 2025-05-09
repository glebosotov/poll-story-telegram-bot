# Проект интерактивной истории на базе Telegram-бота и LLM

Этот проект представляет собой Telegram-бота, который ведёт интерактивную историю в стиле киберпанка, используя OpenAI и Google Gemini (Imagen) для генерации текстовых продолжений и иллюстраций.

## Функциональность

* Автоматическая генерация продолжения истории на русском языке с помощью OpenAI (функция `generate_story_continuation_openai`).
* Генерация вариантов опроса для дальнейшего развития сюжета (функция `generate_poll_options_openai`).
* Формирование промптов для генерации изображений (функция `generate_imagen_prompt`).
* Генерация иллюстраций к сценам истории с помощью Google Gemini Imagen (функция `make_gemini_image`).
* Хранение состояния истории, публикация сообщений и опросов в указанный канал Telegram.

## Требования

* Python 3.9+
* Установленные зависимости из `requirements.txt` (примерный список ниже):

  ```text
  python-dotenv
  openai
  google-genai
  python-telegram-bot
  ```

## Установка

1. Склонируйте репозиторий:

   ```bash
   git clone <URL_репозитория>
   cd <папка_проекта>
   ```

2. Создайте и активируйте виртуальное окружение:

   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate    # Windows
   ```

3. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```

## Конфигурация

1. Скопируйте файл окружения и переименуйте его:

   ```bash
   cp .env.example .env
   ```

2. Откройте `.env` и заполните значения:

   ```dotenv
   # Telegram-бот
   BOT_TOKEN="<токен_бота>"
   CHANNEL_ID="<ID_канала_или_чата>"

   # Режим отладки
   DRY_RUN=true  # true — не сохранять состояние в файл (для тестирования)

   # OpenAI (текст)
   OPENAI_API_KEY="<ключ_OpenAI>"
   OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
   OPENAI_MODEL="gemini-2.5-pro-preview-05-06"

   # Google Gemini (Imagen)
   GEMINI_API_KEY="<ключ_Gemini>"
   GEMINI_IMAGE_MODEL=imagen-3.0-generate-002
   IMAGE_PROMPT_START="<начальный_промпт_для_изображений>"

   # Ограничения контекста и длины истории
   MAX_CONTEXT_CHARS=150000
   STORY_MAX_SENTENCES=500
   ```

## Запуск

```bash
python main.py
```

* Скрипт проверит конфигурацию (`validate_config`), затем загрузит текущее состояние и выполнит один шаг истории (`run_story_step`).
* При первом запуске публикуется начальная идея истории (`INITIAL_STORY_IDEA`).
* Далее бот генерирует новое продолжение, публикует текст и изображение, создаёт опрос.
* Результаты опроса влияют на дальнейшую логику сюжета.

## Структура проекта

```text
├── .env.example        # Пример файла окружения
├── main.py             # Точка входа скрипта
├── open_ai_gen.py      # Функции для работы с OpenAI (текст и промпты)
├── image_gen.py        # Функция генерации изображений через Google Gemini Imagen
├── state.py            # Модуль сохранения/загрузки состояния истории
├── requirements.txt    # Зависимости проекта
└── README.md           # Документация (этот файл)
```

## Описание ключевых модулей

* **main.py**

  * Настройка логирования.
  * Загрузка `.env`.
  * Функция `run_story_step` — единичный шаг обработки: остановка предыдущего опроса, генерация продолжения, публикация текста, изображений и опроса.

* **open\_ai\_gen.py**

  * `generate_story_continuation_openai` — получает от OpenAI функцию продолжения истории с жёсткими правилами форматирования.
  * `generate_poll_options_openai` — получает 4 варианта ответов для опроса.
  * `generate_imagen_prompt` — формирует оптимизированный промпт для генерации изображения.

* **image\_gen.py**

  * `make_gemini_image` — отправляет запрос к Google Gemini Imagen и возвращает байты изображения.

* **state.py**

  * Функции `load_state` и `save_state` для хранения текущего текста истории, ID последнего опроса и флага завершения.
