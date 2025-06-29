import logging
import requests
import datetime
import os
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURACIÓN SEGURA ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')
WEBHOOK_URL = os.environ.get('RENDER_EXTERNAL_URL') # Esta variable la da Render automáticamente

if not all([TELEGRAM_BOT_TOKEN, NOTION_TOKEN, NOTION_DATABASE_ID]):
    raise ValueError("Error: Faltan variables de entorno críticas.")

# --- Lógica del Bot (exactamente la misma que antes) ---
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
pending_users = set()

def update_notion_by_name(name: str) -> bool:
    logger.info(f"🔎 Buscando en Notion el nombre: {name}")
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    query = {"filter": {"property": "Nombre", "title": {"equals": name}}}
    try:
        response = requests.post(url, headers=NOTION_HEADERS, json=query)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error en la petición a Notion: {e}")
        return False
    results = response.json().get("results")
    if not results:
        logger.warning(f"🤷‍♂️ Nombre no encontrado en Notion: {name}")
        return False
    page_id = results[0]["id"]
    update_url = f"https://api.notion.com/v1/pages/{page_id}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    update_data = {"properties": {"PDF Enviado": {"checkbox": True}, "Fecha de registro": {"date": {"start": now_iso}}}}
    try:
        update_response = requests.patch(update_url, headers=NOTION_HEADERS, json=update_data)
        update_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error actualizando la página de Notion: {e}")
        return False
    logger.info(f"✅ Registro de '{name}' actualizado correctamente en Notion.")
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    pending_users.add(user_id)
    await update.message.reply_text(
        "👋 ¡Hola! Bienvenido al equipo de afiliados de Nexora Studio.\n\n"
        "✍️ Por favor, escribe tu nombre completo, tal como lo escribiste en el formulario, para confirmar tu registro."
    )

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    nombre = update.message.text.strip()
    if user_id not in pending_users:
        await update.message.reply_text("⚠️ Por favor, inicia la conversación con el comando /start.")
        return
    encontrado = update_notion_by_name(nombre)
    if encontrado:
        await update.message.reply_text(
            f"✅ ¡Gracias, {nombre}! Tu registro ha sido confirmado. 🎉\n\n"
            f"Aquí tienes tu acceso exclusivo: https://oportunidad-exclusiva-ga-a0v9paa.gamma.site/\n\n"
            "🚀 ¡Mucho éxito en esta nueva etapa como afiliado!"
        )
    else:
        await update.message.reply_text(
            f"❌ Lo sentimos, no encontramos el nombre '{nombre}' en nuestra base de datos.\n\n"
            "Por favor, asegúrate de escribirlo exactamente igual que en el formulario. Si el problema persiste, contacta con soporte."
        )
    pending_users.remove(user_id)

# --- Configuración del Servidor Web (Flask) y Webhook ---
# ESTA ES LA LÍNEA QUE GUNICORN BUSCA Y NO ENCONTRABA
app = Flask(__name__) 
# --------------------------------------------------------

ptb_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
ptb_app.add_handler(CommandHandler("start", start))
ptb_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_name))

@app.route("/", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), ptb_app.bot)
    await ptb_app.process_update(update)
    return "ok"

async def setup():
    if not WEBHOOK_URL:
        logger.warning("RENDER_EXTERNAL_URL no encontrada, saltando configuración de webhook.")
        return
    await ptb_app.bot.set_webhook(url=f"{WEBHOOK_URL}")
    logger.info(f"✅ Webhook configurado en: {WEBHOOK_URL}")

# Se crea un loop de eventos para correr la función asíncrona de setup
import asyncio
# Solo se ejecuta una vez al inicio del programa
if __name__ != "__main__":
    asyncio.run(setup())
