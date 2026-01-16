"""
Componentes de layout compartilhados.
"""

from pathlib import Path
import streamlit as st
from utils.auth import logout

LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "logo.png"


def render_logo(width: int = 160) -> None:
    """Renderiza o logo do app."""
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=width)
    else:
        st.markdown("**Gestão de Obras**")


def render_top_logo(width: int = 140) -> None:
    """Renderiza o logo alinhado à direita no topo da tela."""
    _, col_logo = st.columns([6, 1])
    with col_logo:
        render_logo(width=width)


def render_sidebar(profile: dict) -> None:
    """Renderiza a sidebar padrão para usuários autenticados."""
    with st.sidebar:
        st.markdown(f"""
        <div style="padding: 20px; background: #f0f2f6; border-radius: 10px; margin: 10px 0 20px 0;">
            <h3 style="margin: 0;">👤 {profile['usuario']}</h3>
            <p style="margin: 5px 0; color: #666;">Perfil: <strong>{profile['perfil']}</strong></p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚪 Sair", use_container_width=True):
            logout()
            st.rerun()

        st.markdown("---")
