import streamlit as st
import pandas as pd
import numpy as np
import os
import hashlib
from datetime import datetime, date
from supabase import create_client, Client  # BANCO NA NUVEM (Supabase)


# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Sistema Nutricional",
    page_icon="🥗",
    layout="wide"
)

st.markdown("""
<style>
    .login-card {
        background: #f8f9fa;
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }
    .titulo-verde {
        color: #2e7d32;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# SEÇÃO 1 — BANCO DE DADOS (SUPABASE)
# ==============================================================================

# Conexão com o Supabase via secrets do Streamlit
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)


# ---- Funções auxiliares de segurança ----

def hash_senha(senha: str) -> str:
    """Retorna o hash SHA-256 da senha em hexadecimal."""
    return hashlib.sha256(senha.encode('utf-8')).hexdigest()


# ---- Funções de usuário ----

def cadastrar_usuario(username: str, email: str, senha: str):
    """
    Insere um novo usuário no Supabase.
    Retorna (True, mensagem) em caso de sucesso ou (False, erro) em falha.
    """
    try:
        dados = {
            "username": username.strip(),
            "email": email.strip().lower(),
            "senha_hash": hash_senha(senha),
            "data_cadastro": datetime.now().isoformat()
        }
        supabase.table("usuarios").insert(dados).execute()
        return True, "✅ Cadastro realizado com sucesso! Faça login para continuar."
    except Exception as e:
        if "already exists" in str(e) or "duplicate" in str(e).lower():
            return False, "❌ Nome de usuário ou E-mail já cadastrado!"
        return False, f"❌ Erro inesperado: {e}"


def fazer_login(username: str, senha: str):
    """
    Verifica credenciais no Supabase.
    Retorna (True, dict_usuario) ou (False, None).
    """
    try:
        query = supabase.table("usuarios") \
            .select("id, username, email, senha_hash") \
            .eq("username", username.strip()) \
            .execute()

        if query.data:
            user_data = query.data[0]  # query.data é uma lista
            if user_data['senha_hash'] == hash_senha(senha):
                return True, {
                    'id':       user_data['id'],
                    'username': user_data['username'],
                    'email':    user_data['email']
                }
        return False, None
    except Exception:
        return False, None


# ---- Funções de refeição ----

def salvar_refeicao(user_id: int, data_refeicao: str, nome_refeicao: str,
                    lista_alimentos: list, totais: dict):
    """
    Persiste uma refeição completa (cabeçalho + itens) no Supabase.
    Retorna (True, mensagem) ou (False, erro).
    """
    try:
        # 1. Insere o cabeçalho da refeição
        cabecalho = {
            "user_id":           user_id,
            "data":              str(data_refeicao),
            "nome_refeicao":     nome_refeicao,
            "total_kcal":        totais['kcal'],
            "total_proteina":    totais['proteina'],
            "total_carboidrato": totais['carboidrato'],
            "total_gordura":     totais['gordura'],
            "total_fibra":       totais['fibra'],
            "data_registro":     datetime.now().isoformat()
        }
        res_ref = supabase.table("refeicoes").insert(cabecalho).execute()
        refeicao_id = res_ref.data[0]['id']  # res_ref.data é uma lista

        # 2. Insere cada alimento/bebida da lista
        for item in lista_alimentos:
            supabase.table("itens_refeicao").insert({
                "refeicao_id": refeicao_id,
                "alimento":    item['alimento'],
                "quantidade":  item['quantidade'],
                "unidade":     item['unidade'],
                "kcal":        item['kcal'],
                "proteina":    item['proteina'],
                "carboidrato": item['carboidrato'],
                "gordura":     item['gordura'],
                "fibra":       item['fibra'],
                "categoria":   item['categoria']
            }).execute()

        return True, "✅ Refeição salva no histórico com sucesso!"
    except Exception as e:
        return False, f"❌ Erro ao salvar: {e}"


def buscar_historico(user_id: int, data_inicio=None, data_fim=None):
    """
    Retorna lista de refeições no mesmo formato de tupla do SQLite original:
    (id, data, nome_refeicao, total_kcal, total_proteina,
     total_carboidrato, total_gordura, total_fibra, data_registro)
    """
    try:
        query = supabase.table("refeicoes") \
            .select("id, data, nome_refeicao, total_kcal, total_proteina, "
                    "total_carboidrato, total_gordura, total_fibra, data_registro") \
            .eq("user_id", user_id)

        if data_inicio:
            query = query.gte("data", str(data_inicio))
        if data_fim:
            query = query.lte("data", str(data_fim))

        res = query.order("data", desc=True).execute()

        # Converte dicts → tuplas para manter compatibilidade com aba_historico
        return [
            (r['id'], r['data'], r['nome_refeicao'],
             r['total_kcal'], r['total_proteina'],
             r['total_carboidrato'], r['total_gordura'],
             r['total_fibra'], r['data_registro'])
            for r in res.data
        ]
    except Exception:
        return []


def buscar_itens_refeicao(refeicao_id: int):
    """
    Retorna os itens de uma refeição no mesmo formato de tupla do SQLite original:
    (alimento, quantidade, unidade, kcal, proteina,
     carboidrato, gordura, fibra, categoria)
    """
    try:
        res = supabase.table("itens_refeicao") \
            .select("alimento, quantidade, unidade, kcal, proteina, "
                    "carboidrato, gordura, fibra, categoria") \
            .eq("refeicao_id", refeicao_id) \
            .execute()

        # Converte dicts → tuplas para manter compatibilidade com aba_historico
        return [
            (r['alimento'], r['quantidade'], r['unidade'],
             r['kcal'], r['proteina'], r['carboidrato'],
             r['gordura'], r['fibra'], r['categoria'])
            for r in res.data
        ]
    except Exception:
        return []


def deletar_refeicao(refeicao_id: int) -> bool:
    """Remove uma refeição e todos os seus itens do Supabase."""
    try:
        supabase.table("itens_refeicao").delete().eq("refeicao_id", refeicao_id).execute()
        supabase.table("refeicoes").delete().eq("id", refeicao_id).execute()
        return True
    except Exception:
        return False


# ==============================================================================
# SEÇÃO 2 — TELA DE LOGIN / CADASTRO
# ==============================================================================

def tela_login():
    """
    Página de autenticação com duas abas: Login e Cadastro.
    """
    col_c, col_m, col_d = st.columns([1, 2, 1])
    with col_m:
        st.markdown("## 🥗 Sistema Nutricional")
        st.markdown("##### Seu assistente de alimentação saudável")
        st.markdown("---")

        aba_login, aba_cadastro = st.tabs(["🔑 Entrar", "📝 Criar Conta"])

        # ===== ABA DE LOGIN =====
        with aba_login:
            st.markdown("### Acesse sua conta")

            username_login = st.text_input(
                "Nome de usuário", key="login_user",
                placeholder="seu_usuario"
            )
            senha_login = st.text_input(
                "Senha", type="password", key="login_pass",
                placeholder="••••••••"
            )

            col_btn, _ = st.columns([1, 1])
            with col_btn:
                if st.button("🚀 Entrar", use_container_width=True, type="primary"):
                    if not username_login or not senha_login:
                        st.warning("⚠️ Preencha usuário e senha.")
                    else:
                        ok, usuario = fazer_login(username_login, senha_login)
                        if ok:
                            st.session_state.usuario_logado = usuario
                            st.success(f"Bem-vindo(a), {usuario['username']}! 👋")
                            st.rerun()
                        else:
                            st.error("❌ Usuário ou senha incorretos.")
                            st.error("❌ Verifique se você já criou a conta na aba: Criar Conta.")

        # ===== ABA DE CADASTRO =====
        with aba_cadastro:
            st.markdown("### Crie sua conta gratuita")

            novo_username = st.text_input(
                "Nome de usuário", key="cad_user",
                placeholder="escolha um nome único"
            )
            novo_email = st.text_input(
                "E-mail", key="cad_email",
                placeholder="seu@email.com"
            )
            nova_senha = st.text_input(
                "Senha (mín. 6 caracteres)", type="password",
                key="cad_pass", placeholder="••••••••"
            )
            confirma_senha = st.text_input(
                "Confirme a senha", type="password",
                key="cad_pass2", placeholder="••••••••"
            )

            if st.button("✅ Criar Conta", use_container_width=True, type="primary"):
                if not all([novo_username, novo_email, nova_senha, confirma_senha]):
                    st.warning("⚠️ Preencha todos os campos.")
                elif len(nova_senha) < 6:
                    st.error("❌ A senha deve ter pelo menos 6 caracteres.")
                elif nova_senha != confirma_senha:
                    st.error("❌ As senhas não coincidem.")
                elif "@" not in novo_email:
                    st.error("❌ E-mail inválido.")
                else:
                    ok, msg = cadastrar_usuario(novo_username, novo_email, nova_senha)
                    if ok:
                        st.success(msg)
                        st.info("Agora acesse a aba **Entrar** para fazer login.")
                    else:
                        st.error(msg)


# ==============================================================================
# SEÇÃO 3 — INICIALIZAÇÃO DO SESSION STATE
# ==============================================================================

def init_session_state():
    """Inicializa variáveis da sessão (executada uma vez por sessão)."""
    defaults = {
        'usuario_logado':        None,
        'tdee_usuario':          0,
        'total_kcal':            0.0,
        'total_proteina':        0.0,
        'total_carboidrato':     0.0,
        'total_gordura':         0.0,
        'total_fibra':           0.0,
        'lista_alimentos':       [],
        'data_refeicao':         date.today(),
        'nome_refeicao':         'Almoço',
    }
    for chave, valor in defaults.items():
        if chave not in st.session_state:
            st.session_state[chave] = valor


# ==============================================================================
# SEÇÃO 4 — CARREGAMENTO DOS DADOS NUTRICIONAIS (CSV + Excel)
# ==============================================================================

@st.cache_data
def carregar_dados():
    dataframes = []

# ----- COMIDAS (CSV) -----
    try :
        if os.path.exists("Tabela_Alimentos_Original.csv"):
            # Lemos o arquivo deixando o pandas detectar o separador sozinho
            # O 'on_bad_lines' evita que o erro da linha 544 trave tudo
            df_comidas = pd.read_csv(
                "Tabela_Alimentos_Original.csv", 
                sep=None, 
                engine='python', 
                encoding="latin1",
                on_bad_lines='skip' 
            )
            
            # Remove espaços extras dos nomes das colunas
            df_comidas.columns = df_comidas.columns.str.strip()

            # Ajuste para caso a primeira coluna se chame '#' ou algo similar
            if '#' in df_comidas.columns:
                df_comidas = df_comidas.rename(columns={df_comidas.columns[1]: 'Alimento'})
            elif 'Alimento' not in df_comidas.columns:
                # Se não achar 'Alimento', assume que a primeira coluna de texto é o nome
                df_comidas = df_comidas.rename(columns={df_comidas.columns[0]: 'Alimento'})

            df_comidas['Categoria'] = 'Comida'
            df_comidas['Unidade'] = 'g'
            dataframes.append(df_comidas)
            st.sidebar.success(f"✅ Comidas carregadas: {len(df_comidas)} itens")
    except Exception as e:  # <--- ESTA LINHA PRECISA EXISTIR E ESTAR ALINHADA COM O TRY
        st.sidebar.error(f"Erro ao carregar comidas: {e}")

    # ----- BEBIDAS (Excel) ----- (Mantido conforme seu original)
    try:
        if os.path.exists("tabela_bebidas.xlsx"):
            df_bebidas = pd.read_excel("tabela_bebidas.xlsx")
            df_bebidas.columns = df_bebidas.columns.str.strip()

            # Localiza a coluna de nome (ajustado para ser mais flexível)
            for col in df_bebidas.columns:
                if 'bebida' in col.lower() or 'alimento' in col.lower():
                    df_bebidas = df_bebidas.rename(columns={col: 'Alimento'})
                    break

            mapa_colunas = {
                'Calorias (kcal)':  ['kcal', 'caloria', 'energia', 'cal'],
                'Proteínas (g)':    ['proteína', 'proteina', 'prot', 'protein'],
                'Carboidratos (g)': ['carboidrato', 'carb', 'carbo'],
                'Fibras (g)':       ['fibra', 'fibras', 'fiber'],
                'Gorduras (g)':     ['gordura', 'gord', 'lipídio', 'lipideo'],
            }
            
            for coluna_padrao, aliases in mapa_colunas.items():
                for col in df_bebidas.columns:
                    if any(alias in col.lower() for alias in aliases):
                        df_bebidas = df_bebidas.rename(columns={col: coluna_padrao})
                        break

            df_bebidas['Alimento']  = df_bebidas['Alimento'].astype(str).str.strip()
            df_bebidas['Categoria'] = 'Bebida'
            df_bebidas['Unidade']   = 'ml'

            dataframes.append(df_bebidas)
            st.sidebar.success(f"✅ Bebidas carregadas: {len(df_bebidas)} itens")
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar bebidas: {e}")

    # ----- COMBINA E LIMPA TUDO -----
    if dataframes:
        df = pd.concat(dataframes, ignore_index=True)
        
        # Garante que colunas numéricas sejam tratadas corretamente
        colunas_nutri = ['Calorias (kcal)', 'Proteínas (g)', 'Carboidratos (g)', 'Fibras (g)', 'Gorduras (g)']
        
        for col in colunas_nutri:
            if col in df.columns:
                # Converte para string, troca vírgula por ponto e transforma em número
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(',', '.').str.strip(), 
                    errors='coerce'
                ).fillna(0) # Se não conseguir converter, vira 0
            else:
                df[col] = 0.0
                
        return df
    else:
        st.error("❌ Nenhum arquivo de dados carregado!")
        return pd.DataFrame()
# ==============================================================================
# SEÇÃO 5 — ABA 1: SOBRE NUTRIÇÃO
# ==============================================================================

def aba_sobre_nutricao():
    """Primeira aba com informações educativas sobre nutrição."""

    st.title("🥗 Guia Alimentar para uma Vida Saudável")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        ### 🌱 A Base: Qualidade Segundo o Guia Alimentar

        Antes de calcular números, o governo brasileiro destaca que a saúde vem da escolha dos alimentos.
        """)

        categorias = pd.DataFrame({
            "Categoria": ["**In Natura**", "**Processados**", "**Ultraprocessados**"],
            "Recomendação": ["Base da dieta", "Limitar", "Evitar"],
            "Exemplos": [
                "Arroz, feijão, carnes, ovos, frutas, tubérculos",
                "Queijos, pães artesanais, conservas simples",
                "Refrigerantes, biscoitos recheados, macarrão instantâneo"
            ]
        })
        st.table(categorias)

        st.markdown("---")
        st.markdown("""
        ### ⚠️ 1. Desinformação Nutricional

        As redes sociais frequentemente propagam dietas milagrosas e o medo injustificado de
        alimentos (como glúten e carboidratos). Essas práticas podem levar a:

        - **Deficiências nutricionais** e queda de imunidade
        - **Transtornos alimentares** devido a restrições severas
        - **Perda de fibras** e nutrientes essenciais
        """)

        st.markdown("---")
        st.markdown("""
        ### 🔥 2. Entendendo o Gasto Energético

        **TMB (Taxa Metabólica Basal):** Gasto energético mínimo para manter funções vitais em
        repouso. Representa cerca de 60-75% do gasto diário.

        **TMT (Taxa Metabólica Total):** Soma de toda a energia gasta em 24 horas (TMB + atividades
        físicas + digestão). O fator de atividade varia entre 1,2 e 1,9.

        **Déficit Calórico:** Estado em que o corpo consome menos calorias do que gasta,
        forçando o organismo a usar reservas de gordura como energia — princípio fundamental
        do emagrecimento saudável. Recomenda-se um déficit gradual de **200 a 500 kcal/dia**.
        """)

        st.markdown("---")

        col_tmb, col_tmt = st.columns(2)
        with col_tmb:
            st.info("""
            **📊 TMB — Taxa Metabólica Basal**

            • Gasto em repouso completo
            • 60–75 % do gasto diário
            • Varia com idade, sexo, peso e altura
            """)
        with col_tmt:
            st.info("""
            **📈 TMT — Taxa Metabólica Total**

            • Gasto total nas 24 horas
            • TMB + atividades físicas
            • Fator de atividade: 1,2 a 1,9
            """)

        st.markdown("---")
        st.markdown("""
        ### 3. Entendendo o IMC (Índice de Massa Corporal)

        O IMC (Índice de Massa Corporal) é uma medida internacional, baseada na fórmula
        (Peso/altura²), que avalia se uma pessoa está em seu peso ideal, sobrepeso ou obesidade.
        É um indicador rápido de saúde nutricional, útil para rastreamento, mas não distingue massa magra de gordura.
        """)
        st.markdown("---")

        st.markdown("### ⚖️ 4. Como as Calorias Agem no Corpo")
        st.markdown("""
        O corpo funciona como um sistema de energia.

        - Calorias são o combustível
        - O corpo usa para viver, se mover e digerir

        Diferença importante:
        - Açúcar → energia rápida, baixa saciedade
        - Proteína → digestão mais lenta, maior saciedade

        Isso acontece por causa do **efeito térmico dos alimentos** (gasto para digerir).
        """)

        st.markdown("---")
        st.markdown("### 🥦 5. Como a Origem dos Alimentos Influencia o Corpo")
        st.markdown("""
        A qualidade dos alimentos impacta diretamente sua saúde.

        - **Alimentos naturais:** ricos em fibras, vitaminas e minerais
        Consequências:
        - Melhora ou piora da digestão
        - Controle de fome

        - **Ultraprocessados:** pobres em nutrientes e ricos em aditivos
        Consequências:
        - Risco de doenças (ex: diabetes, anemia)
        - Queda de cabelo
        - Além de enfraquecer o sistema imunológico
        """)

    with col2:
        st.markdown("""
        ### 🎯 Recomendação Diária (por kg de peso)

        **Proteína:** 1,5 g/kg
        **Gordura:** 1,0 g/kg
        **Carboidrato:** 5,0 g/kg

        > **Exemplo:** Pessoa com 80 kg precisa de ~120 g de proteína por dia
        """)
        st.markdown("---")
        st.markdown("""
        ### 🍽️ Como Comer

        - Comer em horários regulares
        - Preferir comida caseira
        - Mastigar bem os alimentos
        - Beber água ao longo do dia
        """)
        st.markdown("---")
        st.header("📌 Resumo prático dos conceitos chave.")
        st.info("""
        - 1 Grama de Proteína = 4 kcal
        - 1 Grama de Carboidrato = 4 kcal/g
        - 1 Grama de Gordura = 9 kcal/g

        Regra básica:
        - Comer mais calorias do que gasta → ganho de peso
        - Comer menos calorias do que gasta → perda de peso
        - Comer calorias igual do que gasta → mantém o peso
        """)
        st.markdown("---")
        st.warning("""
        **💡 Dica Importante:**

        Desconfie de dietas da moda. Nutrição saudável é baseada em equilíbrio e evidências
        científicas. Para emagrecimento saudável, faça um déficit calórico moderado de
        200–500 kcal abaixo da TMT! E é recomendado fazer atividades físicas.
        """)
        st.markdown("---")
        st.markdown("""
        ### 🔗 Fontes Confiáveis

        - [Ministério da Saúde](https://www.gov.br/saude)
        - [Guia Alimentar da População Brasileira](https://www.gov.br/saude)
        - [CFN — Conselho Federal de Nutrição](https://www.cfn.org.br)
        """)
        st.markdown("""
        ### Como se Proteger

        - **Verifique a fonte:** Priorize informações de nutricionistas registrados e órgãos oficiais.
        - **Desconfie de promessas rápidas:** Não existem milagres alimentares sem evidência científica.
        - **Déficit calórico comprovado:** Para emagrecimento saudável, é necessário fazer déficit calórico.
        """)


# ==============================================================================
# SEÇÃO 6 — ABA 2: CALCULADORA TMB
# ==============================================================================

def aba_calculadora_tmb():
    """Segunda aba: calcula TMB e TDEE e salva no session_state."""

    st.title("⚖️ Calculadora de Gasto Diário")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📝 Dados Pessoais")

        peso   = st.number_input("Peso (kg)",   min_value=20.0,  max_value=300.0, value=70.0,  step=0.1)
        altura = st.number_input("Altura (cm)", min_value=100.0, max_value=250.0, value=170.0, step=0.1)
        idade  = st.number_input("Idade",       min_value=1,     max_value=100,   value=30,    step=1)
        sexo   = st.selectbox("Sexo", ["Homem", "Mulher"])

        atividade = st.selectbox(
            "Nível de Atividade",
            ["Sedentário(pouco ou nenhum exercício)",
             "Levemente ativo(exercício leve 1 a 3 dias/semana)",
             "Moderado(exercício moderado 3 a 5 dias/semana)",
             "Muito ativo(exercício pesado 5 a 6 dias/semana)",
             "Extremamente ativo (exercício muito pesado, 2 exercícios por dia, atleta, profissional)"]
        )

        fatores = {
            "Sedentário(pouco ou nenhum exercício)"                                                   : 1.200,
            "Levemente ativo(exercício leve 1 a 3 dias/semana)"                                      : 1.375,
            "Moderado(exercício moderado 3 a 5 dias/semana)"                                         : 1.550,
            "Muito ativo(exercício pesado 5 a 6 dias/semana)"                                        : 1.725,
            "Extremamente ativo (exercício muito pesado, 2 exercícios por dia, atleta, profissional)": 1.900,
        }

        if st.button("Calcular Gasto Diário", type="primary"):
            # Fórmula de Mifflin-St Jeor
            if sexo == "Homem":
                tmb = (10 * peso) + (6.25 * altura) - (5 * idade) + 5
            else:
                tmb = (10 * peso) + (6.25 * altura) - (5 * idade) - 161

            tdee = tmb * fatores[atividade]
            st.session_state.tdee_usuario = tdee

            with col2:
                st.subheader("📊 Resultados")

                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Taxa Metabólica Basal (TMB)", f"{tmb:.0f} kcal")
                with col_b:
                    st.metric("Gasto Total Diário (TDEE/TMT)", f"{tdee:.0f} kcal")

                st.subheader("🥩 Macronutrientes Recomendados")
                st.info(f"""
                - **Proteína:**     {peso * 1.5:.0f} g/dia
                - **Gordura:**      {peso * 1.0:.0f} g/dia
                - **Carboidrato:**  {peso * 4.0:.0f} g/dia
                """)

                st.success(f"""
                **🎯 Para emagrecimento saudável:**
                Consuma entre **{tdee - 500:.0f}** e **{tdee - 200:.0f}** kcal/dia
                (déficit de 200–500 kcal)
                """)

    if st.session_state.tdee_usuario > 0 and 'col2' not in locals():
        with col2:
            st.subheader("📊 Último Cálculo")
            st.metric("Gasto Total Diário", f"{st.session_state.tdee_usuario:.0f} kcal")


# ==============================================================================
# SEÇÃO 7 — ABA 3: CALCULADORA DE REFEIÇÃO
# ==============================================================================

def aba_buscador_alimentos():
    """
    Terceira aba: busca comidas/bebidas, monta a refeição e permite salvar
    no histórico com data e nome personalizados.
    """
    st.title("🔍 Calculadora de Refeição")
    st.markdown("""Média de medidas

    - Uma colher de sopa cheia de arroz pesa em média 20 a 25 Gramas

    - 1 Concha de feijão Média/Cheia: Aproximadamente 100 a 140 Gramas

    - 1 Concha de feijão Média Rasa: Cerca de 80 a 90 Gramas

    - 1 Concha de feijão Pequena: Cerca de 50 a 70 Gramas
    """)

    df = carregar_dados()
    if df.empty:
        st.error("❌ Nenhuma base de dados carregada!")
        return

    st.sidebar.subheader("📊 Base de Dados")
    st.sidebar.write(f"Total: **{len(df)}** itens")
    st.sidebar.write(f"Comidas: **{len(df[df['Categoria']=='Comida'])}**")
    st.sidebar.write(f"Bebidas: **{len(df[df['Categoria']=='Bebida'])}**")

    # ---- Identificação da Refeição ----
    st.markdown("### 📅 Identificação da Refeição")
    col_data, col_nome, col_limpar = st.columns([1, 2, 1])

    with col_data:
        data_escolhida = st.date_input(
            "Data da refeição:",
            value=st.session_state.data_refeicao,
            format="DD/MM/YYYY",
            key="seletor_data"
        )
        st.session_state.data_refeicao = data_escolhida

    with col_nome:
        nome_refeicao = st.selectbox(
            "Tipo de refeição:",
            ["Café da manhã", "Lanche da manhã", "Almoço",
             "Lanche da tarde", "Jantar", "Ceia", "Outro"],
            index=2,
            key="sel_nome_refeicao"
        )
        st.session_state.nome_refeicao = nome_refeicao

    with col_limpar:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Limpar Refeição", use_container_width=True):
            st.session_state.lista_alimentos   = []
            st.session_state.total_kcal        = 0.0
            st.session_state.total_proteina    = 0.0
            st.session_state.total_carboidrato = 0.0
            st.session_state.total_gordura     = 0.0
            st.session_state.total_fibra       = 0.0
            st.rerun()

    st.divider()

    col_esquerda, col_direita = st.columns([1, 1])

    # ===== COLUNA ESQUERDA: BUSCA =====
    with col_esquerda:
        tab_comida, tab_bebida = st.tabs(["🍛 COMIDAS", "🥤 BEBIDAS"])

        # ---------- ABA COMIDAS ----------
        with tab_comida:
            st.subheader("🍛 Buscar Comida")
            df_comidas = df[df['Categoria'] == 'Comida']

            busca_comida = st.text_input(
                "Nome da comida:",
                placeholder="Ex: arroz, frango, feijão...",
                key="busca_comida"
            )

            if busca_comida.strip():
                filtrados = df_comidas[
                    df_comidas['Alimento'].str.lower().str.contains(
                        busca_comida.strip().lower(), na=False
                    )
                ]
                st.caption(f"🔍 {len(filtrados)} resultado(s) encontrado(s)")
            else:
                filtrados = df_comidas
                st.caption(f"📋 {len(df_comidas)} comidas disponíveis")

            if not filtrados.empty:
                alimento_sel = st.selectbox(
                    "Selecione:", filtrados['Alimento'].tolist(), key="select_comida"
                )
                info = df[df['Alimento'] == alimento_sel].iloc[0]

                qtd = st.number_input(
                    "Quantidade (g):", min_value=1, max_value=2000,
                    value=100, step=10, key="qtd_comida"
                )

                kcal  = info['Calorias (kcal)']  * qtd
                prot  = info['Proteínas (g)']    * qtd
                carb  = info['Carboidratos (g)'] * qtd
                gord  = info['Gorduras (g)']     * qtd
                fibra = info['Fibras (g)']       * qtd

                st.subheader("📊 Valores Nutricionais")
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("kcal",  f"{kcal:.0f}")
                c2.metric("Prot.", f"{prot:.1f}g")
                c3.metric("Carb.", f"{carb:.1f}g")
                c4.metric("Gord.", f"{gord:.1f}g")
                c5.metric("Fibra", f"{fibra:.1f}g")

                if st.button("➕ Adicionar comida", use_container_width=True, key="btn_comida"):
                    st.session_state.lista_alimentos.append({
                        'alimento': alimento_sel, 'quantidade': qtd, 'unidade': 'g',
                        'kcal': kcal, 'proteina': prot, 'carboidrato': carb,
                        'gordura': gord, 'fibra': fibra, 'categoria': 'Comida'
                    })
                    st.session_state.total_kcal        += kcal
                    st.session_state.total_proteina    += prot
                    st.session_state.total_carboidrato += carb
                    st.session_state.total_gordura     += gord
                    st.session_state.total_fibra       += fibra
                    st.success(f"✅ {alimento_sel} adicionado!")
                    st.rerun()

        # ---------- ABA BEBIDAS ----------
        with tab_bebida:
            st.subheader("🥤 Buscar Bebida")
            df_bebidas = df[df['Categoria'] == 'Bebida']

            busca_bebida = st.text_input(
                "Nome da bebida:",
                placeholder="Ex: água, suco, refrigerante...",
                key="busca_bebida"
            )

            if busca_bebida.strip():
                filtrados_b = df_bebidas[
                    df_bebidas['Alimento'].str.lower().str.contains(
                        busca_bebida.strip().lower(), na=False
                    )
                ]
                st.caption(f"🔍 {len(filtrados_b)} resultado(s) encontrado(s)")
            else:
                filtrados_b = df_bebidas
                st.caption(f"📋 {len(df_bebidas)} bebidas disponíveis")

            if not filtrados_b.empty:
                bebida_sel = st.selectbox(
                    "Selecione:", filtrados_b['Alimento'].tolist(), key="select_bebida"
                )
                info_b = df[df['Alimento'] == bebida_sel].iloc[0]

                qtd_b = st.number_input(
                    "Quantidade (ml):", min_value=1, max_value=2000,
                    value=200, step=50, key="qtd_bebida"
                )

                kcal_b  = info_b['Calorias (kcal)']  * qtd_b
                prot_b  = info_b['Proteínas (g)']    * qtd_b
                carb_b  = info_b['Carboidratos (g)'] * qtd_b
                gord_b  = info_b['Gorduras (g)']     * qtd_b
                fibra_b = info_b['Fibras (g)']       * qtd_b

                st.subheader("📊 Valores Nutricionais")
                b1, b2, b3, b4, b5 = st.columns(5)
                b1.metric("kcal",  f"{kcal_b:.0f}")
                b2.metric("Prot.", f"{prot_b:.1f}g")
                b3.metric("Carb.", f"{carb_b:.1f}g")
                b4.metric("Gord.", f"{gord_b:.1f}g")
                b5.metric("Fibra", f"{fibra_b:.1f}g")

                if st.button("➕ Adicionar bebida", use_container_width=True, key="btn_bebida"):
                    st.session_state.lista_alimentos.append({
                        'alimento': bebida_sel, 'quantidade': qtd_b, 'unidade': 'ml',
                        'kcal': kcal_b, 'proteina': prot_b, 'carboidrato': carb_b,
                        'gordura': gord_b, 'fibra': fibra_b, 'categoria': 'Bebida'
                    })
                    st.session_state.total_kcal        += kcal_b
                    st.session_state.total_proteina    += prot_b
                    st.session_state.total_carboidrato += carb_b
                    st.session_state.total_gordura     += gord_b
                    st.session_state.total_fibra       += fibra_b
                    st.success(f"✅ {bebida_sel} adicionada!")
                    st.rerun()

    # ===== COLUNA DIREITA: LISTA DA REFEIÇÃO =====
    with col_direita:
        data_fmt = st.session_state.data_refeicao.strftime('%d/%m/%Y')
        st.subheader(f"📝 {st.session_state.nome_refeicao} — {data_fmt}")

        if st.session_state.lista_alimentos:
            for i, item in enumerate(st.session_state.lista_alimentos):
                with st.container():
                    col_del, col_info = st.columns([1, 6])
                    with col_del:
                        if st.button("❌", key=f"del_{i}", help="Remover item"):
                            st.session_state.total_kcal        -= item['kcal']
                            st.session_state.total_proteina    -= item['proteina']
                            st.session_state.total_carboidrato -= item['carboidrato']
                            st.session_state.total_gordura     -= item['gordura']
                            st.session_state.total_fibra       -= item['fibra']
                            st.session_state.lista_alimentos.pop(i)
                            st.rerun()
                    with col_info:
                        icone = "🍛" if item['categoria'] == 'Comida' else "🥤"
                        st.write(f"{icone} **{item['alimento']}** — {item['quantidade']}{item['unidade']}")
                        st.caption(
                            f"{item['kcal']:.0f} kcal | "
                            f"P: {item['proteina']:.1f}g | "
                            f"C: {item['carboidrato']:.1f}g | "
                            f"G: {item['gordura']:.1f}g | "
                            f"F: {item['fibra']:.1f}g"
                        )

            st.divider()

            st.subheader("📊 Total da Refeição")
            t1, t2, t3, t4, t5 = st.columns(5)
            t1.metric("kcal",  f"{st.session_state.total_kcal:.0f}")
            t2.metric("Prot.", f"{st.session_state.total_proteina:.1f}g")
            t3.metric("Carb.", f"{st.session_state.total_carboidrato:.1f}g")
            t4.metric("Gord.", f"{st.session_state.total_gordura:.1f}g")
            t5.metric("Fibra", f"{st.session_state.total_fibra:.1f}g")

            if st.session_state.tdee_usuario > 0:
                perc = (st.session_state.total_kcal / st.session_state.tdee_usuario) * 100
                st.progress(min(perc / 100, 1.0))
                st.caption(
                    f"{perc:.1f}% do gasto diário "
                    f"({st.session_state.tdee_usuario:.0f} kcal)"
                )

            st.divider()

            st.markdown("### 💾 Salvar no Histórico")
            if st.button("✅ Salvar esta refeição", use_container_width=True, type="primary"):
                usuario = st.session_state.usuario_logado
                totais = {
                    'kcal':        st.session_state.total_kcal,
                    'proteina':    st.session_state.total_proteina,
                    'carboidrato': st.session_state.total_carboidrato,
                    'gordura':     st.session_state.total_gordura,
                    'fibra':       st.session_state.total_fibra,
                }
                ok, msg = salvar_refeicao(
                    user_id         = usuario['id'],
                    data_refeicao   = str(st.session_state.data_refeicao),
                    nome_refeicao   = st.session_state.nome_refeicao,
                    lista_alimentos = st.session_state.lista_alimentos,
                    totais          = totais
                )
                if ok:
                    st.success(msg)
                    st.session_state.lista_alimentos   = []
                    st.session_state.total_kcal        = 0.0
                    st.session_state.total_proteina    = 0.0
                    st.session_state.total_carboidrato = 0.0
                    st.session_state.total_gordura     = 0.0
                    st.session_state.total_fibra       = 0.0
                    st.balloons()
                    st.rerun()
                else:
                    st.error(msg)
        else:
            st.info(
                "Sua refeição está vazia.\n\n"
                "Use a aba Comidas para adicionar comidas.\n"
                "Use a aba Bebidas para adicionar bebidas.\n"
                "Se você procurou uma comida e não encontrou, verifique a grafia.\n"
                "Se mesmo assim não encontrar, mande o nome para: duvidassite00@Gmail.com"
            )


# ==============================================================================
# SEÇÃO 8 — ABA 4: HISTÓRICO DE REFEIÇÕES
# ==============================================================================

def aba_historico():
    """
    Quarta aba: exibe o histórico de refeições salvas do usuário logado,
    com filtro por período, visualização detalhada e opção de excluir.
    """
    st.title("📅 Histórico de Refeições")

    usuario = st.session_state.usuario_logado
    st.markdown(f"Exibindo registros de **{usuario['username']}**")

    st.subheader("🔎 Filtrar por Período")
    col_ini, col_fim, col_btn = st.columns([1, 1, 1])

    with col_ini:
        data_inicio = st.date_input("De:", value=date.today().replace(day=1), format="DD/MM/YYYY", key="hist_ini")
    with col_fim:
        data_fim = st.date_input("Até:", value=date.today(), format="DD/MM/YYYY", key="hist_fim")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("🔍 Buscar", use_container_width=True, type="primary")

    refeicoes = buscar_historico(usuario['id'], data_inicio, data_fim)

    st.divider()

    if not refeicoes:
        st.info("Nenhuma refeição encontrada para o período selecionado. 📭")
        return

    datas_unicas = sorted(
        set(r[1] for r in refeicoes),
        reverse=True
    )

    total_kcal_periodo = sum(r[3] for r in refeicoes if r[3])
    st.markdown(
        f"**{len(refeicoes)} refeição(ões)** encontrada(s) | "
        f"Total do período: **{total_kcal_periodo:.0f} kcal**"
    )
    st.divider()

    for data_str in datas_unicas:
        try:
            data_obj = datetime.strptime(data_str, '%Y-%m-%d')
            data_exib = data_obj.strftime('%d/%m/%Y')
        except Exception:
            data_exib = data_str

        refeicoes_do_dia = [r for r in refeicoes if r[1] == data_str]
        kcal_dia = sum(r[3] for r in refeicoes_do_dia if r[3])

        with st.expander(
            f"📆 **{data_exib}** — {len(refeicoes_do_dia)} refeição(ões) | "
            f"{kcal_dia:.0f} kcal no dia",
            expanded=(data_str == str(date.today()))
        ):
            for ref in refeicoes_do_dia:
                (ref_id, ref_data, ref_nome, ref_kcal, ref_prot,
                 ref_carb, ref_gord, ref_fibra, ref_registro) = ref

                col_ref, col_excluir = st.columns([5, 1])
                with col_ref:
                    st.markdown(f"#### 🍽️ {ref_nome or 'Refeição'}")
                    m1, m2, m3, m4, m5 = st.columns(5)
                    m1.metric("kcal",  f"{ref_kcal:.0f}"  if ref_kcal  else "—")
                    m2.metric("Prot.", f"{ref_prot:.1f}g"  if ref_prot  else "—")
                    m3.metric("Carb.", f"{ref_carb:.1f}g"  if ref_carb  else "—")
                    m4.metric("Gord.", f"{ref_gord:.1f}g"  if ref_gord  else "—")
                    m5.metric("Fibra", f"{ref_fibra:.1f}g" if ref_fibra else "—")

                with col_excluir:
                    if st.button("🗑️ Excluir", key=f"excl_{ref_id}",
                                 help="Excluir esta refeição permanentemente"):
                        if deletar_refeicao(ref_id):
                            st.success("Refeição excluída!")
                            st.rerun()
                        else:
                            st.error("Erro ao excluir.")

                itens = buscar_itens_refeicao(ref_id)
                if itens:
                    with st.expander("Ver alimentos desta refeição"):
                        df_itens = pd.DataFrame(
                            itens,
                            columns=["Alimento", "Qtd", "Und", "kcal",
                                     "Prot(g)", "Carb(g)", "Gord(g)", "Fibra(g)", "Tipo"]
                        )
                        for col_num in ["kcal", "Prot(g)", "Carb(g)", "Gord(g)", "Fibra(g)"]:
                            df_itens[col_num] = df_itens[col_num].apply(
                                lambda x: f"{x:.1f}" if pd.notna(x) else "—"
                            )
                        st.dataframe(df_itens, use_container_width=True, hide_index=True)

                st.caption(f"🕐 Registrada em: {ref_registro}")
                st.markdown("---")


# ==============================================================================
# SEÇÃO 9 — ABA 5: CALCULADORA DE IMC
# ==============================================================================

def aba_imc():
    """Quinta aba: calcula o IMC e exibe a classificação."""
    st.title("⚖️ Calculadora de IMC")

    usuario = st.session_state.usuario_logado
    st.markdown(f"Calculando para: **{usuario['username']}**")

    col1, col2 = st.columns(2)
    with col1:
        peso = st.number_input("Peso (kg):", min_value=1.0, max_value=500.0, value=70.0, step=0.1)
    with col2:
        altura = st.number_input("Altura (m):", min_value=0.5, max_value=2.5, value=1.70, step=0.01)

    if st.button("📊 Calcular IMC", type="primary", use_container_width=True):
        imc = peso / (altura ** 2)

        if imc < 18.5:
            classe = "Abaixo do peso"
            desc   = "Atenção: Seu peso está abaixo do recomendado para sua altura."
        elif 18.5 <= imc < 25:
            classe = "Peso ideal"
            desc   = "Parabéns! Você está na faixa de peso considerada saudável."
        elif 25 <= imc < 30:
            classe = "Sobrepeso"
            desc   = "Cuidado: Você está levemente acima do peso ideal."
        else:
            classe = "Obesidade"
            desc   = "Atenção: Seu IMC indica obesidade. Procure orientação profissional."

        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("Seu IMC", f"{imc:.1f}")
        c2.metric("Classificação", classe)

        if 18.5 <= imc < 25:
            st.success(desc)
        elif imc < 18.5 or (25 <= imc < 30):
            st.warning(desc)
        else:
            st.error(desc)

    st.divider()

    with st.expander("📌 Veja a Tabela de Referência (OMS)"):
        df_ref = pd.DataFrame({
            "IMC":           ["Menos de 18.5", "18.5 – 24.9", "25.0 – 29.9",
                              "30.0 – 34.9", "35.0 – 39.9", "Mais de 40"],
            "Classificação": ["Abaixo do peso", "Peso Normal", "Sobrepeso",
                              "Obesidade Grau I", "Obesidade Grau II", "Obesidade Grau III"],
            "Risco de Doenças": ["Elevado", "Mínimo", "Aumentado", "Moderado", "Grave", "Muito Grave"]
        })
        st.table(df_ref)

    st.info("""
    **Nota:** O IMC é um indicador útil, mas não mede diretamente a gordura corporal.
    Atletas ou idosos podem ter interpretações diferentes devido à massa muscular ou óssea.
    """)


# ==============================================================================
# SEÇÃO 10 — SIDEBAR DO USUÁRIO LOGADO
# ==============================================================================

def sidebar_usuario():
    """Exibe informações do usuário e botão de logout na barra lateral."""
    usuario = st.session_state.usuario_logado
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### 👤 {usuario['username']}")
    st.sidebar.caption(usuario['email'])

    if st.sidebar.button("🚪 Sair (Logout)", use_container_width=True):
        for chave in list(st.session_state.keys()):
            del st.session_state[chave]
        st.rerun()

    st.sidebar.markdown("---")


# ==============================================================================
# FUNÇÃO PRINCIPAL
# ==============================================================================

def main():
    """
    Ponto de entrada do app.
    1. Inicializa o session_state.
    2. Se não logado → mostra tela de login.
    3. Se logado → mostra o app completo com 5 abas.
    """
    init_session_state()

    if st.session_state.usuario_logado is None:
        tela_login()
        return

    sidebar_usuario()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📖 Sobre Nutrição",
        "⚖️ Calculadora TMB",
        "🔍 Calculadora de Refeição",
        "📅 Histórico",
        "⚖️ IMC"
    ])

    with tab1: aba_sobre_nutricao()
    with tab2: aba_calculadora_tmb()
    with tab3: aba_buscador_alimentos()
    with tab4: aba_historico()
    with tab5: aba_imc()

    st.divider()
    st.caption("Sistema Nutricional — Baseado no Guia Alimentar para a População Brasileira "
               "feito por Rafael Borsoi e Tiago Makowski Spassini")


# ==============================================================================
# PONTO DE ENTRADA
# ==============================================================================
if __name__ == "__main__":
    main()
