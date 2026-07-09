# Развертывание на ALT Linux

## Требования

- ALT Linux (p9, p10, Sisyphus)
- Python 3.8+
- PostgreSQL 14+
- Сетевой доступ к оборудованию (ОВЕН: 192.168.1.99, камера: 192.168.1.36)

## 1. Установка системных зависимостей

```bash
# Обновление пакетов
sudo apt-get update

# Установка Python и необходимых пакетов
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    gcc \
    make \
    libpq-dev \
    postgresql \
    postgresql-client \
    postgresql-server \
    systemd
```

## 2. Настройка PostgreSQL

### Запуск PostgreSQL
```bash
# Инициализация (если не выполнена)
sudo postgresql-setup --initdb

# Запуск сервиса
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### Создание базы данных и пользователя
```bash
# Подключение к PostgreSQL
sudo -u postgres psql

# Создание пользователя и базы данных
CREATE USER stend WITH PASSWORD 'Alexej@12';
CREATE DATABASE stend_hardware OWNER stend;
GRANT ALL PRIVILEGES ON DATABASE stend_hardware TO stend;

# Выход из psql
\q
```

### Настройка аутентификации
Отредактируйте `/var/lib/pgsql/data/pg_hba.conf`:

```bash
# Найдите строку:
# local   all             all                                     peer

# Замените на:
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
```

Перезапустите PostgreSQL:
```bash
sudo systemctl restart postgresql
```

## 3. Установка приложения

### Вариант А: Клонирование репозитория
```bash
# Переход в директорию развертывания
cd /home/marat/proj

# Клонирование (или копирование файлов)
git clone <repository_url> stend_hardware
cd stend_hardware
```

### Вариант Б: Установка из ZIP-архива

#### Подготовка ZIP-файла на Windows

1. **Создание ZIP-архива** (на Windows):
   ```powershell
   # В PowerShell или проводнике Windows:
   # Выделите папку stend_hardware → ПКМ → Отправить → Сжатая папка
   # Или через командную строку:
   cd C:\proj\python\git_stend
   tar -a -c -f stend_hardware.zip stend_hardware
   ```

2. **Что НЕ включать в архив** (если создаете вручную):
   - Папка `venv/` (создается заново на Linux)
   - Папка `__pycache__/` (не нужна)
   - Папка `.git/` (не нужна)
   - Файл `.env` (создается заново с паролями сервера)

3. **Что ДОЛЖНО быть в архиве**:
   - `run.py`
   - `config.yaml`
   - `requirements.txt`
   - `init_postgres.py`
   - `create_admin.py`
   - Папки: `core/`, `hardware/`, `web/`, `utils/`
   - (опционально) `data/` — если хотите сохранить изображения и логи

#### Перенос ZIP-файла на сервер

```bash
# Вариант 1: scp (из терминала Windows)
scp stend_hardware.zip root@192.168.1.100:/tmp/

# Вариант 2: SFTP-клиент (WinSCP, FileZilla)
# Подключиться к серверу и загрузить файл в /tmp/

# Вариант 3: USB-накопитель
# Скопировать файл на флешку, подключить к серверу
# Монтирование: sudo mount /dev/sdb1 /mnt/usb
# Копирование: cp /mnt/usb/stend_hardware.zip /tmp/
```

#### Установка на сервере

```bash
# Переход в директорию развертывания
cd /home/marat/proj

# Распаковка архива
unzip /tmp/stend_hardware.zip

# Переход в директорию проекта
cd stend_hardware

# Установка утилит (если нет unzip)
sudo apt-get install -y unzip
```

### Создание виртуального окружения
```bash
# Создание venv
python3 -m venv venv

# Активация
source venv/bin/activate

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt
```

### Настройка переменных окружения
```bash
# Если .env.example существует:
cp .env.example .env

# Если .env.example НЕ существует (чистая установка из ZIP):
nano .env
```

Содержимое `.env`:
```bash
DB_PASSWORD=Alexej@12
```

### Настройка прав доступа
```bash
# Права на папки данных
chmod -R 755 data/
chmod 600 .env
chmod 600 config.yaml
```

### Настройка конфигурации
Отредактируйте `config.yaml`:

```yaml
database:
  type: postgresql
  host: localhost
  port: 5432
  dbname: stend_hardware
  user: stend
  password: Alexej@12

owen:
  ip: 192.168.1.99
  port: 502
  unit: 1
  timeout: 1.0

camera:
  ip: 192.168.1.36
  port: 502
  unit: 1
  # ... остальные настройки камеры

paths:
  images: data/images
  logs: data/logs
```

## 4. Создание systemd сервиса

### Создание файла сервиса
```bash
sudo nano /etc/systemd/system/stend_hardware.service
```

Содержимое файла:
```ini
[Unit]
Description=Стенд машинного зрения
After=network.target postgresql.service

[Service]
Type=simple
User=marat
WorkingDirectory=/home/marat/proj/stend_hardware
ExecStart=/usr/bin/python3 run.py
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

### Включение и запуск сервиса
```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable stend_hardware

# Запуск сервиса
sudo systemctl start stend_hardware

# Проверка статуса
sudo systemctl status stend_hardware
```

## 5. Настройка файрвола

### Открытие портов
```bash
# Порт веб-интерфейса
sudo firewall-cmd --permanent --add-port=5001/tcp

# Modbus TCP (если нужен входящий трафик)
sudo firewall-cmd --permanent --add-port=502/tcp

# Перезагрузка файрвола
sudo firewall-cmd --reload
```

### Проверка правил
```bash
sudo firewall-cmd --list-all
```

## 6. Настройка сети для оборудования

### Проверка сетевых интерфейсов
```bash
# Просмотр интерфейсов
ip addr show

# Проверка подключения к оборудованию
ping 192.168.1.99  # ОВЕН
ping 192.168.1.36  # Камера
```

### Настройка статического IP (если необходимо)
```bash
sudo nano /etc/sysconfig/network-scripts/ifcfg-eth0
```

Пример конфигурации:
```ini
DEVICE=eth0
BOOTPROTO=static
IPADDR=192.168.1.100
NETMASK=255.255.255.0
GATEWAY=192.168.1.1
ONBOOT=yes
```

Перезапуск сети:
```bash
sudo systemctl restart network
```

## 7. Инициализация базы данных

### Запуск скрипта инициализации
```bash
# Активация venv
source venv/bin/activate

# Инициализация таблиц
python init_postgres.py

# Создание администратора
python create_admin.py
```

## 8. Первый запуск сервиса

### Запуск
```bash
# Перезагрузка systemd (после создания/изменения .service файла)
sudo systemctl daemon-reload

# Запуск сервиса
sudo systemctl start stend_hardware

# Включение автозапуска при загрузке системы
sudo systemctl enable stend_hardware
```

### Проверка после первого запуска
```bash
# Статус сервиса (должен быть active (running))
sudo systemctl status stend_hardware

# Проверка порта (должен слушать 5001)
ss -tlnp | grep 5001

# Проверка процесса
ps aux | grep run.py

# Проверка веб-интерфейса
curl -I http://localhost:5001
```

### Просмотр логов при старте
```bash
# Логи systemd (последние 50 строк + следить за новыми)
sudo journalctl -u stend_hardware -n 50 -f

# Логи приложения
tail -f /home/marat/proj/stend_hardware/data/logs/controller.log
tail -f /home/marat/proj/stend_hardware/data/logs/web.log
```

---

## 9. Перезапуск сервиса после корректировок

### Когда нужен перезапуск

| Тип изменений | Нужен перезапуск? | Команда |
|---------------|-------------------|---------|
| Изменение Python-кода (`.py` файлы) | Да | `restart` |
| Изменение `config.yaml` | Да | `restart` |
| Изменение `.env` | Да | `restart` |
| Обновление зависимостей (`requirements.txt`) | Да | `restart` |
| Изменение HTML/CSS/JS шаблонов | Да | `restart` |
| Логи, изображения (`data/`) | Нет | — |
| `update.sh` (git pull + pip install) | Да | в скрипте |

### Процедура перезапуска

#### Вариант А: Быстрый перезапуск (изменения в коде)
```bash
# 1. Остановить сервис
sudo systemctl stop stend_hardware

# 2. Внести изменения в код
nano /home/marat/proj/stend_hardware/имя_файла.py

# 3. Запустить сервис
sudo systemctl start stend_hardware

# 4. Проверить статус
sudo systemctl status stend_hardware
```

#### Вариант Б: Перезапуск одной командой
```bash
sudo systemctl restart stend_hardware
```

#### Вариант В: Обновление из Git + перезапуск
```bash
# 1. Перейти в директорию проекта
cd /home/marat/proj/stend_hardware

# 2. Активировать виртуальное окружение
source venv/bin/activate

# 3. Получить последние изменения
git pull origin main

# 4. Установить обновлённые зависимости (если requirements.txt изменился)
pip install -r requirements.txt

# 5. Перезапустить сервис
sudo systemctl restart stend_hardware

# 6. Проверить статус
sudo systemctl status stend_hardware
```

#### Вариант Г: Использование скрипта обновления (рекомендуется)
```bash
# Если скрипт update.sh уже создан (раздел 11):
/home/marat/proj/stend_hardware/update.sh

# Или одной строкой:
cd /home/marat/proj/stend_hardware && ./update.sh
```

### Что делать после перезапуска

```bash
# 1. Убедиться, что сервис запущен
sudo systemctl status stend_hardware

# 2. Проверить логи на наличие ошибок
sudo journalctl -u stend_hardware -n 20

# 3. Открыть веб-интерфейс и проверить работу
# http://<IP_СЕРВЕРА>:5001

# 4. Проверить подключение к оборудованию (если есть)
ping 192.168.1.99  # ОВЕН
ping 192.168.1.36  # Камера
```

### Автозапуск после перезагрузки сервера
```bash
# Проверить, что автозапуск включён
sudo systemctl is-enabled stend_hardware

# Если не включён:
sudo systemctl enable stend_hardware
```

---

## 10. Управление сервисом (справочник)

### Основные команды
```bash
# Запуск
sudo systemctl start stend_hardware

# Остановка
sudo systemctl stop stend_hardware

# Перезапуск (остановка + запуск)
sudo systemctl restart stend_hardware

# Перезагрузка конфигурации (без остановки, если поддерживается)
sudo systemctl reload stend_hardware

# Статус
sudo systemctl status stend_hardware

# Включение автозапуска
sudo systemctl enable stend_hardware

# Отключение автозапуска
sudo systemctl disable stend_hardware
```

### Просмотр логов
```bash
# Логи systemd (все)
sudo journalctl -u stend_hardware

# Логи systemd (последние 100 строк)
sudo journalctl -u stend_hardware -n 100

# Логи systemd (следить в реальном времени)
sudo journalctl -u stend_hardware -f

# Логи за конкретный период
sudo journalctl -u stend_hardware --since "2026-07-08 10:00:00"

# Логи приложения
tail -f /home/marat/proj/stend_hardware/data/logs/controller.log
tail -f /home/marat/proj/stend_hardware/data/logs/web.log
```

### Проверка работоспособности
```bash
# Проверка порта
ss -tlnp | grep 5001

# Проверка процесса
ps aux | grep run.py

# Проверка веб-интерфейса
curl -I http://localhost:5001

# Проверка с другого компьютера
curl -I http://192.168.1.100:5001
```

---

## 11. Решение проблем

### Типовые ошибки при запуске и перезапуске

| Симптом | Причина | Решение |
|---------|---------|---------|
| `Job for stend_hardware.service failed` | Ошибка в коде или конфигурации | `journalctl -u stend_hardware -n 50` — посмотреть ошибку |
| `Address already in use` | Старый процесс не завершился | `sudo fuser -k 5001/tcp` затем `sudo systemctl start stend_hardware` |
| `ModuleNotFoundError` | Venv не активирован в .service | Проверить `ExecStart` — должен быть полный путь к Python из venv |
| `Permission denied` к БД | Пароль в .env не совпадает | Проверить `.env` и `config.yaml` |
| Сервис запущен, но сайт не открывается | Файрвол блокирует порт | `sudo firewall-cmd --add-port=5001/tcp --permanent && sudo firewall-cmd --reload` |
| `Connection refused` к БД | PostgreSQL не запущен | `sudo systemctl start postgresql` |
| Сервис падает сразу после старта | Ошибка в Python-коде | `journalctl -u stend_hardware -n 100` — найти traceback |
| `git pull` конфликтует | Незакоммиченные изменения на сервере | `git stash` перед `git pull`, или `git reset --hard origin/main` |

### Правильный порядок действий при ошибке

```bash
# 1. Посмотреть последние логи
sudo journalctl -u stend_hardware -n 100

# 2. Остановить сервис (если "завис")
sudo systemctl stop stend_hardware

# 3. Проверить, нет ли "повисшего" процесса
ps aux | grep run.py
# Если есть — убить:
sudo kill $(pgrep -f "run.py")

# 4. Исправить проблему

# 5. Запустить заново
sudo systemctl start stend_hardware

# 6. Проверить статус
sudo systemctl status stend_hardware
```

### Проверка зависимостей
```bash
# Активация venv
source /home/marat/proj/stend_hardware/venv/bin/activate

# Проверка установленных пакетов
pip list

# Проверка версии Python
python --version

# Проверка подключения к БД
psql -h localhost -U stend -d stend_hardware
```

### Дублирующий пользовательский сервис (stend.service)

**Проблема:** Приложение продолжает работать и общаться с оборудованием (OWEN моргает, камера отвечает), хотя системный сервис `stend_hardware.service` остановлен и отключен.

**Причина:** Существует **два разных systemd сервиса**, запускающих одно и то же приложение:

| Сервис | Уровень | Файл | Управление |
|--------|---------|------|------------|
| `stend_hardware.service` | системный | `/etc/systemd/system/stend_hardware.service` | `sudo systemctl ...` |
| `stend.service` | **пользовательский** | `~/.config/systemd/user/stend.service` | `systemctl --user ...` |

Пользовательский сервис `stend.service` имеет `Restart=on-failure` с `RestartSec=5` — приложение падает и перезапускается каждые 5 секунд, из-за чего лампа на OWEN постоянно моргает.

**Диагностика:**
```bash
# Проверка системного сервиса (показывает "inactive" — создаёт ложное впечатление, что всё остановлено)
sudo systemctl status stend_hardware.service

# Проверка пользовательских сервисов (вот он — активный!)
systemctl --user list-units --type=service | grep stend

# Детальный статус
systemctl --user status stend.service
```

**Решение:**
```bash
# Остановка пользовательского сервиса
systemctl --user stop stend.service

# Отключение автозапуска
systemctl --user disable stend.service

# Удаление файла сервиса (если больше не нужен)
rm ~/.config/systemd/user/stend.service
systemctl --user daemon-reload
```

**Предотвращение:** При развертывании использовать **только один** из двух вариантов:
- Системный сервис (`stend_hardware.service`) — управление через `sudo systemctl`
- Пользовательский сервис (`stend.service`) — управление через `systemctl --user`

Не использовать оба одновременно. Если ранее был создан пользовательский сервис, удалить его перед настройкой системного.

---

## 12. Обновление проекта из GitHub

### Ручное обновление
```bash
# 1. Перейти в директорию проекта
cd /home/marat/proj/stend_hardware

# 2. Остановить сервис
sudo systemctl stop stend_hardware

# 3. Получить изменения
git pull origin main

# 4. Установить обновлённые зависимости
source venv/bin/activate
pip install -r requirements.txt

# 5. Выполнить миграции БД (если есть)
# python init_postgres.py  # раскомментировать при необходимости

# 6. Запустить сервис
sudo systemctl start stend_hardware

# 7. Проверить статус
sudo systemctl status stend_hardware
```

### Автоматическое обновление (скрипт)
```bash
# Запуск скрипта обновления (если создан раздел 13)
/home/marat/proj/stend_hardware/update.sh
```

### Что делать при конфликтах git
```bash
# Если есть локальные изменения, которые не нужны:
git reset --hard origin/main

# Если локальные изменения нужно сохранить:
git stash
git pull origin main
git stash pop
```

---

## 13. Резервное копирование

### Бэкап базы данных
```bash
# Создание бэкапа
pg_dump -h localhost -U stend -d stend_hardware > backup_$(date +%Y%m%d).sql

# Восстановление
psql -h localhost -U stend -d stend_hardware < backup_20260629.sql
```

### Бэкап конфигурации
```bash
# Копирование конфига
cp config.yaml config.yaml.backup.$(date +%Y%m%d)

# Копирование .env
cp .env .env.backup.$(date +%Y%m%d)
```

## 14. Автоматическое обновление (опционально)

### Создание скрипта обновления
```bash
sudo nano /home/marat/proj/stend_hardware/update.sh
```

Содержимое:
```bash
#!/bin/bash
cd /home/marat/proj/stend_hardware
source venv/bin/activate
git pull
pip install -r requirements.txt
sudo systemctl restart stend_hardware
```

### Права на выполнение
```bash
chmod +x /home/marat/proj/stend_hardware/update.sh
```

## 15. Проверка после установки

1. **Веб-интерфейс**: Откройте http://192.168.1.100:5001
2. **Авторизация**: Войдите с созданным администратором
3. **Мониторинг**: Проверьте статус оборудования
4. **Логи**: Убедитесь, что нет ошибок

---

## Быстрая инструкция (ZIP-установка)

Для быстрого развертывания из ZIP-архива выполните последовательно:

```bash
# 1. Установка зависимостей
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv python3-dev gcc make libpq-dev postgresql postgresql-client unzip

# 2. Настройка PostgreSQL
sudo postgresql-setup --initdb
sudo systemctl enable postgresql
sudo systemctl start postgresql
sudo -u postgres psql -c "CREATE USER stend WITH PASSWORD 'Alexej@12';"
sudo -u postgres psql -c "CREATE DATABASE stend_hardware OWNER stend;"

# 3. Установка приложения
cd /home/marat/proj
unzip /tmp/stend_hardware.zip
cd stend_hardware
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Создание .env файла
nano .env  # ввести параметры БД

# 5. Настройка pg_hba.conf (md5 аутентификация)
sudo nano /var/lib/pgsql/data/pg_hba.conf
sudo systemctl restart postgresql

# 6. Инициализация БД
python init_postgres.py
python create_admin.py

# 7. Создание systemd сервиса
sudo nano /etc/systemd/system/stend_hardware.service  # вставить содержимое из документации
sudo systemctl daemon-reload
sudo systemctl enable stend_hardware
sudo systemctl start stend_hardware

# 8. Проверка
sudo systemctl status stend_hardware
curl http://localhost:5001
```

---

**Примечание:** Замените `192.168.1.100` на реальный IP-адрес вашего сервера ALT Linux.
