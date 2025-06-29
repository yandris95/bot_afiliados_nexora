# ==========================================================
#         CÓDIGO FINAL Y DEFINITIVO PARA EL BOT
# ==========================================================

import logging
import requests
import datetime
import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- ZONA DE CONFIGURACIÓN (NO TOCAR) ---
# Lee las variables directamente desde Render.
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')

# --- LÓGICA DEL BOT (Esto funciona bien y no se toca) ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
pending_users = set()
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"
}

def update_notion_by_name(name: str) -> bool:
    logger.info(f"🔎 Buscando en Notion: {name}")
    try:
        url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
        query = {"filter": {"property": "Nombre", "title": {"equals": name}}}
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

# --- ESTRUCTURA FINAL Y ROBUSTA ---

# Esta es la función principal que se ejecuta CADA VEZ que llega un mensaje.
async def main(update_json):
    # Construimos la aplicación de Telegram desde cero en cada llamada.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Añadimos los manejadores de comandos.
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_name))
    
    # "Encendemos" la aplicación.
    await application.initialize()
    
    # Procesamos el mensaje que nos llegó de Telegram.
    update = Update.de_json(update_json, application.bot)
    await application.process_update(update)
    
    # "Apagamos" la aplicación para limpiar todo.
    await application.shutdown()

# Este es el servidor web Flask, ahora mucho más simple.
app = Flask(__name__)

@app.route("/", methods=["POST"])
def webhook():
    # Cuando Telegram nos contacta, ejecutamos nuestra función principal.
    # asyncio.run crea un entorno limpio para cada mensaje.
    asyncio.run(main(request.get_json(force=True)))
    return "ok"
