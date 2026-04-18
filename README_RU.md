# Media Machine - Autonomous Telegram Content System

🤖 **Полная multi-agent система для автоматического создания вирусного контента в Telegram**

## Возможности

### 8 Автономных Агентов:

1. **Trend Detector** — Раннее обнаружение трендов
   - Мониторит Reddit, Twitter/X, Google Trends, RSS (BBC, Reuters)
   - Кластеризует сигналы через embeddings
   - Считает `trend_score = (Reddit × 2) + (X velocity) + (Google growth) + novelty`
   - Отдаёт только темы со score > 7

2. **Writer** — Генерация контента
   - Создаёт 3 варианта поста по каждой теме
   - Стили: Direct/Factual, Story-driven, Question-based
   - Учитывает успешные посты из памяти

3. **Hype Optimizer** — Усиление виральности
   - Улучшает заголовки и первые абзацы
   - Добавляет вопросы, цифры, триггеры
   - Без добавления ложной информации

4. **Critic** — Строгий фактчекер
   - Проверяет каждый вариант по источникам
   - Оценивает по 3 метрикам (1-10): Truth / Clarity / Hype
   - Ищет выдумки, искажения, кликбейт

5. **Judge** — Финальный редактор
   - Выбирает лучший вариант ИЛИ отклоняет
   - Публикация только если: Truth≥8, Clarity≥7, Hype≥6

6. **Analyst** — Анализ конкурентов
   - Каждые 6 часов парсит топ-посты конкурентов
   - Считает views/hour, ER, длину, структуру
   - Выдаёт insights о работающих паттернах

7. **Strategist** — Стратег
   - Генерирует 5 новых идей на основе трендов + аналитики
   - Предлагает лучшее время публикации

8. **Publisher + Monetizer** — Публикация и монетизация
   - Добавляет нативные партнёрские ссылки
   - Соблюдает правило 5 полезных : 1 рекламный
   - Ведёт базу posted ссылок

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                           │
│  (Main Loop: every 20-30 minutes)                           │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌─────────────────┐    ┌──────────────┐
│   Trend       │    │    Analyst      │    │  Self-Improvement │
│   Detector    │    │   (6 hours)     │    │   (daily)   │
└───────┬───────┘    └─────────────────┘    └──────────────┘
        │
        ▼ (if trend_score > 7)
┌───────────────┐
│  Strategist   │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│    Writer     │ → 3 variants
└───────┬───────┘
        │
        ▼
┌───────────────┐
│   Hype        │
│  Optimizer    │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│    Critic     │ → Truth/Clarity/Hype scores
└───────┬───────┘
        │
        ▼
┌───────────────┐
│    Judge      │ → APPROVE or REJECT
└───────┬───────┘
        │
        ▼ (if approved)
┌───────────────┐
│   Publisher   │ → Telegram + monetization
└───────────────┘
```

## Установка

### 1. Клонирование и окружение

```bash
cd /workspace
python3.11 -m venv venv
source venv/bin/activate
```

### 2. Установка зависимостей

```bash
pip install python-dotenv openai groq anthropic feedparser praw telethon python-telegram-bot apscheduler pandas sentence-transformers
```

Или используйте requirements.txt:

```bash
pip install -r requirements.txt
```

### 3. Настройка конфигурации

```bash
cp config/.env.example config/.env
```

Отредактируйте `config/.env` и добавьте ваши API ключи:

```env
# LLM Configuration
LLM_PROVIDER=openai  # или groq, anthropic
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini

# Telegram Configuration
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHANNEL_ID=@your_channel
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890

# Trend Sources (опционально)
REDDIT_CLIENT_ID=your_reddit_id
REDDIT_CLIENT_SECRET=your_reddit_secret

# RSS Feeds
RSS_FEEDS=https://feeds.bbci.co.uk/news/rss.xml,https://feeds.reuters.com/reuters/topNews

# Competitor Channels
COMPETITOR_CHANNELS=@competitor1,@competitor2

# Database
DATABASE_PATH=./data/media_machine.db

# Scheduling
TREND_CHECK_INTERVAL=20
ANALYST_INTERVAL=360

# Monetization
PARTNER_LINKS_AI=https://partner.example.com/ai
PARTNER_LINKS_CRYPTO=https://partner.example.com/crypto
PARTNER_LINKS_TOOLS=https://partner.example.com/tools
MONETIZATION_RATIO=5
```

## Использование

### Инициализация базы данных

```bash
python main.py init
```

### Тестовый запуск (один цикл)

```bash
python main.py test
```

### Проверка статуса

```bash
python main.py status
```

### Подробная статистика

```bash
python main.py stats
```

### Постоянная работа (24/7)

```bash
python main.py run
```

### В фоне (production)

```bash
nohup python main.py run > logs/orchestrator.log 2>&1 &
```

Или используйте systemd/tmux/screen.

## Структура проекта

```
/workspace/
├── main.py                 # Точка входа, CLI
├── orchestrator.py         # Центральный координатор
├── config/
│   ├── __init__.py
│   ├── settings.py         # Конфигурация из .env
│   └── .env.example        # Шаблон конфига
├── agents/
│   ├── __init__.py
│   ├── trend_detector.py   # Агент 1: Поиск трендов
│   ├── writer.py           # Агент 2: Генерация контента
│   ├── hype_optimizer.py   # Агент 3: Усиление
│   ├── critic.py           # Агент 4: Фактчек
│   ├── judge.py            # Агент 5: Редактор
│   ├── analyst.py          # Агент 6: Аналитик
│   ├── strategist.py       # Агент 7: Стратег
│   └── publisher.py        # Агент 8: Публикация + Монетизация
├── utils/
│   ├── __init__.py
│   ├── database.py         # SQLite память системы
│   ├── llm_client.py       # LLM абстракция (OpenAI/Groq/Anthropic)
│   └── logger.py           # Логирование
├── data/
│   └── media_machine.db    # База данных (создаётся автоматически)
├── logs/
│   └── media_machine.log   # Логи
└── requirements.txt        # Зависимости
```

## Память системы (SQLite)

### Таблицы:

- **posted** — Опубликованные ссылки (для избежания дублей)
- **performance** — Метрики постов (views_1h, views_3h, ER, likes, comments)
- **post_history** — История генерации (все варианты, оценки, решения)
- **trend_signals** — Детектированные тренды
- **competitor_posts** — Посты конкурентов для анализа
- **analyst_insights** — Инсайты от Analyst

### Self-Improvement Loop:

Каждые 24 часа Judge анализирует:
- Последние 20 успешных постов
- Последние 20 проваленных/отклонённых
- Генерирует рекомендации для Writer

## A/B Тестирование

Для каждого поста Hype Optimizer создаёт 2 варианта заголовка. 
Publisher может публиковать разные варианты в разное время для теста.

## Монетизация

Система соблюдает правило **5 полезных постов : 1 рекламный**.

Партнёрские ссылки ротируются по категориям:
- AI/ML инструменты
- Crypto проекты
- Software/Tools

## Логирование

Все действия логируются в `logs/media_machine.log`:

```
2024-01-15 10:30:00 | orchestrator | INFO     | 🚀 Initializing Media Machine Orchestrator...
2024-01-15 10:30:01 | orchestrator | INFO     | 📊 Database initialized: ./data/media_machine.db
2024-01-15 10:30:02 | orchestrator | INFO     | ✅ All agents initialized
2024-01-15 10:30:02 | orchestrator | INFO     | 🔍 Running Trend Detector...
2024-01-15 10:30:05 | orchestrator | INFO     | ✨ Found 3 strong trends
2024-01-15 10:30:05 | orchestrator | INFO     | 📝 Processing trend: AI breakthrough announced...
2024-01-15 10:30:15 | orchestrator | INFO     | ✅ APPROVED: Major AI Breakthrough Changes Everything
2024-01-15 10:30:16 | orchestrator | INFO     | 📊 Published to Telegram: post_id=12345
```

## Расширение системы

### Добавление нового источника трендов:

```python
# agents/trend_detector.py
def _collect_custom_signals(self) -> List[Dict]:
    signals = []
    # Your custom source logic
    return signals
```

### Добавление нового агента:

1. Создать класс в `agents/new_agent.py`
2. Добавить `run()` метод
3. Импортировать в `orchestrator.py`
4. Вызвать в нужном месте pipeline

### Кастомизация стиля:

Изменить системный промпт в `agents/writer.py`:

```python
self.system_prompt = """
Your custom style guidelines here...
"""
```

## Troubleshooting

### "No trends found"
- Проверьте RSS feeds и Reddit API credentials
- Уменьшите порог trend_score в настройках

### "LLM API error"
- Проверьте API ключи в `.env`
- Убедитесь, что выбран правильный provider

### "Telegram publish failed"
- Проверьте токен бота и channel ID
- Убедитесь, что бот добавлен администратором канала

## Лицензия

MIT License — используйте на здоровье!

---

**Created by Senior AI Architect** 🚀
