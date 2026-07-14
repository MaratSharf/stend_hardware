# История изменений — 14 июля 2026

## Версия 4.8.0

### Healthcheck endpoint

- **Добавлен `GET /api/health`** — эндпоинт проверки работоспособности системы (без авторизации)
- Возвращает:
  - `status`: `ok` (200) или `degraded` (503)
  - `uptime`: время работы с момента старта (секунды)
  - `components.database`: статус подключения к БД + latency
  - `components.owen`: статус ОВЕН (`ok`/`disconnected`/`no_controller`) + IP
  - `components.camera`: статус камеры (`ok`/`disconnected`/`no_controller`) + IP
- Файл: `web/pages/health.py`

### Обновлена документация

- `README.md` — добавлен health endpoint в таблицу API, обновлена структура проекта, версия 4.8.0
- `IMPROVEMENTS.md` — пункт #8 отмечен как решённый
- `KODA.md` — добавлен health endpoint в таблицу API и структуру проекта
