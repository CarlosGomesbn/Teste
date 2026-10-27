import os
import json
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters
)

import database
from agente_extrator import processar_gasto_dinheiro, genai

# Força o recarregamento do .env
load_dotenv(override=True)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


# --- Comando /start ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Sou o assistente de gastos domésticos.\n\n"
        "Envie seus gastos em dinheiro como:\n"
        "• *20 reais padaria*\n"
        "• *45.50 mercado*\n"
        "• *15 pastel de carne*",
        parse_mode="Markdown"
    )

# --- Processamento de Gastos ---
def processar_e_salvar_gasto(texto: str) -> str:
    db = database.SessionLocal()
    try:
        dados = processar_gasto_dinheiro(texto)
        if dados and "valor" in dados and dados.get("valor", 0) > 0:
            nova_transacao = database.Transacao(
                valor=dados.get("valor", 0.0),
                descricao=dados.get("descricao", "Sem descrição"),
                categoria=dados.get("categoria", "Outros"),
                metodo_pagamento="Dinheiro"
            )
            db.add(nova_transacao)
            db.commit()
            db.refresh(nova_transacao)

            valor_fmt = f"R$ {nova_transacao.valor:.2f}".replace('.', ',')
            return (
                f"✅ **Gasto registrado!**\n\n"
                f"• **Descrição:** {nova_transacao.descricao}\n"
                f"• **Valor:** {valor_fmt}\n"
                f"• **Categoria:** {nova_transacao.categoria}\n"
                f"• **Forma:** Dinheiro"
            )
        else:
            return "⚠️ Não consegui identificar o valor na mensagem. Tente algo como: '20 reais padaria'."
    except Exception as e:
        return f"❌ Erro interno: {e}"
    finally:
        db.close()

async def tratar_mensagem_telegram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    print(f"📩 Mensagem recebida no Telegram: '{texto}'", flush=True)
    
    try:
        # Executa o Gemini e o Banco em uma thread separada para não travar o loop assíncrono
        resposta = await asyncio.to_thread(processar_e_salvar_gasto, texto)
        await update.message.reply_text(resposta, parse_mode="Markdown")
        print("✅ Resposta enviada ao usuário no Telegram!", flush=True)
    except Exception as e:
        print(f"❌ ERRO NO HANDLER DO TELEGRAM: {e}", flush=True)
        await update.message.reply_text("❌ Ocorreu um erro interno ao processar a mensagem.")

# --- Ciclo de Vida do FastAPI (Com flush=True) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    token = os.getenv("TELEGRAM_TOKEN")
    
    print("\n" + "="*40, flush=True)
    print("🚀 INICIANDO SERVIDOR E RECURSOS", flush=True)
    print(f"• TELEGRAM_TOKEN: {token[:8] + '...' if token else '❌ NÃO ENCONTRADO'}", flush=True)
    
    # Inicializa o banco de dados sem travar a subida da API
    try:
        database.init_db()
        print("• BANCO DE DADOS: ✅ Conectado com sucesso", flush=True)
    except Exception as e:
        print(f"• BANCO DE DADOS: ❌ Erro ao conectar ({e})", flush=True)

    print("="*40 + "\n", flush=True)

    if token:
        try:
            tg_app = ApplicationBuilder().token(token).build()
            await tg_app.bot.delete_webhook(drop_pending_updates=True)
            
            tg_app.add_handler(CommandHandler("start", start_command))
            tg_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), tratar_mensagem_telegram))
            
            await tg_app.initialize()
            await tg_app.start()
            await tg_app.updater.start_polling()
            print("🟢 BOT DO TELEGRAM ATIVO E AGUARDANDO MENSAGENS!", flush=True)
        except Exception as e:
            print(f"❌ Erro ao ligar o Bot do Telegram: {e}", flush=True)
    else:
        print("🔴 ALERTA: TELEGRAM_TOKEN está vazio no .env!", flush=True)
    
    yield
    
    if token and 'tg_app' in locals():
        print("🛑 Desligando Bot do Telegram...", flush=True)
        await tg_app.updater.stop()
        await tg_app.stop()
        await tg_app.shutdown()


app = FastAPI(title="Gestor de Gastos Doméstico", version="1.0.0", lifespan=lifespan)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Endpoints da API ---
class EntradaCartaoWebhook(BaseModel):
    texto_notificacao: str

class TransacaoOut(BaseModel):
    id: int
    data: datetime
    valor: float
    descricao: str
    categoria: str
    metodo_pagamento: str

    class Config:
        from_attributes = True

@app.post("/transacoes/cartao", response_model=TransacaoOut, status_code=status.HTTP_201_CREATED)
def registrar_gasto_cartao(item: EntradaCartaoWebhook, db: Session = Depends(get_db)):
    modelo = genai.GenerativeModel('gemini-3.8-flash')
    prompt = f"""
    Extraia o valor da compra, o estabelecimento (descrição) e uma categoria da seguinte notificação bancária:
    "{item.texto_notificacao}"
    
    Regras estritas:
    1. Retorne APENAS um JSON no formato:
       {{"valor": 0.0, "descricao": "string", "categoria": "string"}}
    2. Categorias permitidas: "Alimentação", "Transporte", "Saúde", "Casa", "Lazer", "Outros".
    """
    
    resposta = modelo.generate_content(prompt)
    try:
        texto_limpo = resposta.text.replace('```json', '').replace('```', '').strip()
        dados = json.loads(texto_limpo)
    except Exception:
        raise HTTPException(status_code=400, detail="Erro ao processar notificação do cartão.")

    nova_transacao = database.Transacao(
        valor=dados.get("valor", 0.0),
        descricao=dados.get("descricao", "Compra Cartão"),
        categoria=dados.get("categoria", "Outros"),
        metodo_pagamento="Cartão"
    )

    db.add(nova_transacao)
    db.commit()
    db.refresh(nova_transacao)
    return nova_transacao

@app.get("/transacoes", response_model=List[TransacaoOut])
def listar_transacoes(
    categoria: Optional[str] = None,
    metodo_pagamento: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(database.Transacao)
    if categoria:
        query = query.filter(database.Transacao.categoria == categoria)
    if metodo_pagamento:
        query = query.filter(database.Transacao.metodo_pagamento == metodo_pagamento)
    return query.all()