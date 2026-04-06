import streamlit as st
import psycopg2
import pandas as pd
from sqlalchemy import create_engine, text
import os

# --- CONFIGURAÇÕES DE CONEXÃO (VOLTANDO PARA O MODO DIRETO) ---
# 1. Substitua [SUA-SENHA] pela senha do Banco.
# Note que voltamos para o endereço 'db.yvakbrkllvavtnzywkor.supabase.co'
DB_URL = "postgresql://postgres:[calecatusmay]@db.yvakbrkllvavtnzywkor.supabase.co:5432/postgres"

# 2. Senha de acesso ao site
SENHA_ACESSO = "sv2026" 

def criar_engine_sql():
    # Usamos o pool_pre_ping para ele testar a conexão antes de falhar
    return create_engine(DB_URL, pool_pre_ping=True)

def conectar_banco():
    return psycopg2.connect(DB_URL)

st.set_page_config(page_title="Oficina SV", layout="wide", page_icon="🔧")

# --- LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔐 Acesso Restrito - Oficina SV")
    senha_digitada = st.text_input("Senha:", type="password")
    if st.button("Entrar"):
        if senha_digitada == SENHA_ACESSO:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta!")
    st.stop()

# --- LOGO ---
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
caminho_logo = os.path.join(diretorio_atual, 'logo.png.png')
if os.path.exists(caminho_logo):
    st.sidebar.image(caminho_logo, use_container_width=True)
st.sidebar.write("**📍 Bataguassu - MS**")

# --- ABAS ---
aba1, aba2, aba3 = st.tabs(["🛠️ Nova O.S.", "📈 Histórico", "⚙️ Configurações"])

with aba1:
    st.subheader("📝 Registro de Manutenção")
    try:
        conn = conectar_banco()
        df_frota = pd.read_sql("SELECT numero_frota FROM dim_frota ORDER BY numero_frota", conn)
        lista_frotas = df_frota['numero_frota'].tolist()
        conn.close()
    except:
        lista_frotas = []
    
    if not lista_frotas:
        st.warning("⚠️ Nenhuma frota carregada. Vá em Configurações.")

    with st.form("form_os", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            frota_sel = st.selectbox("Frota", options=lista_frotas)
            mecanico = st.text_input("Mecânico")
        with c2:
            horimetro = st.number_input("Horímetro", step=0.1)
            tipo = st.selectbox("Tipo", ["OFICINA", "PREVENTIVA", "LUBRIFICAÇÃO"])
        
        servico = st.text_area("Descrição")
        if st.form_submit_button("✅ SALVAR"):
            try:
                conn = conectar_banco()
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS fato_os (id SERIAL PRIMARY KEY, data_reg TIMESTAMP DEFAULT CURRENT_TIMESTAMP, frota_id TEXT, mecanico_resp TEXT, descricao_servico TEXT, horimetro_decimal NUMERIC, tipo_os TEXT)")
                cur.execute("INSERT INTO fato_os (frota_id, mecanico_resp, descricao_servico, horimetro_decimal, tipo_os) VALUES (%s, %s, %s, %s, %s)", (frota_sel, mecanico, servico, horimetro, tipo))
                conn.commit()
                conn.close()
                st.success("Salvo com sucesso!")
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

with aba2:
    if st.button("🔄 Atualizar Histórico"):
        try:
            conn = conectar_banco()
            df = pd.read_sql("SELECT * FROM fato_os ORDER BY data_reg DESC", conn)
            st.dataframe(df, use_container_width=True)
            conn.close()
        except:
            st.info("Sem dados.")

with aba3:
    st.subheader("📦 Importar Frota")
    arquivo = st.file_uploader("Arquivo CSV", type=['csv', 'txt'])
    if arquivo:
        try:
            df_import = pd.read_csv(arquivo, sep=None, engine='python', encoding='latin1')
            if len(df_import.columns) >= 4:
                df_import = df_import.iloc[:, :4]
                df_import.columns = ['numero_frota', 'tipo_bem', 'descricao', 'setor_padrao']
                st.dataframe(df_import.head())
                if st.button("🚀 EXECUTAR CARGA"):
                    engine = criar_engine_sql()
                    with engine.begin() as conn:
                        conn.execute(text("CREATE TABLE IF NOT EXISTS dim_frota (numero_frota TEXT PRIMARY KEY, tipo_bem TEXT, descricao TEXT, setor_padrao TEXT)"))
                        conn.execute(text("TRUNCATE TABLE dim_frota CASCADE;"))
                        df_import.to_sql('dim_frota', conn, if_exists='append', index=False)
                    st.success("Frota carregada!")
            else:
                st.error("O arquivo precisa de 4 colunas.")
        except Exception as e:
            st.error(f"Erro: {e}")