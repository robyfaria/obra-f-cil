"""
Componentes de layout compartilhados.
"""

from pathlib import Path
import base64
import streamlit as st
from utils.auth import logout

LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "logo.png"


def render_logo(width: int = 160) -> None:
    """Renderiza o logo do app."""
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=width)
    else:
        st.markdown("**Gestão de Obras**")


def render_centered_logo(width: int = 140) -> None:
    """Renderiza o logo centralizado para telas de login."""
    if not LOGO_PATH.exists():
        st.markdown("**Gestão de Obras**")
        return

    logo_bytes = LOGO_PATH.read_bytes()
    logo_b64 = base64.b64encode(logo_bytes).decode("utf-8")
    st.markdown(
        f"""
        <div style="display: flex; justify-content: center; align-items: center; padding: 16px 0;">
            <img
                src="data:image/png;base64,{logo_b64}"
                alt="Gestão de Obras"
                style="width: {width}px; max-width: 55vw; height: auto; display: block;"
            />
        </div>
        """,
        unsafe_allow_html=True,
    )


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
