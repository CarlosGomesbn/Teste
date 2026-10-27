import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(override=True)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def processar_gasto_dinheiro(mensagem_texto: str) -> dict:
    modelo = genai.GenerativeModel('gemini-3.8-flash')
    
    prompt = f"""
    Você é um agente de extração de dados financeiros.
    Leia a mensagem abaixo, extraia o valor numérico, a descrição e escolha a categoria mais adequada.

    Categorias permitidas: "Alimentação", "Transporte", "Saúde", "Casa", "Lazer", "Outros".
    
    Mensagem do usuário: "{mensagem_texto}"
    """

    try:
        # Força o Gemini a responder estritamente em formato JSON
        resposta = modelo.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        dados = json.loads(resposta.text)
        print(f"🔍 DEBUG GEMINI: {dados}", flush=True)
        
        # Garante que 'metodo_pagamento' exista na resposta
        dados["metodo_pagamento"] = "Dinheiro"
        return dados
    except Exception as e:
        print(f"❌ Erro ao processar mensagem no Gemini: {e}", flush=True)
        return None