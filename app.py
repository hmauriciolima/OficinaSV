import streamlit as st
import psycopg2
import pandas as pd
from sqlalchemy import create_engine, text
import os
import urllib.parse

# --- CONFIGURAÇÕES DE CONEXÃO ---

# 1. A SENHA DO BANCO (Aquela que você redefiniu no painel do Supabase - Apenas letras e números)
SENHA_BANCO = "VerginiaAgro2026"

# 2. O seu Usuário Completo (ID do projeto: yvakbrkllvavtnzywkor)
USUARIO = "postgres.yvakbrkllvavtnzywkor"

# 3. A SENHA PARA ABRIR O SITE (O que você digita no navegador, ex: sv2026)
SENHA_ACESSO = "sv2026"

# --- MONTAGEM DA CONEXÃO (POOLER NA PORTA 5432 + SSL) ---
# O quote_plus garante que se houver algum caractere chato na senha, ele seja lido corretamente.
senha_safe = urllib.parse.quote_plus(SENHA_BANCO)
DB_URL = f"postgresql://{USUARIO}:{senha_safe}@aws-0-sa-east-1.pooler.supabase.com:5432/postgres?sslmode=require"

def criar_engine_sql():
    return create_engine(DB_URL, pool_pre_ping=True)

def conectar_banco():
    return psycopg2.connect(DB_URL)

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Oficina SV", layout="wide", page_icon="🔧")

# --- LOGIN NO SITE ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔐 Acesso Restrito - Oficina SV")
    senha_digitada = st.text_input("Senha de Acesso:", type="password")
    if st.button("Entrar"):
        if senha_digitada == SENHA_ACESSO:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta!")
    st.stop()

# --- BARRA LATERAL ---
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
caminho_logo = os.path.join(diretorio_atual, 'logo.png.png')
if os.path.exists(caminho_logo):
    st.sidebar.image(caminho_logo, use_container_width=True)
st.sidebar.markdown("---")
st.sidebar.write("**📍 Bataguassu - MS**")

st.title("🚜 Sistema de Gestão de Frota - SV")

# --- FUNÇÃO PARA BUSCAR FROTAS CADASTRADAS ---
def buscar_frotas():
    try:
        conn = conectar_banco()
        df = pd.read_sql("SELECT numero_frota FROM dim_frota ORDER BY numero_frota", conn)
        conn.close()
        return df['numero_frota'].tolist()
    except:
        return []

# --- ORGANIZAÇÃO EM ABAS ---
aba1, aba2, aba3 = st.tabs(["🛠️ Nova O.S.", "📈 Histórico", "⚙️ Configurações"])

with aba1:
    st.subheader("📝 Registrar Manutenção")
    lista_frotas = buscar_frotas()
    
    if not lista_frotas:
        st.warning("⚠️ Nenhuma frota cadastrada. Vá em 'Configurações' para importar a lista.")
    
    with st.form("form_os", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            frota_sel = st.selectbox("Frota", options=lista_frotas)
            mecanico = st.text_input("Mecânico")
        with c2:
            horimetro = st.number_input("Horímetro", step=0.1)
            tipo = st.selectbox("Tipo", ["OFICINA", "PREVENTIVA", "LUBRIFICAÇÃO", "CAMPO"])

        servico = st.text_area("Descrição do Serviço")
        
        if st.form_submit_button("✅ SALVAR"):
            try:
                conn = conectar_banco()
                cur = conn.cursor()
                # Cria a tabela de fatos se ela não existir
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
                st.error(f"Erro ao salvar dados: {e}")

with aba2:
    st.subheader("📈 Histórico de Manutenções")
    if st.button("🔄 Atualizar Dados"):
        try:
            conn = conectar_banco()
            df_hist = pd.read_sql("SELECT data_reg as Data, frota_id as Frota, mecanico_resp as Mecânico, tipo_os as Tipo, descricao_servico as Serviço FROM fato_os ORDER BY data_reg DESC", conn)
            st.dataframe(df_hist, use_container_width=True)
            conn.close()
        except:
            st.info("Ainda não existem registros no banco de dados.")

with aba3:
    st.subheader("⚙️ Importação de Frota Master")
    st.write("Selecione o arquivo CSV/TXT com as colunas: numero_frota, tipo_bem, descricao, setor_padrao.")
    
    arquivo = st.file_uploader("Upload do arquivo de frota", type=['csv', 'txt'])
    
    if arquivo:
        try:
            df_import = pd.read_csv(arquivo, sep=None, engine='python', encoding='latin1')
            if len(df_import.columns) >= 4:
                df_import = df_import.iloc[:, :4]
                df_import.columns = ['numero_frota', 'tipo_bem', 'descricao', 'setor_padrao']
                st.write("Prévia da Importação:")
                st.dataframe(df_import.head())

                if st.button("🚀 EXECUTAR CARGA"):
                    try:
                        engine = criar_engine_sql()
                        with engine.begin() as conn_engine:
                            # Cria a tabela de dimensões se ela não existir
                            conn_engine.execute(text("""
                                CREATE TABLE IF NOT EXISTS dim_frota (
                                    numero_frota TEXT PRIMARY KEY,
                                    tipo_bem TEXT,
                                    descricao TEXT,
                                    setor_padrao TEXT
                                )
                            """))
                            # Limpa os dados antigos para evitar duplicidade
                            conn_engine.execute(text("TRUNCATE TABLE dim_frota CASCADE;"))
                            df_import.to_sql('dim_frota', conn_engine, if_exists='append', index=False)
                        st.success("Frota atualizada com sucesso no Supabase!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Erro na carga do banco: {e}")
            else:
                st.error("O arquivo precisa de pelo menos 4 colunas.")
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")