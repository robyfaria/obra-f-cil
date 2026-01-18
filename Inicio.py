"""
Gestão de Obras de Pintura - App Principal
Interface 60+ friendly com Supabase como backend
"""

import streamlit as st
from utils.auth import init_supabase, login, logout, get_current_user, get_user_profile
from utils.layout import render_centered_logo, render_sidebar, render_top_logo

# Configuração da página
st.set_page_config(
    page_title="Gestão de Obras",
    page_icon="assets/icon.ico",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado para UX 60+
st.markdown("""
<style>
    /* Fontes maiores e mais legíveis */
    .stApp {
        font-size: 18px;
    }
    
    /* Botões maiores */
    .stButton > button {
        font-size: 18px !important;
        padding: 12px 24px !important;
        min-height: 50px !important;
    }
    
    /* Inputs maiores */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stNumberInput > div > div > input {
        font-size: 18px !important;
        padding: 12px !important;
    }
    
    /* Labels mais visíveis */
    .stTextInput > label,
    .stSelectbox > label,
    .stNumberInput > label {
        font-size: 16px !important;
        font-weight: 600 !important;
    }
    
    /* Sidebar mais limpa */
    .css-1d391kg {
        padding-top: 2rem;
    }
    
    /* Títulos */
    h1 {
        font-size: 2.5rem !important;
        color: #1a5276 !important;
    }
    
    h2 {
        font-size: 2rem !important;
        color: #2c3e50 !important;
    }
    
    h3 {
        font-size: 1.5rem !important;
    }
    
    /* Mensagens de sucesso/erro mais visíveis */
    .stSuccess, .stError, .stWarning, .stInfo {
        font-size: 18px !important;
        padding: 16px !important;
    }
    
    /* Tabelas mais legíveis */
    .dataframe {
        font-size: 16px !important;
    }
    
    /* Cards de estatísticas */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

def show_login_page():
    """Exibe a página de login"""
    st.markdown("---")

    render_centered_logo(width=150)

    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 40px 0;">
            <h1 style="color: #1a5276;">🎨 Gestão de Obras</h1>
            <p style="font-size: 20px; color: #666;">Sistema de Gerenciamento de Obras de Pintura</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🔐 Acesse sua conta")
        
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input(
                "📧 E-mail",
                placeholder="seu.email@exemplo.com",
                key="login_email"
            )
            
            password = st.text_input(
                "🔑 Senha",
                type="password",
                placeholder="Sua senha",
                key="login_password"
            )
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                submitted = st.form_submit_button(
                    "✅ Entrar",
                    use_container_width=True,
                    type="primary"
                )
            
            if submitted:
                if not email or not password:
                    st.error("⚠️ Preencha e-mail e senha!")
                else:
                    with st.spinner("Verificando..."):
                        success, message = login(email, password)
                        
                        if success:
                            st.success("✅ Login realizado com sucesso!")
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
        
        st.markdown("""
        <div style="text-align: center; margin-top: 40px; color: #888;">
            <p>Problemas para acessar? Entre em contato com o administrador.</p>
        </div>
        """, unsafe_allow_html=True)


def show_home_page(user_profile):
    """Exibe a página inicial após login"""
    
    render_sidebar(user_profile)
    render_top_logo()
    
    # Conteúdo principal
    st.markdown(f"""
    <div style="padding: 20px 0;">
        <h1>🎨 Bem-vindo, {user_profile['usuario']}!</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📊 Painel Rápido")
    
    # Cards de resumo
    col1, col2, col3, col4 = st.columns(4)
    
    from utils.db import get_dashboard_stats
    stats = get_dashboard_stats()
    
    with col1:
        st.metric(
            label="🏗️ Obras Ativas",
            value=stats.get('obras_ativas', 0)
        )
    
    with col2:
        st.metric(
            label="📋 Orçamentos Pendentes",
            value=stats.get('orcamentos_pendentes', 0)
        )
    
    with col3:
        st.metric(
            label="👷 Profissionais Ativos",
            value=stats.get('pessoas_ativas', 0)
        )
    
    with col4:
        st.metric(
            label="👥 Clientes Ativos",
            value=stats.get('clientes_ativos', 0)
        )

    col5, col6, col7, col8 = st.columns(4)

    with col5:
        st.metric(
            label="💰 Recebimentos do Mês",
            value=f"R$ {stats.get('recebimentos_mes', 0):,.2f}"
        )

    with col6:
        st.metric(
            label="📤 Pagamentos do Mês",
            value=f"R$ {stats.get('pagamentos_mes', 0):,.2f}"
        )

    with col7:
        st.metric(
            label="📈 Resultado do Mês",
            value=f"R$ {stats.get('resultado_mes', 0):,.2f}"
        )

    with col8:
        st.metric(
            label="🧱 Fases Não Concluídas",
            value=stats.get('fases_nao_concluidas', 0)
        )
    
    st.markdown("---")
    
    # Ações rápidas
    st.markdown("### ⚡ Ações Rápidas")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ Nova Obra", use_container_width=True, type="primary"):
            st.switch_page("pages/1_🏠_Obras.py")
    
    with col2:
        if st.button("📅 Ver Agenda de Hoje", use_container_width=True):
            st.switch_page("pages/5_📅_Agenda.py")
    
    with col3:
        if st.button("👥 Gerenciar Clientes", use_container_width=True):
            st.switch_page("pages/2_👥_Clientes.py")


def main():
    """Função principal do app"""
    
    # Inicializa o cliente Supabase
    init_supabase()
    
    # Verifica se há usuário logado
    user = get_current_user()
    
    if not user:
        show_login_page()
        return
    
    # Busca o perfil do usuário
    profile = get_user_profile(user['id'])
    
    if not profile:
        st.error("""
        ⚠️ **Usuário sem permissão**
        
        Seu usuário não está cadastrado no sistema ou está inativo.
        Entre em contato com o administrador.
        """)
        
        if st.button("🚪 Sair"):
            logout()
            st.rerun()
        return
    
    if not profile.get('ativo', False):
        st.error("""
        ⚠️ **Usuário inativo**
        
        Sua conta está desativada. Entre em contato com o administrador.
        """)
        
        if st.button("🚪 Sair"):
            logout()
            st.rerun()
        return
    
    # Armazena o perfil na sessão
    st.session_state['user_profile'] = profile
    
    # Exibe a página inicial
    show_home_page(profile)


if __name__ == "__main__":
    main()
