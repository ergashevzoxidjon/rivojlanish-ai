# Rivojlanish AI

Sun'iy intellekt vositalaridagi (Claude, ChatGPT, Gemini, Claude Code, Cursor, Codex, n8n, MCP) yangi funksiyalarni
har kuni kuzatib, ularni **o'zbek tilida qadam-baqadam dars + amaliy topshiriq + test** ko'rinishida yetkazadigan platforma.

Uch qismdan iborat, hammasi bitta backend va bitta bazada ishlaydi:

| Qism | Vazifasi |
| --- | --- |
| Telegram bot | Har kuni soat 8:00 da 1–3 ta dars, "📚 Yana dars yuborish" tugmasi, test, takrorlash savollari, AI ustoz |
| Telegram Web App | Bot ichida to'liq platforma (Telegram orqali avtomatik kirish) |
| Web ilova | Brauzerda: darslar arxivi, qidiruv, progress, AI ustoz, admin panel |

## Imkoniyatlar

- **Avtomatik kontent.** Rasmiy manbalar (RSS/Atom, GitHub releases, sahifa o'zgarishlari) har 3 soatda tekshiriladi.
  Claude har bir yangilikni baholaydi: haqiqiy yangi funksiyami, takror emasmi, qanchalik muhim (1–10).
  Foydalilari darsga aylanadi.
- **Aqlli tanlov.** Ertalabki darslar muhimlik, yangilik va foydalanuvchi darajasiga qarab saralanadi, mavzular aralashtiriladi.
- **"Yana dars yuborish".** Vaqti ko'p foydalanuvchi xohlagancha dars oladi. Tayyor darslar tugasa, AI uning
  darajasiga mos yangi dars yozadi (kunlik limit bilan).
- **Test va moslashuvchan daraja.** Har darsda 3 ta savol. So'nggi testlar natijasiga qarab daraja
  (Boshlang'ich → O'rta → Ilg'or) avtomatik o'zgaradi.
- **Takrorlash (spaced repetition).** Bajarilgan dars 3 va 7 kundan keyin qisqa savol bilan qaytadi.
- **AI ustoz.** Dars ichida yoki umumiy savollarga o'zbek tilida javob beradi (botda shunchaki yozish kifoya).
- **Gamifikatsiya.** XP, unvonlar, ketma-ket kunlar, yutuqlar, reyting.
- **Admin panel.** Statistika, qoralamalarni tahrirlash/nashr qilish, AI bilan dars yozdirish, test muharriri,
  manbalar, yangiliklar oqimi, ishlar jurnali, hammaga xabar yuborish, foydalanuvchilar.
- **Ro'yxatdan o'tish** — Google (email) orqali. Telegram akkaunt avtomatik bog'lanadi.

## Texnologiyalar

- Backend: Python 3.10+, FastAPI, SQLAlchemy 2 (MySQL yoki SQLite), Claude API
- Bot: Telegram Bot API (webhook)
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS + TanStack Query
- Hosting: cPanel "Setup Python App" (Passenger) — `backend/passenger_wsgi.py`

```
backend/
  app/
    main.py          FastAPI ilova, webhook, frontendni berish
    models.py        Baza jadvallari
    lessons.py       O'quv dvigateli: tanlov, XP, test, daraja, takrorlash, yutuqlar
    collector.py     Manbalardan yig'ish + AI orqali darsga aylantirish
    ai_writer.py     Claude bilan ishlash (dars, test, ustoz)
    tutor.py         AI ustoz
    bot/             Telegram bot (handlers, xabarlar, yuborish)
    api/             REST API (users, learning, admin)
    static/          React build (frontend `npm run build` shu yerga yozadi)
  scripts/           init_db, cron_collect, cron_daily, setup_bot, make_admin
  tests/             avtomatik testlar (pytest)
  passenger_wsgi.py  cPanel uchun kirish nuqtasi
frontend/            React ilova manba kodi
```

---

## O'rnatish (Hostmaster.uz, cPanel)

### 1. Kerakli kalitlar

1. **Telegram bot tokeni** — @BotFather'dan (bor).
2. **Claude API kaliti** — https://console.anthropic.com → API Keys.
3. **Google Client ID**:
   - https://console.cloud.google.com → yangi loyiha → *APIs & Services* → *OAuth consent screen* (External, ilova nomi: Rivojlanish AI).
   - *Credentials* → *Create credentials* → *OAuth client ID* → *Web application*.
   - *Authorized JavaScript origins*: `https://SIZNING-DOMEN.uz`
   - Hosil bo'lgan `...apps.googleusercontent.com` qiymati — `GOOGLE_CLIENT_ID`.
4. **Domen + SSL** — cPanel → *SSL/TLS Status* → AutoSSL (Telegram Web App faqat HTTPS bilan ishlaydi).

### 2. MySQL baza

cPanel → *MySQL Databases*: baza va foydalanuvchi yarating, foydalanuvchiga **ALL PRIVILEGES** bering.
`DATABASE_URL` shunday bo'ladi:

```
mysql+pymysql://cpuser_rivoj:PAROL@localhost/cpuser_rivojlanish?charset=utf8mb4
```

### 3. Kodni yuklash

cPanel → *Git Version Control* → *Create* → Clone URL: `https://github.com/ergashevzoxidjon/rivojlanish-ai.git`,
Repository Path: `rivojlanish-ai`.

### 4. Python ilova

cPanel → *Setup Python App* → *Create Application*:

| Maydon | Qiymat |
| --- | --- |
| Python version | 3.11 (yoki 3.10+) |
| Application root | `rivojlanish-ai/backend` |
| Application URL | domeningiz |
| Application startup file | `passenger_wsgi.py` |
| Application Entry point | `application` |

Yaratilgandan keyin *Configuration files* → `requirements.txt` → **Run Pip Install**.

### 5. `.env` fayli

cPanel → *File Manager* → `rivojlanish-ai/backend/.env.example` faylini `.env` nomi bilan nusxalang va to'ldiring
(`WEB_URL`, `DATABASE_URL`, `SECRET_KEY`, `TELEGRAM_*`, `GOOGLE_CLIENT_ID`, `ANTHROPIC_API_KEY`, `ADMIN_EMAILS`).

`SECRET_KEY` uchun uzun tasodifiy satr: `python -c "import secrets;print(secrets.token_hex(32))"`

### 6. Bazani va botni sozlash

*Setup Python App* sahifasining yuqorisidagi `source .../activate && cd ...` buyrug'ini nusxalab, cPanel → *Terminal* da bajaring, so'ng:

```bash
python scripts/init_db.py     # jadvallar + standart manbalar
python scripts/setup_bot.py   # webhook, buyruqlar, menyu tugmasi (Web App)
```

Keyin *Setup Python App* → **Restart**.

### 7. Cron vazifalari

cPanel → *Cron Jobs* (`VENV` — Setup Python App sahifasida ko'rsatilgan virtualenv yo'li):

```
# Har 3 soatda: yangiliklarni yig'ish va darsga aylantirish
0 */3 * * *  cd ~/rivojlanish-ai/backend && ~/virtualenv/rivojlanish-ai/backend/3.11/bin/python scripts/cron_collect.py >/dev/null 2>&1

# Har soat: ertalabki darslar (skript Toshkent vaqti bilan 8:00 dan keyin kuniga bir marta yuboradi)
5 * * * *    cd ~/rivojlanish-ai/backend && ~/virtualenv/rivojlanish-ai/backend/3.11/bin/python scripts/cron_daily.py >/dev/null 2>&1
```

### 8. Admin bo'lish

`.env` dagi `ADMIN_EMAILS` ga yozilgan email bilan saytga Google orqali kiring — avtomatik admin bo'lasiz.
Admin panel: sayt → **Admin**. Birinchi marta *Umumiy → Yangiliklarni hozir yig'ish* tugmasini bosing.

### Yangilash

GitHub'ga yangi kod push qilingach: cPanel → *Git Version Control* → *Manage* → **Update from Remote**,
so'ng *Setup Python App* → **Restart** (yoki `touch ~/rivojlanish-ai/backend/tmp/restart.txt`).
`requirements.txt` o'zgargan bo'lsa — yana *Run Pip Install*.

---

## Lokal ishlab chiqish

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt pytest
cp .env.example .env                                     # DATABASE_URL=sqlite:///./rivojlanish.db
python scripts/init_db.py
uvicorn app.main:app --reload --port 8000
pytest                                                   # testlar

# Frontend (alohida terminalda)
cd frontend
npm install
npm run dev          # http://localhost:5173 (API so'rovlari 8000 ga yo'naltiriladi)
npm run build        # natija backend/app/static ga yoziladi — shu holatda GitHub'ga yuklang
```

> Hostingda Node.js shart emas: build qilingan frontend (`backend/app/static`) repozitoriyada saqlanadi.
> Frontendni o'zgartirgandan keyin `npm run build` qilib, natijani ham commit qiling.

## Muhim sozlamalar (`.env`)

| Kalit | Ma'nosi | Standart |
| --- | --- | --- |
| `DAILY_HOUR` | Ertalabki yuborish soati (Toshkent) | 8 |
| `DAILY_MIN_LESSONS` / `DAILY_MAX_LESSONS` | Kunlik darslar oralig'i | 1 / 3 |
| `MORE_LESSONS_BATCH` | "Yana dars" bosilganda nechta | 3 |
| `ON_DEMAND_DAILY_LIMIT` | Kuniga AI yozadigan qo'shimcha darslar (har foydalanuvchiga) | 10 |
| `TUTOR_DAILY_LIMIT` | AI ustozga kunlik savollar | 30 |
| `AUTO_PUBLISH` | `false` bo'lsa yangiliklardan yozilgan darslar admin tasdiqlashini kutadi | true |
| `COLLECT_MAX_ITEMS` | Bir yig'ishda AI ko'radigan yangiliklar soni (xarajatni cheklaydi) | 6 |
| `CLAUDE_MODEL` | Claude modeli | claude-sonnet-5-5 |

## Xavfsizlik

- `.env` hech qachon GitHub'ga yuklanmaydi (`.gitignore`).
- Telegram webhook maxfiy so'z bilan himoyalangan; Web App `initData` imzosi tekshiriladi.
- Google ID token server tomonda tekshiriladi; sessiya — JWT.
- Test javoblari foydalanuvchi testni topshirmaguncha brauzerga yuborilmaydi.
