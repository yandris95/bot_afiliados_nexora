# Contenido para bot.py

import logging
import requests
import datetime
import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURACIÓN ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')

# --- LÓGICA DEL BOT (Esto no cambia) ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
pending_users = set()
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"
}

def update_notion_by_name(name: str) -> bool:
    logger.info(f"🔎 Buscando en Notion: {name}")
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    query = {"filter": {"property": "Nombre", "title": {"equals": name}}}
    try:
        response = requests.post(url, headers=NOTION_HEADERS, json=query)
        response.raise_for_status()
        results = response.json().get("results")
        if not results:
            logger.warning(f"🤷‍♂️ Nombre no encontrado: {name}")
            return False
        page_id = results[0]["id"]
        update_url = f"https://api.notion.com/v1/pages/{page_id}"
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        update_data = {"properties": {"PDF Enviado": {"checkbox": True}, "Fecha de registro": {"date": {"start": now_iso}}}}
        update_response = requests.patch(update_url, headers=NOTION_HEADERS, json=update_data)
        update_response.raise_for_status()
        logger.info(f"✅ Registro actualizado para: {name}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error en la API de Notion: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pending_users.add(update.message.from_user.id)
    await update.message.reply_text("👋 ¡Hola! Bienvenido. Por favor, escribe tu nombre completo tal como lo pusiste en el formulario.")

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in pending_users:
        await update.message.reply_text("⚠️ Por favor, inicia con /start.")
        return
    nombre = update.message.text.strip()
    if update_notion_by_name(nombre):
        await update.message.reply_text(f"✅ ¡Gracias, {nombre}! Registro confirmado.🎉\n\nAquí tienes tu acceso: https://oportunidad-exclusiva-ga-a0v9paa.gamma.site/")
    else:
        await update.message.reply_text(f"❌ No encontramos '{nombre}'. Revisa que esté escrito exactamente igual que en el formulario.")
    pending_users.remove(user_id)

# --- ESTRUCTURA CORRECTA PARA RENDER ---
# 1. Construye la aplicación de Telegram
ptb_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
ptb_app.add_handler(CommandHandler("start", start))
ptb_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_name))

# 2. Inicializa la aplicación (la "llave de arranque" que faltaba en el lugar correcto)
# Esto se ejecuta UNA SOLA VEZ cuando Render carga el archivo.
asyncio.run(ptb_app.initialize())

# 3. Crea el servidor web Flask
app = Flask(__name__)

# 4. Define el webhook, que ahora es una función ASÍNCRONA
@app.route("/", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), ptb_app.bot)
    await ptb_app.process_update(update)
    return "ok"
