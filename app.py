import streamlit as st
import psycopg2
import pandas as pd
from sqlalchemy import create_engine, text
import os
import urllib.parse

# --- CONFIGURAÇÕES DE CONEXÃO (MODO POOLER OBRIGATÓRIO) ---

# 1. Coloque a SENHA do Banco de Dados que você redefiniu (apenas letras e números)
SENHA_BANCO = "VerginiaAgro2026"

# 2. Seu Usuário Completo (ID do seu projeto: yvakbrkllvavtnzywkor)
USUARIO = "postgres.yvakbrkllvavtnzywkor"

# 3. Senha para as pessoas acessarem o SEU SITE (Pode ser qualquer uma)
SENHA_ACESSO = "sv2026"

# --- MONTAGEM TÉCNICA DA CONEXÃO (PORTA 6543 + SSL) ---
# O urllib limpa a senha para não dar erro de leitura no link
senha_safe = urllib.parse.quote_plus(SENHA_BANCO)
DB_URL = f"postgresql://{USUARIO}:{senha_safe}@aws-0-sa-east-1.pooler.supabase.com:6543/postgres?sslmode=require"

def criar_engine_sql():
    return create_engine(DB_URL, pool_pre_ping=True)

def conectar_banco():
    return psycopg2.connect(DB_URL)

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Oficina SV", layout="wide", page_icon="🔧")

# --- SISTEMA DE LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔐 Acesso Restrito - Oficina SV")
    senha_digitada = st.text_input("Senha do Site:", type="password")
    if st.button("Entrar"):
        if senha_digitada == SENHA_ACESSO:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta!")
    st.stop()

# --- BARRA LATERAL (LOGO E LOCALIZAÇÃO) ---
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
caminho_logo = os.path.join(diretorio_atual, 'logo.png.png')
if os.path.exists(caminho_logo):
    st.sidebar.image(caminho_logo, use_container_width=True)
st.sidebar.markdown("---")
st.sidebar.write("**📍 Bataguassu - MS**")

st.title("🚜 Gestão de Frota e Manutenção - SV")

# --- FUNÇÃO PARA PEGAR FROTAS ---
def buscar_frotas():
    try:
        conn = conectar_banco()
        df = pd.read_sql("SELECT numero_frota FROM dim_frota ORDER BY numero_frota", conn)
        conn.close()
        return df['numero_frota'].tolist()
    except:
        return []

# --- ABAS DO SISTEMA ---
aba1, aba2, aba3 = st.tabs(["🛠️ Nova O.S.", "📈 Histórico", "⚙️ Configurações"])

with aba1:
    st.subheader("📝 Registro de Manutenção")
    lista_frotas = buscar_frotas()
    
    if not lista_frotas:
        st.warning("⚠️ Nenhuma frota encontrada. Vá em Configurações para importar.")
    
    with st.form("form_os", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            frota_sel = st.selectbox("Selecione a Frota", options=lista_frotas)
            mecanico = st.text_input("Mecânico Responsável")
        with c2:
            horimetro = st.number_input("Horímetro Atual", step=0.1)
            tipo = st.selectbox("Tipo de Serviço", ["OFICINA", "LUBRIFICAÇÃO", "PREVENTIVA", "CAMPO"])

        servico = st.text_area("Descrição Detalhada")
        
        if st.form_submit_button("✅ SALVAR MANUTENÇÃO"):
            try:
                conn = conectar_banco()
                cur = conn.cursor()
                # Cria a tabela de Fato se não existir
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
                st.success("Dados salvos com sucesso!")
                st.balloons()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

with aba2:
    st.subheader("📈 Relatório de Atividades")
    if st.button("🔄 Atualizar Tabela"):
        try:
            conn = conectar_banco()
            df_hist = pd.read_sql("SELECT data_reg as Data, frota_id as Frota, mecanico_resp as Mecânico, tipo_os as Tipo, descricao_servico as Serviço FROM fato_os ORDER BY data_reg DESC", conn)
            st.dataframe(df_hist, use_container_width=True)
            conn.close()
        except:
            st.info("Nenhum registro encontrado no banco.")

with aba3:
    st.subheader("⚙️ Configurações do Sistema")
    st.write("Importe o arquivo CSV com a lista de frotas (4 colunas: numero_frota, tipo_bem, descricao, setor_padrao)")
    
    arquivo = st.file_uploader("Upload de Frota", type=['csv', 'txt'])
    
    if arquivo:
        try:
            # Lê o arquivo tratando codificação comum em Excel/Bataguassu (latin1)
            df_import = pd.read_csv(arquivo, sep=None, engine='python', encoding='latin1')
            if len(df_import.columns) >= 4:
                df_import = df_import.iloc[:, :4]
                df_import.columns = ['numero_frota', 'tipo_bem', 'descricao', 'setor_padrao']
                st.write("Prévia dos dados:")
                st.dataframe(df_import.head())

                if st.button("🚀 EXECUTAR CARGA"):
                    try:
                        engine = criar_engine_sql()
                        with engine.begin() as conn_engine:
                            # Cria a tabela dim_frota se não existir
                            conn_engine.execute(text("""
                                CREATE TABLE IF NOT EXISTS dim_frota (
                                    numero_frota TEXT PRIMARY KEY,
                                    tipo_bem TEXT,
                                    descricao TEXT,
                                    setor_padrao TEXT
                                )
                            """))
                            # Limpa a frota antiga e sobe a nova
                            conn_engine.execute(text("TRUNCATE TABLE dim_frota CASCADE;"))
                            df_import.to_sql('dim_frota', conn_engine, if_exists='append', index=False)
                        st.success("Frota atualizada no Supabase!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Erro na conexão com o banco: {e}")
            else:
                st.error("O arquivo precisa de pelo menos 4 colunas.")
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {e}")