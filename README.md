# 🌡️ Worklimate Bot — Rischio Caldo

Bot che monitora automaticamente [Worklimate](https://app.worklimate.it/ordinanza-caldo-lavoro)  
e invia una notifica Telegram quando viene rilevato **livello di rischio ALTO (Emergenza)**  
per il comune di **Surano (LE)**.

---

## Come funziona

Ogni giorno alle **06:00** e alle **12:00** (ora italiana), GitHub Actions:

1. Apre la pagina Worklimate con Playwright (browser headless)
2. Cerca il comune "Surano, Lecce" e legge i livelli di rischio per i prossimi 3 giorni
3. Se trova "rischio ALTO" o "Emergenza" → invia messaggio Telegram
4. Salva un **screenshot** come artefatto per debug (conservato 3 giorni)

---

## Setup (una tantum)

### 1. Crea il bot Telegram
1. Scrivi a [@BotFather](https://t.me/BotFather) su Telegram → `/newbot`
2. Salva il **token** (es. `123456:ABCdef...`)
3. Scrivi qualcosa al tuo bot, poi visita:  
   `https://api.telegram.org/bot<TOKEN>/getUpdates`  
   e prendi il valore `chat.id` dal JSON

### 2. Aggiungi i Secrets su GitHub

Vai su **Settings → Secrets and variables → Actions → New repository secret**:

| Secret name        | Valore                        |
|--------------------|-------------------------------|
| `TELEGRAM_TOKEN`   | Il token del tuo bot Telegram |
| `TELEGRAM_CHAT_ID` | Il tuo chat ID numerico       |

### 3. Attiva GitHub Actions
Il workflow gira automaticamente. Puoi avviarlo manualmente da  
**Actions → Worklimate Rischio Caldo Bot → Run workflow**

---

## File del progetto

```
worklimate_bot/
├── check_rischio_caldo.py        # Script principale
└── .github/
    └── workflows/
        └── worklimate_bot.yml    # Workflow GitHub Actions
```

---

## Esempio notifica Telegram

```
🚨 RISCHIO CALDO ALTO — Surano, Lecce

Worklimate ha previsto livello di rischio ALTO (Emergenza)
per uno o più giorni:
  🔴 Lunedì, 23 giugno 2026

Riepilogo previsioni:
🟠 Sabato, 21 giugno 2026: Rischio Medio
🔴 Domenica, 22 giugno 2026: Rischio Alto
🔴 Lunedì, 23 giugno 2026: Rischio Alto (Emergenza)

⚠️ Modifica gli orari lavorativi, privilegia le ore più fresche,
aumenta le pause e l'idratazione.

🔗 Apri Worklimate
🕐 Rilevato: 23/06/2026 06:02
```

---

## Note

- Il sito Worklimate aggiorna le previsioni **una volta al giorno** (mattina presto)
- Le previsioni sono **sperimentali e automatiche** — usarle come supporto, non come unica fonte
- In caso di problemi tecnici, lo screenshot di debug è disponibile in **Actions → Artifacts**
