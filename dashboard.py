import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# Configuração da página
st.set_page_config(
    page_title="Painel de Controle Financeiro",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Painel de Controle de Gastos Mensais")
st.markdown("Acompanhamento consolidado de compras no **Cartão** e no **Dinheiro**.")

# --- Conexão com o Banco de Dados ---
def carregar_dados():
    try:
        conn = sqlite3.connect("gastos.db")
        df = pd.read_sql_query("SELECT * FROM transacoes", conn)
        conn.close()
        if not df.empty:
            df['data'] = pd.to_datetime(df['data'])
        return df
    except Exception as e:
        st.error(f"Erro ao acessar o banco de dados: {e}")
        return pd.DataFrame()

df = carregar_dados()

# Botão para recarregar dados manualmente
if st.sidebar.button("🔄 Atualizar Dados"):
    st.rerun()

if df.empty:
    st.info("Nenhuma transação encontrada no banco de dados. Adicione novos gastos via API para visualizar os gráficos.")
    st.stop()

# --- Barra Lateral (Filtros) ---
st.sidebar.header("🔍 Filtros de Exibição")

# 1. Filtro por Método de Pagamento
metodos = ["Todos"] + list(df['metodo_pagamento'].unique())
metodo_sel = st.sidebar.selectbox("Tipo de Pagamento", metodos)

# 2. Filtro por Categoria / Segmento
categorias = ["Todas"] + list(df['categoria'].unique())
categoria_sel = st.sidebar.selectbox("Segmento / Categoria", categorias)

# 3. Filtro por Período
data_min = df['data'].min().date()
data_max = df['data'].max().date()
periodo = st.sidebar.date_input("Período de Análise", [data_min, data_max])

# --- Aplicação dos Filtros ---
df_filtrado = df.copy()

if metodo_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['metodo_pagamento'] == metodo_sel]

if categoria_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado['categoria'] == categoria_sel]

if len(periodo) == 2:
    data_inicio, data_fim = periodo
    df_filtrado = df_filtrado[
        (df_filtrado['data'].dt.date >= data_inicio) & 
        (df_filtrado['data'].dt.date <= data_fim)
    ]

# --- KPIs / Métricas Principais ---
m1, m2, m3, m4 = st.columns(4)

total_geral = df_filtrado['valor'].sum()
total_cartao = df_filtrado[df_filtrado['metodo_pagamento'] == 'Cartão']['valor'].sum()
total_dinheiro = df_filtrado[df_filtrado['metodo_pagamento'] == 'Dinheiro']['valor'].sum()
qtd_compras = len(df_filtrado)

m1.metric("Gasto Total", f"R$ {total_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
m2.metric("Total Cartão", f"R$ {total_cartao:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
m3.metric("Total Dinheiro", f"R$ {total_dinheiro:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
m4.metric("Qtd. de Compras", qtd_compras)

st.markdown("---")

# --- Gráficos Principais ---
col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    st.subheader("🏷️ Gastos por Segmento / Categoria")
    if not df_filtrado.empty:
        df_cat = df_filtrado.groupby('categoria')['valor'].sum().reset_index()
        fig_cat = px.bar(
            df_cat,
            x='categoria',
            y='valor',
            labels={'categoria': 'Categoria', 'valor': 'Total (R$)'},
            text_auto='.2f',
            color='categoria'
        )
        fig_cat.update_layout(showlegend=False)
        st.plotly_chart(fig_cat, use_container_width=True)

with col_graf2:
    st.subheader("💳 Divisão por Tipo de Pagamento")
    if not df_filtrado.empty:
        df_pag = df_filtrado.groupby('metodo_pagamento')['valor'].sum().reset_index()
        fig_pag = px.pie(
            df_pag,
            values='valor',
            names='metodo_pagamento',
            hole=0.45,
            color='metodo_pagamento',
            color_discrete_map={'Cartão': '#2b5c8f', 'Dinheiro': '#2e8b57'}
        )
        st.plotly_chart(fig_pag, use_container_width=True)

# --- Evolução Temporal ---
st.subheader("📈 Linha do Tempo de Gastos")
if not df_filtrado.empty:
    df_tempo = df_filtrado.groupby([df_filtrado['data'].dt.date, 'metodo_pagamento'])['valor'].sum().reset_index()
    fig_tempo = px.line(
        df_tempo,
        x='data',
        y='valor',
        color='metodo_pagamento',
        markers=True,
        labels={'data': 'Data', 'valor': 'Valor (R$)', 'metodo_pagamento': 'Pagamento'}
    )
    st.plotly_chart(fig_tempo, use_container_width=True)

# --- Tabela Detalhada ---
st.subheader("📋 Tabela de Registros")
df_tabela = df_filtrado.sort_values(by='data', ascending=False)
st.dataframe(
    df_tabela[['data', 'descricao', 'categoria', 'metodo_pagamento', 'valor']],
    use_container_width=True,
    column_config={
        "data": st.column_config.DatetimeColumn("Data e Hora", format="DD/MM/YYYY HH:mm"),
        "descricao": "Descrição",
        "categoria": "Segmento",
        "metodo_pagamento": "Tipo de Pagamento",
        "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")
    }
)