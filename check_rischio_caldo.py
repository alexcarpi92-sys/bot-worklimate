"""
Bot Worklimate - Rischio Caldo
Monitora https://app.worklimate.it/ordinanza-caldo-lavoro per Surano (LE)
e invia notifica Telegram se viene rilevato livello di rischio ALTO.
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

# ── Configurazione ──────────────────────────────────────────────────────────
COMUNE          = "Surano, Lecce"          # Come da indicazioni del sito
TELEGRAM_TOKEN  = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
URL             = "https://app.worklimate.it/ordinanza-caldo-lavoro"

# Parole chiave che identificano il livello ALTO nei testi della pagina
KEYWORDS_ALTO = [
    "rischio alto",
    "livello alto",
    "emergenza",
    "alto (emergenza)",
    "e' previsto un livello di rischio alto",
]

# ── Telegram ─────────────────────────────────────────────────────────────────
import urllib.request
import urllib.parse

def send_telegram(message: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
    if not result.get("ok"):
        raise RuntimeError(f"Telegram error: {result}")
    print("✅ Messaggio Telegram inviato.")

# ── Scraping con Playwright ──────────────────────────────────────────────────
async def check_rischio_caldo() -> dict:
    """
    Apre la pagina Worklimate, digita il comune, attende i risultati
    e restituisce i livelli di rischio trovati per i 3 giorni.
    """
    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        page = await browser.new_page()

        print(f"🌐 Apro {URL} ...")
        await page.goto(URL, wait_until="networkidle", timeout=30000)

        # Cerca il campo di input del comune
        # Il sito usa un autocomplete/typeahead
        input_selector = 'input[type="text"], input[placeholder*="comune"], input[placeholder*="Comune"], input[placeholder*="localit"]'
        await page.wait_for_selector(input_selector, timeout=10000)

        print(f"🔍 Digito comune: {COMUNE}")
        await page.fill(input_selector, COMUNE)
        await asyncio.sleep(1.5)  # Attendo autocomplete

        # Prova a selezionare il primo suggerimento
        suggestion_selectors = [
            ".autocomplete-suggestion",
            ".suggestion",
            "[role='option']",
            ".pac-item",
            "ul li",
            ".dropdown-item",
        ]
        suggestion_found = False
        for sel in suggestion_selectors:
            try:
                await page.wait_for_selector(sel, timeout=3000)
                await page.click(sel)
                suggestion_found = True
                print(f"✅ Selezionato suggerimento con: {sel}")
                break
            except Exception:
                continue

        if not suggestion_found:
            # Prova con Enter
            print("⚠️  Nessun suggerimento trovato, provo con Enter")
            await page.keyboard.press("Enter")

        # Attendo che la pagina aggiorni i risultati
        await asyncio.sleep(3)
        await page.wait_for_load_state("networkidle", timeout=15000)

        # Prendi tutto il testo visibile
        page_text = await page.inner_text("body")
        page_text_lower = page_text.lower()

        # Screenshot per debug (salvato come artefatto in Actions)
        await page.screenshot(path="debug_screenshot.png", full_page=True)
        print("📸 Screenshot salvato: debug_screenshot.png")

        # ── Parsing dei livelli di rischio ──────────────────────────────────
        # La pagina mostra 3 giorni: Oggi, Domani, Dopodomani
        # Cerca i blocchi di testo per ciascun giorno
        giorni_found = []
        lines = page_text.split("\n")
        current_day = None
        current_livello = None

        for line in lines:
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            # Detecta riga giorno
            if any(g in line_lower for g in ["sabato", "domenica", "lunedì", "martedì",
                                              "mercoledì", "giovedì", "venerdì"]):
                if "202" in line_stripped:  # ha la data
                    current_day = line_stripped
                    current_livello = None

            # Detecta livello di rischio
            for kw in ["rischio basso", "rischio medio", "rischio alto",
                        "basso", "medio", "alto", "emergenza", "livello"]:
                if kw in line_lower and current_day:
                    if current_livello is None:
                        current_livello = line_stripped
                        giorni_found.append({
                            "giorno": current_day,
                            "livello": current_livello,
                        })
                    break

        results["giorni"] = giorni_found
        results["page_text"] = page_text
        results["alto_trovato"] = any(
            kw in page_text_lower for kw in KEYWORDS_ALTO
        )

        await browser.close()

    return results

# ── Main ────────────────────────────────────────────────────────────────────
async def main():
    print(f"\n{'='*60}")
    print(f"  Worklimate Bot  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Comune: {COMUNE}")
    print(f"{'='*60}\n")

    try:
        data = await check_rischio_caldo()
    except Exception as e:
        print(f"❌ Errore durante lo scraping: {e}")
        # Notifica errore tecnico su Telegram (opzionale, commentare se disturbante)
        # send_telegram(f"⚠️ <b>Worklimate Bot</b>\nErrore tecnico: {e}")
        sys.exit(1)

    giorni = data.get("giorni", [])
    alto_trovato = data.get("alto_trovato", False)

    print("\n📊 Risultati rilevati:")
    if giorni:
        for g in giorni:
            print(f"  {g['giorno']}  →  {g['livello']}")
    else:
        print("  ⚠️  Nessun dato strutturato trovato (vedi debug_screenshot.png)")
        # Fallback: usa il flag grezzo
        if alto_trovato:
            print("  ⚡ Keyword 'rischio alto' trovata nel testo grezzo!")

    # ── Costruisci riepilogo giorni ───────────────────────────────────────
    riepilogo_righe = []
    for g in giorni[:3]:
        livello = g["livello"].upper()
        if "ALTO" in livello or "EMERGENZA" in livello:
            emoji = "🔴"
        elif "MEDIO" in livello:
            emoji = "🟠"
        else:
            emoji = "🟢"
        riepilogo_righe.append(f"{emoji} {g['giorno']}: {g['livello']}")

    # ── Invia notifica solo se ALTO trovato ──────────────────────────────
    if alto_trovato:
        print("\n🚨 RISCHIO ALTO rilevato! Invio notifica Telegram...")

        giorni_alto = []
        for g in giorni:
            if any(kw in g["livello"].lower() for kw in ["alto", "emergenza"]):
                giorni_alto.append(g["giorno"])

        # Testo messaggio
        msg_giorni_alto = "\n".join(f"  🔴 {d}" for d in giorni_alto) if giorni_alto else "  🔴 (rilevato nel testo)"
        riepilogo_str = "\n".join(riepilogo_righe) if riepilogo_righe else "(dati non strutturati)"

        messaggio = (
            f"🚨 <b>RISCHIO CALDO ALTO — {COMUNE}</b>\n\n"
            f"Worklimate ha previsto <b>livello di rischio ALTO (Emergenza)</b> "
            f"per uno o più giorni:\n"
            f"{msg_giorni_alto}\n\n"
            f"<b>Riepilogo previsioni:</b>\n"
            f"{riepilogo_str}\n\n"
            f"⚠️ Modifica gli orari lavorativi, privilegia le ore più fresche, "
            f"aumenta le pause e l'idratazione.\n\n"
            f"🔗 <a href='{URL}'>Apri Worklimate</a>\n"
            f"🕐 Rilevato: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        send_telegram(messaggio)
    else:
        print("\n✅ Nessun rischio alto rilevato. Nessuna notifica inviata.")

    print("\nDone.\n")


if __name__ == "__main__":
    asyncio.run(main())
