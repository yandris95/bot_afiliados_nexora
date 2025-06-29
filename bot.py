import logging
import requests
import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURACIÓN ---
TELEGRAM_BOT_TOKEN = '7811966001:AAG2L6-ZOvzefKljQoAAFEyaapA98JVx1v8'
NOTION_TOKEN = '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'
NOTION_DATABASE_ID = '220ed096dd1c80aba7cecccc6e0841f4'
WEB_LINK = 'https://oportunidad-exclusiva-ga-a0v9paa.gamma.site/'

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

pending_users = set()

def update_notion_by_name(name: str) -> bool:
    logging.info(f"Buscando en Notion al usuario con nombre: {name}")
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    query = {
        "filter": {
            "property": "Nombre",
            "title": {
                "equals": name
            }
        }
    }

    response = requests.post(url, headers=NOTION_HEADERS, json=query)
    if response.status_code != 200:
        logging.error(f"Error buscando en Notion: {response.status_code} - {response.text}")
        return False

    results = response.json().get("results")
    if not results:
        logging.info(f"No se encontró el nombre {name} en Notion")
        return False

    page_id = results[0]["id"]
    update_url = f"https://api.notion.com/v1/pages/{page_id}"

    now_iso = datetime.datetime.utcnow().isoformat()
    update_data = {
        "properties": {
            "PDF Enviado": {"checkbox": True},
            "Fecha de registro": {"date": {"start": now_iso}}
        }
    }

    update_response = requests.patch(update_url, headers=NOTION_HEADERS, json=update_data)
    if update_response.status_code != 200:
        logging.error(f"Error actualizando Notion: {update_response.status_code} - {update_response.text}")
        return False

    logging.info(f"Notion actualizado para {name}")
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args  # Esto recibe lo que venga después de /start

    pending_users.add(user_id)

    if args and args[0].lower() == 'hola':
        await update.message.reply_text(
            "Hola. Bienvenido al equipo de afiliados de Nexora Studio.\n\n"
            "Por favor, escribe tu nombre tal como lo escribiste en el formulario para confirmar tu registro."
        )
    else:
        await update.message.reply_text(
            "Hola. Para comenzar, por favor escribe tu nombre tal como aparece en el formulario."
        )

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if user_id not in pending_users:
        await update.message.reply_text(
            "Por favor, inicia primero con /start o con el enlace que te enviamos."
        )
        return

    nombre = text
    encontrado = update_notion_by_name(nombre)

    if encontrado:
        await update.message.reply_text(
            f"Gracias, {nombre}.\n\n"
            f"Aquí tienes acceso exclusivo: {WEB_LINK}\n\n"
            f"Te deseamos mucho éxito como afiliado."
        )
    else:
        await update.message.reply_text(
            f"No encontramos el nombre '{nombre}' en nuestra base de datos.\n"
            "Por favor verifica que lo hayas escrito igual que en el formulario."
        )

    pending_users.remove(user_id)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_name))
    logging.info("Bot funcionando correctamente.")
    app.run_polling()
