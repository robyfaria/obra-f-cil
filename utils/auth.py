"""
Módulo de autenticação com Supabase
"""

import os
import streamlit as st
from yarl import URL
from supabase import create_client, Client
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()


def get_supabase_client() -> Client:
    """Retorna o cliente Supabase da sessão"""
    if 'supabase' not in st.session_state:
        init_supabase()
    return st.session_state['supabase']


def init_supabase():
    """Inicializa o cliente Supabase"""
    if 'supabase' in st.session_state:
        return
    
    # Tenta carregar das variáveis de ambiente ou secrets do Streamlit
    url = os.getenv('SUPABASE_URL') or st.secrets.get('SUPABASE_URL')
    key = os.getenv('SUPABASE_ANON_KEY') or st.secrets.get('SUPABASE_ANON_KEY')
    storage_url = os.getenv('SUPABASE_STORAGE_URL') or st.secrets.get('SUPABASE_STORAGE_URL')
    storage_region = os.getenv('SUPABASE_STORAGE_REGION') or st.secrets.get('SUPABASE_STORAGE_REGION')
    
    if not url or not key:
        st.error("""
        ⚠️ **Configuração necessária**
        
        Configure as variáveis de ambiente:
        - SUPABASE_URL
        - SUPABASE_ANON_KEY
        
        Veja o README.md para instruções.
        """)
        st.stop()
    
    supabase = create_client(url, key)

    if storage_url:
        supabase.storage_url = URL(storage_url if storage_url.endswith("/") else f"{storage_url}/")

    if storage_region:
        supabase.options.headers["x-amz-bucket-region"] = storage_region
        supabase.options.headers["x-amz-region"] = storage_region

    st.session_state['supabase'] = supabase


def login(email: str, password: str) -> tuple[bool, str]:
    """
    Realiza login no Supabase Auth
    
    Returns:
        tuple: (sucesso: bool, mensagem: str)
    """
    try:
        supabase = get_supabase_client()
        
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user:
            st.session_state['user'] = {
                'id': response.user.id,
                'email': response.user.email
            }
            st.session_state['access_token'] = response.session.access_token
            return True, "Login realizado com sucesso!"
        
        return False, "Credenciais inválidas"
        
    except Exception as e:
        error_msg = str(e)
        if "Invalid login credentials" in error_msg:
            return False, "E-mail ou senha incorretos"
        elif "Email not confirmed" in error_msg:
            return False, "E-mail não confirmado. Verifique sua caixa de entrada."
        else:
            return False, f"Erro ao fazer login: {error_msg}"


def logout():
    """Realiza logout"""
    try:
        supabase = get_supabase_client()
        supabase.auth.sign_out()
    except:
        pass
    
    # Limpa a sessão
    for key in ['user', 'user_profile', 'access_token']:
        if key in st.session_state:
            del st.session_state[key]


def get_current_user() -> dict | None:
    """Retorna o usuário atual logado"""
    return st.session_state.get('user')


def get_user_profile(auth_user_id: str) -> dict | None:
    """
    Busca o perfil do usuário em public.usuarios_app
    
    Args:
        auth_user_id: UUID do usuário no auth.users
        
    Returns:
        dict com dados do perfil ou None
    """
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('usuarios_app') \
            .select('*') \
            .eq('auth_user_id', auth_user_id) \
            .single() \
            .execute()
        
        return response.data
        
    except Exception as e:
        print(f"Erro ao buscar perfil: {e}")
        return None


def is_admin() -> bool:
    """Verifica se o usuário atual é ADMIN"""
    profile = st.session_state.get('user_profile')
    return profile and profile.get('perfil') == 'ADMIN'


def is_operacao() -> bool:
    """Verifica se o usuário atual é OPERACAO"""
    profile = st.session_state.get('user_profile')
    return profile and profile.get('perfil') == 'OPERACAO'


def require_auth():
    """
    Decorator/helper que requer autenticação
    Redireciona para login se não autenticado
    """
    user = get_current_user()
    profile = st.session_state.get('user_profile')
    
    if not user or not profile:
        st.warning("⚠️ Você precisa estar logado para acessar esta página.")
        st.markdown("[👉 Ir para Login](./)")
        st.stop()
    
    if not profile.get('ativo', False):
        st.error("⚠️ Sua conta está inativa.")
        st.stop()
    
    return profile


def require_admin():
    """
    Requer que o usuário seja ADMIN
    """
    profile = require_auth()
    
    if profile.get('perfil') != 'ADMIN':
        st.error("🚫 Acesso restrito a administradores.")
        st.stop()
    
    return profile
