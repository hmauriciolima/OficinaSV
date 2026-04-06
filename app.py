import streamlit as st
import psycopg2
import pandas as pd
from sqlalchemy import create_engine, text
import os
import urllib.parse

# --- CONFIGURAÇÕES DE CONEXÃO ---

# 1. Sua senha do banco (VerginiaAgro2026)
SENHA_BANCO = "VerginiaAgro2026"

# 2. Seu ID de projeto (yvakbrkllvavtnzywkor)
PROJECT_ID = "yvakbrkllvavtnzywkor"

# 3. Senha de acesso ao site
SENHA_ACESSO = "sv2026"

# --- MONTAGEM DA CONEXÃO (PORTA 6543 - MODO TRANSACTION) ---
# O segredo: Usuário deve ser exatamente postgres.[ID_DO_PROJETO]
USUARIO = f"postgres.{PROJECT_ID}"
senha_safe = urllib.parse.quote_plus(SENHA_BANCO)

# Usamos a porta 6543, que é a porta do Pooler que resolve o erro de "Tenant not found"
DB_URL = f"postgresql://{USUARIO}:{senha_safe}@aws-0-sa-east-1.pooler.supabase.com:6543/postgres?sslmode=require"

def criar_engine_sql():
    return create_engine(DB_URL, pool_pre_ping=True)

def conectar_banco():
    return psycopg2.connect(DB_URL)

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Oficina SV", layout="wide", page_icon="🔧")

# --- LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔐 Acesso Restrito - Oficina SV")
    senha_digitada = st.text_input("Digite a senha de acesso:", type="password")
    if st.button("Entrar"):
        if senha_digitada == SENHA_ACESSO:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta!")
    st.stop()

# --- LOGOTIPO ---
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
caminho_logo = os.path.join(diretorio_atual, 'logo.png.png')
if os.path.exists(caminho_logo):
    st.sidebar.image(caminho_logo, use_container_width=True)
st.sidebar.markdown("---")
st.sidebar.write("**📍 Bataguassu - MS**")

st.title("📋 Controle de Ordem de Serviço - Oficina SV")

# --- FUNÇÕES ---
def listar_frotas():
    try:
        conn = conectar_banco()
        df = pd.read_sql("SELECT numero_frota FROM dim_frota ORDER BY numero_frota", conn)
        conn.close()
        return df['numero_frota'].tolist()
    except:
        return []

aba1, aba2, aba3 = st.tabs(["🛠️ Nova O.S.", "📈 Histórico", "⚙️ Configurações"])

with aba1:
    st.subheader("📝 Registro de Manutenção")
    lista_frotas = listar_frotas()
    
    if not lista_frotas:
        st.warning("⚠️ Nenhuma frota cadastrada. Vá em 'Configurações' e carregue a frota.")
    
    with st.form("form_os", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            frota_sel = st.selectbox("Nº da Frota", options=lista_frotas)
            mecanico = st.text_input("Mecânico")
        with c2:
            horimetro = st.number_input("Horímetro", step=0.1)
            tipo = st.selectbox("Tipo", ["OFICINA", "LUBRIFICAÇÃO", "PREVENTIVA", "TERCEIROS"])

        servico = st.text_area("Descrição")
        
        if st.form_submit_button("✅ SALVAR"):
            try:
                conn = conectar_banco()
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS fato_os (
                        id SERIAL PRIMARY KEY, 
                        data_reg TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                        frota_id TEXT, 
                        mecanico_resp TEXT, 
                        descricao_servico TEXT, 
                        horimetro_decimal NUMERIC, 
                        tipo_os TEXT
                    )
                """)
                cur.execute("INSERT INTO fato_os (frota_id, mecanico_resp, descricao_servico, horimetro_decimal, tipo_os) VALUES (%s, %s, %s, %s, %s)", (frota_sel, mecanico, servico, horimetro, tipo))
                conn.commit()
                conn.close()
                st.success("Salvo com sucesso!")
                st.balloons()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

with aba2:
    if st.button("🔄 Atualizar Relatório"):
        try:
            conn = conectar_banco()
            df_hist = pd.read_sql("SELECT data_reg as Data, frota_id as Frota, mecanico_resp as Mecânico, tipo_os as Tipo, descricao_servico as Serviço FROM fato_os ORDER BY data_reg DESC", conn)
            st.dataframe(df_hist, use_container_width=True)
            conn.close()
        except:
            st.info("Sem dados registrados.")

with aba3:
    st.subheader("📦 Importação de Frota Master")
    arquivo = st.file_uploader("Arquivo CSV ou TXT", type=['txt', 'csv'])
    
    if arquivo:
        try:
            df_import = pd.read_csv(arquivo, sep=None, engine='python', encoding='latin1')
            if len(df_import.columns) >= 4:
                df_import = df_import.iloc[:, :4]
                df_import.columns = ['numero_frota', 'tipo_bem', 'descricao', 'setor_padrao']
                st.dataframe(df_import.head())

                if st.button("🚀 EXECUTAR CARGA"):
                    try:
                        engine = criar_engine_sql()
                        with engine.begin() as conn_engine:
                            conn_engine.execute(text("CREATE TABLE IF NOT EXISTS dim_frota (numero_frota TEXT PRIMARY KEY, tipo_bem TEXT, descricao TEXT, setor_padrao TEXT)"))
                            conn_engine.execute(text("TRUNCATE TABLE dim_frota CASCADE;"))
                            df_import.to_sql('dim_frota', conn_engine, if_exists='append', index=False)
                        st.success("Frota carregada com sucesso!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Erro na carga: {e}")
            else:
                st.error("O arquivo precisa de 4 colunas.")
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {e}")