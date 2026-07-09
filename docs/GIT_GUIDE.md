# Руководство по Git для проекта stend_hardware

## Содержание

1. [Настройка репозитория](#1-настройка-репозитория)
2. [Удалённые репозитории](#2-удалённые-репозитории)
3. [Ветки](#3-ветки)
4. [Основные операции](#4-основные-операции)
5. [Работа с удалёнными репозиториями](#5-работа-с-удалёнными-репозиториями)
6. [Решение конфликтов](#6-решение-конфликтов)
7. [Полезные команды](#7-полезные-команды)
8. [Правила работы](#8-правила-работы)

---

## 1. Настройка репозитория

### Текущая конфигурация

```bash
# Проверить имя и email
git config user.name    # MaratSharf
git config user.email   # 69249765+MaratSharf@users.noreply.github.com

# Изменить (если нужно)
git config --global user.name "MaratSharf"
git config --global user.email "69249765+MaratSharf@users.noreply.github.com"
```

### Учётные данные GitHub

Учётные данные хранятся в `~/.git-credentials` (credential helper = store).

**Проверить текущий токен:**
```bash
git credential fill <<EOF
protocol=https
host=github.com
EOF
```

**Обновить токен (если протух):**
```bash
# Удалить старый
git credential reject <<EOF
protocol=https
host=github.com
EOF

# Добавить новый
git credential approve <<EOF
protocol=https
host=github.com
username=MaratSharf
password=ghp_ВАШ_НОВЫЙ_ТОКЕН
EOF
```

---

## 2. Удалённые репозитории

### Текущие remote

| Название | URL | Назначение |
|----------|-----|------------|
| `origin` | `https://github.com/MaratSharf/stend_hardware.git` | GitHub (основной) |
| `github` | `https://github.com/MaratSharf/stend_hardware.git` | GitHub (дубль) |
| `gitverse` | `https://gitverse.ru/vdtnch/stend_hardware.git` | GitVerse (бэкап) |
| `gitverse-ssh` | `git@github.com:MaratSharf/stend_hardware.git` | GitHub через SSH |

### Просмотр remote

```bash
git remote -v              # Список всех remote
git remote show origin     # Подробности о remote
```

### Добавление нового remote

```bash
git remote add <имя> <URL>
```

### Удаление remote

```bash
git remote remove <имя>
```

---

## 3. Ветки

### Текущие ветки

| Ветка | Назначение |
|-------|------------|
| `main` | Основная ветка (текущая) |
| `master` | Старая основная ветка |
| `mas` | Рабочая ветка |

### Локальные ветки

```bash
git branch                  # Список веток
git branch -a               # Все ветки (включая удалённые)
git branch -v               # С последним коммитом
```

### Создание ветки

```bash
git checkout -b <имя-ветки>           # Создать и переключиться
git switch -c <имя-ветки>            # Аналог (современный способ)
```

### Переключение между ветками

```bash
git switch <имя-ветки>              # Переключиться
git checkout <имя-ветки>            # Аналог
```

### Удаление ветки

```bash
git branch -d <имя-ветки>           # Удалить (безопасно)
git branch -D <имя-ветки>           # Удалить принудительно
git push origin --delete <имя-ветки> # Удалить удалённую
```

---

## 4. Основные операции

### Просмотр состояния

```bash
git status                  # Текущее состояние
git diff                    # Изменения (не staged)
git diff --staged           # Изменения (staged)
git diff main..feature      # Разница между ветками
```

### Добавление изменений

```bash
git add <файл>              # Добавить файл
git add .                   # Добавить всё
git add *.py                # По маске
git add -p                  # Интерактивно (по частям)
```

### Коммит

```bash
git commit -m "описание"            # Коммит с описанием
git commit -am "описание"           # Добавить все изменённые + коммит
git commit --amend                  # Исправить последний коммит
```

### Просмотр истории

```bash
git log                      # Полная история
git log --oneline            # Сжатая история
git log --oneline -10        # Последние 10 коммитов
git log --graph              # С графом веток
git log --author="Marat"     # Фильтр по автору
```

---

## 5. Работа с удалёнными репозиториями

### Получение изменений

```bash
git fetch origin             # Скачать (без слияния)
git pull origin main         # Скачать + слить
git pull --rebase origin main # Скачать + rebase
```

### Отправка изменений

```bash
git push origin main         # Отправить ветку
git push -u origin main      # Отправить + установить отслеживание
git push origin --all        # Отправить все ветки
```

### Синхронизация с GitHub

```bash
# 1. Получить изменения
git fetch origin

# 2. Посмотреть что изменилось
git log --oneline HEAD..origin/main

# 3. Слить
git merge origin/main
# или
git rebase origin/main
```

### Синхронизация с GitVerse (бэкап)

```bash
# Отправить в GitVerse
git push gitverse main

# Получить из GitVerse
git pull gitverse main
```

---

## 6. Решение конфликтов

### Когда возникают конфликты

- При `git pull` если удалённые изменения конфликтуют с локальными
- При `git merge` двух веток
- При `git rebase` на удалённую ветку

### Алгоритм решения

```bash
# 1. Получить изменения
git pull origin main

# 2. Если конфликт — открыть файлы с конфликтами
git status                  # Покажет конфликтные файлы

# 3. В файлах найти маркеры конфликта:
<<<<<<< HEAD
ваш код
=======
код из удалённого репозитория
>>>>>>> origin/main

# 4. Вручную выбрать нужный вариант, удалить маркеры

# 5. Добавить исправленные файлы
git add <файл>

# 6. Завершить merge
git commit -m "resolve conflict"
```

### Отмена merge/rebase

```bash
git merge --abort            # Отменить merge
git rebase --abort           # Отменить rebase
```

### Сброс локальных изменений

```bash
# Отменить staged изменения
git reset HEAD <файл>

# Сбросить ВСЕ локальные изменения (ОПАСНО!)
git reset --hard origin/main

# Сохранить изменения во временном хранилище
git stash
git stash pop                # Вернуть
git stash list               # Список хранилищ
```

---

## 7. Полезные команды

### Поиск

```bash
git log --all --grep="текст"       # Поиск по описанию коммита
git log --oneline -- "*.py"        # История изменения файла
git log -p -- <файл>               # Все изменения файла
git blame <файл>                   # Кто и когда менял строки
```

### Отмена изменений

```bash
git restore <файл>                 # Отменить изменения в файле
git restore --staged <файл>        # Убрать из staged
git revert <коммит>                # Отменить коммит (новым коммитом)
git reset HEAD~1                   # Сбросить последний коммит (сохранить изменения)
git reset --hard HEAD~1            # Сбросить последний коммит (УДАЛИТЬ изменения)
```

### Теги

```bash
git tag <имя>                      # Создать тег на текущем коммите
git tag -a <имя> -m "описание"    # Тег с описанием
git push origin <имя>              # Отправить тег
git push origin --tags             # Отправить все теги
git tag -d <имя>                   # Удалить локальный тег
git push origin --delete <имя>     # Удалить удалённый тег
```

### Шпаргалка

```bash
# Что я делаю?
git status

# Что изменилось?
git diff

# Что коммитить?
git diff --staged

# Кто что менял?
git log --oneline -10

# Как отменить?
git restore <файл>
```

---

## 8. Правила работы

### Перед началом работы

```bash
# 1. Убедиться, что вы в правильной ветке
git branch

# 2. Получить последние изменения
git pull origin main

# 3. Активировать виртуальное окружение
source venv/bin/activate
```

### Во время работы

1. **Делать коммиты часто** — маленькие, с понятными описаниями
2. **Не коммитить секреты** — `.env`, пароли, токены
3. **Не коммитить сгенерированные файлы** — `__pycache__/`, `venv/`, `*.pyc`

### Перед отправкой

```bash
# 1. Посмотреть что будет отправлено
git status
git diff --staged

# 2. Отправить
git push origin main
```

### Частые ошибки и решения

| Проблема | Решение |
|----------|---------|
| Закоммитил не тот файл | `git reset --soft HEAD~1` и коммит заново |
| Забыл добавить файл | `git add <файл>` и `git commit --amend` |
| Конфликт при pull | `git stash` → `git pull` → `git stash pop` |
| Протухший токен | Обновить через `git credential approve` |
| Ветка уехала от main | `git rebase origin/main` |

### Структура коммитов

```
# Формат:
<тип>: <описание>

# Примеры:
feat: добавлена кнопка экспорта в PDF
fix: исправлена ошибка подключения к ОВЕН
docs: обновлена инструкция по部署
refactor: рефакторинг модуля распознавания
chore: обновлены зависимости
```

---

## Быстрая шпаргалка

```bash
# Статус
git status

# Получить изменения
git pull origin main

# Добавить и коммитить
git add .
git commit -m "описание"

# Отправить
git push origin main

# Посмотреть историю
git log --oneline -10

# Отменить изменения
git restore <файл>

# Переключить ветку
git switch <имя-ветки>
```

---

**Примечание:** Этот репозиторий синхронизируется с GitHub (`origin`) и GitVerse (`gitverse`). Основная работа ведётся через GitHub.
