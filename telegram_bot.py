import logging
import requests
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters


# URL da sua API FastAPI
API_URL = "http://127.0.0.1:8000/transacoes/dinheiro"
TELEGRAM_TOKEN = "8503783159:AAHqelwsoffaZe_IQomuaSPxkHQdkNNWZbQ"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def receber_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    chat_id = update.message.chat_id

    # Envia a mensagem para a API FastAPI processar via LLM
    try:
        response = requests.post(API_URL, json={"mensagem": texto}, timeout=10)
        
        if response.status_code == 201:
            dados = response.json()
            valor_fmt = f"R$ {dados['valor']:.2f}".replace('.', ',')
            
            resposta_telegram = (
                f"✅ **Gasto registrado!**\n\n"
                f"• **Descrição:** {dados['descricao']}\n"
                f"• **Valor:** {valor_fmt}\n"
                f"• **Categoria:** {dados['categoria']}\n"
                f"• **Forma:** {dados['metodo_pagamento']}"
            )
        else:
            resposta_telegram = "⚠️ Não consegui entender essa compra. Tente enviar algo como: '20 reais padaria'."
            
    except Exception as e:
        resposta_telegram = f"❌ Erro ao se comunicar com o servidor: {e}"

    await update.message.reply_text(resposta_telegram, parse_mode="Markdown")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), receber_mensagem))
    
    print("Bot do Telegram em execução...")
    app.run_polling()