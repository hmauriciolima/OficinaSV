import streamlit as st
import psycopg2
import pandas as pd
from sqlalchemy import create_engine, text
import os
import urllib.parse

# --- CONFIGURAÇÕES DE CONEXÃO (MODO SUPREME POOLER) ---
# 1. Coloque APENAS a sua senha do Supabase entre as aspas abaixo:
SENHA_BANCO = "calecatusmay"

# 2. O seu usuário completo (NÃO ALTERE ESTA LINHA):
USUARIO = "postgres.yvakbrkllvavtnzywkor"

# 3. Defina a senha para o pessoal da oficina acessar o site:
SENHA_ACESSO = "sv2026" 

# --- MONTAGEM AUTOMÁTICA DO LINK (EVITA ERROS DE DIGITAÇÃO) ---
senha_codificada = urllib.parse.quote_plus(SENHA_BANCO)
DB_URL = f"postgresql://{USUARIO}:{senha_codificada}@aws-0-sa-east-1.pooler.supabase.com:6543/postgres?sslmode=require"

def criar_engine_sql():
    # pool_pre_ping garante que a conexão seja testada antes de cada uso
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

# --- FUNÇÕES DE DADOS ---
def listar_frotas():
    try:
        conn = conectar_banco()
        df = pd.read_sql("SELECT numero_frota FROM dim_frota ORDER BY numero_frota", conn)
        conn.close()
        return df['numero_frota'].tolist()
    except:
        return []

aba1, aba2, aba3 = st.tabs(["🛠️ Nova O.S.", "📈 Histórico", "⚙️ Configurações"])

# --- ABA 1: LANÇAMENTO ---
with aba1:
    st.subheader("📝 Registro de Manutenção")
    lista_frotas = listar_frotas()
    
    if not lista_frotas:
        st.warning("⚠️ Nenhuma frota cadastrada. Vá em 'Configurações' e importe o arquivo.")
    
    with st.form("form_os", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            frota_sel = st.selectbox("Nº da Frota", options=lista_frotas)
            mecanico = st.text_input("Mecânico")
        with c2:
            horimetro = st.number_input("Horímetro", step=0.1)
            tipo = st.selectbox("Tipo", ["OFICINA", "LUBRIFICAÇÃO", "PREVENTIVA", "TERCEIROS"])

        servico = st.text_area("Descrição do Serviço")
        
        if st.form_submit_button("✅ SALVAR NO SISTEMA"):
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
                cur.execute("""
                    INSERT INTO fato_os (frota_id, mecanico_resp, descricao_servico, horimetro_decimal, tipo_os)
                    VALUES (%s, %s, %s, %s, %s)
                """, (frota_sel, mecanico, servico, horimetro, tipo))
                conn.commit()
                conn.close()
                st.success("Ordem de Serviço salva com sucesso!")
                st.balloons()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

# --- ABA 2: HISTÓRICO ---
with aba2:
    if st.button("🔄 Atualizar Relatório"):
        try:
            conn = conectar_banco()
            df_hist = pd.read_sql("SELECT data_reg as Data, frota_id as Frota, mecanico_resp as Mecânico, tipo_os as Tipo, descricao_servico as Serviço FROM fato_os ORDER BY data_reg DESC", conn)
            st.dataframe(df_hist, use_container_width=True)
            conn.close()
        except:
            st.info("Ainda não há dados registrados.")

# --- ABA 3: CONFIGURAÇÕES ---
with aba3:
    st.subheader("📦 Importação de Frota")
    arquivo = st.file_uploader("Selecione o arquivo da Frota (CSV ou TXT)", type=['txt', 'csv'])
    
    if arquivo:
        try:
            df_import = pd.read_csv(arquivo, sep=None, engine='python', encoding='latin1')
            if len(df_import.columns) >= 4:
                df_import = df_import.iloc[:, :4]
                df_import.columns = ['numero_frota', 'tipo_bem', 'descricao', 'setor_padrao']
                st.write("✅ Arquivo lido com sucesso!")
                st.dataframe(df_import.head())

                if st.button("🚀 EXECUTAR CARGA PARA O SUPABASE"):
                    try:
                        engine = criar_engine_sql()
                        with engine.begin() as conn_engine:
                            conn_engine.execute(text("""
                                CREATE TABLE IF NOT EXISTS dim_frota (
                                    numero_frota TEXT PRIMARY KEY,
                                    tipo_bem TEXT,
                                    descricao TEXT,
                                    setor_padrao TEXT
                                )
                            """))
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