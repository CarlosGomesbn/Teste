import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(override=True)

st.set_page_config(
    page_title="Gestor Financeiro Doméstico",
    page_icon="📊",
    layout="wide"
)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    st.error("❌ DATABASE_URL não encontrada no arquivo .env!")
    st.stop()

# Ajusta prefixo do driver e garante parâmetro SSL para o Neon
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

if "sslmode" not in DATABASE_URL and not DATABASE_URL.startswith("sqlite"):
    DATABASE_URL += "&sslmode=require" if "?" in DATABASE_URL else "?sslmode=require"

@st.cache_data(ttl=10)
def carregar_dados():
    engine = create_engine(
        DATABASE_URL,
        connect_args={"connect_timeout": 10} if not DATABASE_URL.startswith("sqlite") else {}
    )
    with engine.connect() as conn:
        df = pd.read_sql_query(text("SELECT * FROM transacoes ORDER BY data DESC"), conn)
    return df

st.title("📊 Painel de Controle Financeiro")

try:
    df = carregar_dados()
    
    if df.empty:
        st.info("Nenhuma transação registrada ainda no banco de dados.")
    else:
        df['data'] = pd.to_datetime(df['data'])
        
        # --- Métricas Principais ---
        col1, col2, col3 = st.columns(3)
        
        total_gasto = df['valor'].sum()
        qtd_transacoes = len(df)
        ticket_medio = total_gasto / qtd_transacoes if qtd_transacoes > 0 else 0

        col1.metric("Total Gasto", f"R$ {total_gasto:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        col2.metric("Lançamentos", f"{qtd_transacoes}")
        col3.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

        st.markdown("---")

        # --- Gráficos ---
        col_graf1, col_graf2 = st.columns(2)

        with col_graf1:
            st.subheader("Gastos por Categoria")
            gastos_categoria = df.groupby('categoria')['valor'].sum().reset_index()
            st.bar_chart(gastos_categoria.set_index('categoria'))

        with col_graf2:
            st.subheader("Gastos por Método")
            gastos_metodo = df.groupby('metodo_pagamento')['valor'].sum().reset_index()
            st.bar_chart(gastos_metodo.set_index('metodo_pagamento'))

        # --- Tabela Detalhada ---
        st.markdown("---")
        st.subheader("📜 Histórico de Transações")
        st.dataframe(
            df[['id', 'data', 'descricao', 'categoria', 'valor', 'metodo_pagamento']],
            use_container_width=True
        )

except Exception as e:
    st.error(f"Erro ao conectar com o banco de dados: {e}")