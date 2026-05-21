# Instagram Reels Factory: удивительные факты

Автоматический пайплайн генерирует русскоязычный Instagram Reel в нише «удивительные факты»: сценарий через Gemini/Groq, озвучка Edge-TTS, word-level субтитры, вертикальный монтаж 1080×1920 и публикация через официальный Instagram Graph API. GitHub Actions запускает workflow 2 раза в день: `0 6,15 * * *` UTC, то есть 9:00 и 18:00 МСК.

## Что получается

- MP4 `1080×1920`, `30fps`, `H.264/AAC`, длительность целится в `30–45` секунд.
- Субтитры в CapCut-viral стиле: 1–3 слова, жирный sans-serif с кириллицей, белый текст с толстой чёрной обводкой, центр-низ.
- Без GPU и без платных сервисов.
- Без реальных секретов в коде: все ключи задаются через GitHub Actions Secrets или локальный `.env`.
- Локальный dry-run без ключей: `USE_MOCK_LLM=1 PUBLISH=0`.

## Нужные ключи

1. `GEMINI_API_KEY` — Google AI Studio: https://aistudio.google.com/app/apikey  
   Используется модель `gemini-2.5-flash` для идеи и сценария.
2. `PEXELS_API_KEY` — Pexels API: https://www.pexels.com/api/  
   Нужен для стоковых вертикальных видео. Если видео мало или ключа нет, пайплайн добирает визуалы через Pollinations.ai, а при сетевой ошибке создаёт локальные placeholder-визуалы.
3. `IG_USER_ID` и `IG_ACCESS_TOKEN` — Instagram Graph API: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/  
   Нужен Instagram Professional account и приложение Meta. Токен должен иметь права на публикацию контента.
4. `GROQ_API_KEY` — опциональный fallback: https://console.groq.com/keys  
   Используется `llama-3.3-70b-versatile`, если Gemini недоступен.

`GITHUB_TOKEN` в Actions создаётся автоматически. Для локальной публикации в GitHub Releases можно использовать PAT с `contents:write`.

## Настройка GitHub Secrets

В репозитории откройте `Settings → Secrets and variables → Actions → New repository secret` и добавьте:

- `GEMINI_API_KEY`
- `PEXELS_API_KEY`
- `IG_USER_ID`
- `IG_ACCESS_TOKEN`
- `GROQ_API_KEY` — опционально

В `Settings → Secrets and variables → Actions → Variables` можно добавить:

- `TTS_VOICE=ru-RU-DmitryNeural` или `ru-RU-SvetlanaNeural`
- `USE_MUSIC=1` или `0`

## Первый локальный запуск

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
USE_MOCK_LLM=1 PUBLISH=0 python -m reels_factory.pipeline
```

Готовый ролик появится в `out/reel_<timestamp>.mp4`.

Для полностью офлайн-проверки визуалов можно добавить:

```bash
USE_MOCK_LLM=1 PUBLISH=0 USE_LOCAL_VISUALS=1 python -m reels_factory.pipeline
```

## Первый запуск в GitHub Actions

1. Добавьте Secrets.
2. Откройте вкладку `Actions`.
3. Выберите workflow `Instagram Reels Factory`.
4. Нажмите `Run workflow`.
5. Workflow соберёт MP4, загрузит его в GitHub Releases и передаст публичный `browser_download_url` в Instagram Graph API.

## Как поменять нишу, голос и расписание

- Ниша: переменная `NICHE` или значение по умолчанию в `reels_factory/config.py`.
- Подтемы: список `SUBTOPICS` в `reels_factory/config.py`.
- Голос: `TTS_VOICE=ru-RU-DmitryNeural` или `ru-RU-SvetlanaNeural`.
- Частота: cron в `.github/workflows/reels.yml`.
- Музыка: положите только CC0/CC-BY треки в `assets/music/` или задайте `MUSIC_PATH`. В репозиторий не добавлены треки с непроверенной лицензией.

## Публикация

При `PUBLISH=1` пайплайн:

1. Создаёт GitHub Release `reels-<timestamp>`.
2. Загружает MP4 как asset.
3. Берёт публичный URL.
4. Создаёт Instagram Reels media container:
   `POST /{ig-user-id}/media?media_type=REELS&video_url=...`
5. Проверяет `status_code` до `FINISHED`.
6. Публикует через `POST /{ig-user-id}/media_publish`.

Не используются `instagrapi` и другие неофициальные Instagram-библиотеки.

## Troubleshooting

- **Pexels не нашёл стоки.** Проверьте `PEXELS_API_KEY`; пайплайн автоматически добирает изображения Pollinations.ai. Для теста без сети используйте `USE_LOCAL_VISUALS=1`.
- **Instagram container застрял в `IN_PROGRESS`.** Проверьте, что GitHub Release asset публично скачивается без авторизации, видео соответствует ограничениям Reels, токен действителен, а аккаунт Instagram Professional. Пайплайн ждёт до 5 минут.
- **Токен Instagram истекает.** Долгоживущий токен нужно обновлять примерно раз в 60 дней через Meta Graph API/Meta Developers и заменить `IG_ACCESS_TOKEN` в GitHub Secrets.
- **Нет субтитров на Linux.** Проект рендерит подписи через Pillow PNG overlays и использует `assets/fonts/Inter-Black.ttf`/Manrope с кириллицей; ImageMagick не требуется.
- **Edge-TTS недоступен.** Для CI-testability есть silent fallback, но для боевого канала лучше перезапустить job: основной путь использует Edge-TTS word boundary events.

## Тесты

```bash
pip install -r requirements.txt
USE_MOCK_LLM=1 PUBLISH=0 python -m reels_factory.pipeline
pytest tests/
```

Проверка параметров итогового файла:

```bash
ffprobe -v error -show_streams -show_format out/reel_<timestamp>.mp4
```
