import streamlit as st
import psycopg2
import pandas as pd
from sqlalchemy import create_engine, text
from PIL import Image
import os

# --- CONFIGURAÇÕES DE CONEXÃO (NUVEM SUPABASE) ---
# Substitua [YOUR-PASSWORD] pela sua senha do Supabase
DB_URL = "postgresql://postgres:[YOUR-PASSWORD]@db.yvakbrkllvavtnzywkor.supabase.co:5432/postgres"
SENHA_ACESSO = "calecatusmay" # <--- Defina a senha para abrir o sistema

def criar_engine_sql():
    return create_engine(DB_URL)

def conectar_banco():
    return psycopg2.connect(DB_URL)

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Oficina SV", layout="wide", page_icon="🔧")

# --- TELA DE LOGIN SIMPLES ---
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

# --- LAYOUT E ESTILO ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; font-weight: bold; }
    [data-testid="stSidebar"] { text-align: center; background-color: #f0f2f6; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGO (SISTEMA HÍBRIDO) ---
if 'logo_img' not in st.session_state:
    st.session_state['logo_img'] = None

diretorio_atual = os.path.dirname(os.path.abspath(__file__))
for f in ['logo.jpg', 'logo.png', 'logo.jpeg']:
    caminho = os.path.join(diretorio_atual, f)
    if os.path.exists(caminho):
        st.session_state['logo_img'] = caminho
        break

if st.session_state['logo_img']:
    st.sidebar.image(st.session_state['logo_img'], use_container_width=True)
else:
    st.sidebar.header("🏢 Oficina SV")

st.sidebar.markdown("---")
st.sidebar.write("**📍 Bataguassu - MS**")
if st.sidebar.button("Sair/Logoff"):
    st.session_state["autenticado"] = False
    st.rerun()

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

# --- ABA 1: LANÇAMENTO ---
with aba1:
    st.subheader("📝 Registro de Manutenção")
    lista_frotas = listar_frotas()
    
    if not lista_frotas:
        st.info("💡 Se as tabelas ainda não existirem no Supabase, vá em Configurações e importe a frota.")
    
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
                # Criar tabela fato se não existir no Supabase
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
            df = pd.read_sql(query, conn)
            st.dataframe(df, use_container_width=True)
            conn.close()
        except:
            st.warning("Ainda não há dados registrados ou as tabelas estão sendo criadas.")

# --- ABA 3: CONFIGURAÇÕES ---
with aba3:
    st.subheader("🖼️ Logotipo")
    logo_file = st.file_uploader("Suba o logo se ele não aparecer", type=['jpg', 'png', 'jpeg'])
    if logo_file:
        st.session_state['logo_img'] = logo_file
        st.rerun()

    st.markdown("---")
    st.subheader("📦 Importação de Frota")
    arquivo = st.file_uploader("Arquivo da Frota (TXT/CSV)", type=['txt', 'csv'])
    
    if arquivo:
        conteudo = arquivo.getvalue().decode("utf-8")
        sep_identificado = ';' if ';' in conteudo else r'\s{2,}'
        arquivo.seek(0)
        df_import = pd.read_csv(arquivo, sep=sep_identificado, engine='python', 
                                names=['numero_frota', 'tipo_bem', 'descricao', 'setor_padrao'], skiprows=1)
        df_import['numero_frota'] = df_import['numero_frota'].astype(str).str.replace('.', '', regex=False).str.split(',').str[0]
        df_import = df_import.drop_duplicates(subset=['numero_frota'])
        
        if st.button("🚀 EXECUTAR CARGA PARA O SUPABASE"):
            try:
                engine = criar_engine_sql()
                with engine.begin() as conn:
                    # Cria a tabela dim_frota no Supabase se não existir
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS dim_frota (
                            numero_frota TEXT PRIMARY KEY,
                            tipo_bem TEXT,
                            descricao TEXT,
                            setor_padrao TEXT
                        )
                    """))
                    conn.execute(text("TRUNCATE TABLE dim_frota CASCADE;"))
                    df_import.to_sql('dim_frota', conn, if_exists='append', index=False)
                st.success("Frota carregada na nuvem!")
            except Exception as e:
                st.error(f"Erro: {e}")