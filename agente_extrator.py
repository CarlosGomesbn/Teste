import os
import json
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from dotenv import load_dotenv

load_dotenv(override=True)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def processar_gasto_dinheiro(mensagem_texto: str) -> dict:
    modelo = genai.GenerativeModel('gemini-3.8-flash')
    
    prompt = f"""
    Você é um agente de extração de dados financeiros.
    Leia a mensagem abaixo e extraia as informações no formato JSON estrito usando EXATAMENTE estas chaves:

    - "valor": (número float, apenas o valor numérico ex: 40.0)
    - "descricao": (string simples com o nome do local ou produto ex: "padaria")
    - "categoria": (string, escolha estritamente uma destas opções: "Alimentação", "Transporte", "Saúde", "Casa", "Lazer", "Outros")

    Mensagem do usuário: "{mensagem_texto}"
    """

    try:
        resposta = modelo.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        dados = json.loads(resposta.text)
        print(f"🔍 DEBUG GEMINI RESPOSTA: {dados}", flush=True)

        # Trata e garante que a chave 'valor' seja numérica
        if "valor" in dados:
            if isinstance(dados["valor"], str):
                val_limpo = ''.join(c for c in dados["valor"] if c.isdigit() or c in ['.', ',']).replace(',', '.')
                dados["valor"] = float(val_limpo) if val_limpo else 0.0
            else:
                dados["valor"] = float(dados["valor"])

        dados["metodo_pagamento"] = "Dinheiro"
        return dados

    except ResourceExhausted:
        print("⚠️ Limite de requisições por minuto do Gemini atingido.", flush=True)
        return {"erro": "quota_exceeded"}
    except Exception as e:
        print(f"❌ Erro ao processar mensagem no Gemini: {e}", flush=True)
        return None