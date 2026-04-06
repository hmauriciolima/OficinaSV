import streamlit as st
import psycopg2
import pandas as pd
from sqlalchemy import create_engine, text
import os

# --- CONFIGURAÇÕES DE CONEXÃO (NUVEM SUPABASE - MODO POOLER) ---
# 1. Substitua [SUA-SENHA] pela senha do Banco de Dados. 
# O usuário PRECISA ser 'postgres.yvakbrkllvavtnzywkor' para o Pooler te encontrar.
DB_URL = "postgresql://postgres.yvakbrkllvavtnzywkor:[calecatusmay]@aws-0-sa-east-1.pooler.supabase.com:5432/postgres"

# 2. Senha para o pessoal da oficina acessar o site
SENHA_ACESSO = "sv2026" 

def criar_engine_sql():
    # Timeout de 10 segundos para estabilidade
    return create_engine(DB_URL, connect_args={"connect_timeout": 10})

def conectar_banco():
    return psycopg2.connect(DB_URL)

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Oficina SV", layout="wide", page_icon="🔧")

# --- ESTILO VISUAL ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- TELA DE LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔐 Acesso Restrito - Oficina SV")
    senha_digitada = st.text_input("Digite a senha para acessar o sistema:", type="password")
    if st.button("Entrar"):
        if senha_digitada == SENHA_ACESSO:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta!")
    st.stop()

# --- LOGOTIPO LATERAL ---
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
# Usando o nome do arquivo que apareceu no seu print do Codespaces
caminho_logo = os.path.join(diretorio_atual, 'logo.png.png')
if os.path.exists(caminho_logo):
    st.sidebar.image(caminho_logo, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.write("**📍 Bataguassu - MS**")
if st.sidebar.button("Sair/Logoff"):
    st.session_state["autenticado"] = False
    st.rerun()

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

# --- ABA 1: LANÇAMENTO DE O.S. ---
with aba1:
    st.subheader("📝 Registro de Manutenção")
    lista_frotas = listar_frotas()
    
    if not lista_frotas:
        st.warning("⚠️ Nenhuma frota cadastrada. Vá em 'Configurações' e importe o arquivo da frota.")
    
    with st.form("form_os", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            frota_sel = st.selectbox("Nº da Frota", options=lista_frotas)
            mecanico = st.text_input("Mecânico")
        with c2:
            horimetro = st.number_input("Horímetro", step=0.1)
            tipo = st.selectbox("Tipo", ["OFICINA", "LUBRIFICAÇÃO", "TERCEIROS", "PREVENTIVA"])
        with c3:
            nf_sap = st.text_input("NF-e / SAP")
            custo = st.number_input("Custo Peças", min_value=0.0, step=0.01)

        servico = st.text_area("Descrição do Serviço")
        pecas = st.text_input("Peças Aplicadas")
        
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
                        peca_aplicada TEXT,
                        horimetro_decimal NUMERIC,
                        tipo_os TEXT,
                        nf_sap TEXT,
                        custo_real NUMERIC
                    )
                """)
                cur.execute("""
                    INSERT INTO fato_os (frota_id, mecanico_resp, descricao_servico, peca_aplicada, horimetro_decimal, tipo_os, nf_sap, custo_real)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (frota_sel, mecanico, servico, pecas, horimetro, tipo, nf_sap, custo))
                conn.commit()
                cur.close()
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
            query = """
                SELECT f.data_reg as "Data", f.frota_id as "Frota", d.descricao as "Equipamento", 
                       f.mecanico_resp as "Mecânico", f.tipo_os as "Tipo", f.horimetro_decimal as "Horímetro",
                       f.descricao_servico as "Serviço", f.peca_aplicada as "Peças", f.custo_real as "Custo R$"
                FROM fato_os f
                LEFT JOIN dim_frota d ON f.frota_id = d.numero_frota
                ORDER BY f.data_reg DESC
            """
            df_hist = pd.read_sql(query, conn)
            st.dataframe(df_hist, use_container_width=True)
            conn.close()
        except:
            st.warning("Ainda não há dados registrados ou o banco está inacessível.")

# --- ABA 3: CONFIGURAÇÕES E CARGA ---
with aba3:
    st.subheader("📦 Importação de Frota")
    arquivo = st.file_uploader("Selecione o arquivo da Frota (TXT ou CSV)", type=['txt', 'csv'])
    
    if arquivo:
        try:
            df_import = pd.read_csv(arquivo, sep=None, engine='python', encoding='latin1')
            
            if len(df_import.columns) >= 4:
                df_import = df_import.iloc[:, :4]
                df_import.columns = ['numero_frota', 'tipo_bem', 'descricao', 'setor_padrao']
                df_import['numero_frota'] = df_import['numero_frota'].astype(str).str.strip()
                
                st.write("✅ Arquivo lido! Verifique a prévia:")
                st.dataframe(df_import.head(5))

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
                        st.error(f"Erro ao salvar no banco: {e}")
            else:
                st.error("O arquivo precisa ter pelo menos 4 colunas.")
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {e}")