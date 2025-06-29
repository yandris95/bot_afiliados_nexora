# Guarda este código en un archivo llamado bot.py

import logging
import requests
import datetime
import os  # Importamos la librería 'os' para acceder a las variables de entorno

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURACIÓN SEGURA ---
# Leemos las credenciales desde las Variables de Entorno del servidor (Render)
# ¡NUNCA escribas tus tokens directamente en el código!
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')
WEB_LINK = 'https://oportunidad-exclusiva-ga-a0v9paa.gamma.site/'

# --- Verificación de que las variables existen ---
if not all([TELEGRAM_BOT_TOKEN, NOTION_TOKEN, NOTION_DATABASE_ID]):
    # Si falta alguna variable, el bot no se iniciará y avisará en los logs.
    raise ValueError("Error: Una o más variables de entorno (TELEGRAM_BOT_TOKEN, NOTION_TOKEN, NOTION_DATABASE_ID) no están configuradas.")

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
        response.raise_for_status()  # Esto lanzará un error para códigos 4xx/5xx
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
    update_data = {
        "properties": {
            "PDF Enviado": {"checkbox": True},
            "Fecha de registro": {"date": {"start": now_iso}}
        }
    }

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
            f"Aquí tienes tu acceso exclusivo: {WEB_LINK}\n\n"
            "🚀 ¡Mucho éxito en esta nueva etapa como afiliado!"
        )
    else:
        await update.message.reply_text(
            f"❌ Lo sentimos, no encontramos el nombre '{nombre}' en nuestra base de datos.\n\n"
            "Por favor, asegúrate de escribirlo exactamente igual que en el formulario. Si el problema persiste, contacta con soporte."
        )
    
    pending_users.remove(user_id)

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_name))
    
    logger.info("🚀 Bot iniciando y listo para recibir mensajes...")
    app.run_polling()

if __name__ == '__main__':
    main()