"""
Página de Configurações - Usuários e Auditoria (ADMIN only)
"""

import streamlit as st
from datetime import date, timedelta
from utils.auth import require_admin
from utils.db import get_usuarios_app, update_usuario_app, get_auditoria, get_servicos, create_servico
from utils.auditoria import audit_update, audit_insert
from utils.layout import render_sidebar, render_top_logo

# Requer ADMIN
profile = require_admin()
render_sidebar(profile)
render_top_logo()

st.title("⚙️ Configurações")

tab1, tab2, tab3 = st.tabs(["👥 Usuários", "📋 Auditoria", "🔧 Serviços"])

# ============================================
# USUÁRIOS
# ============================================

with tab1:
    st.markdown("### 👥 Usuários do Sistema")
    
    usuarios = get_usuarios_app()
    
    if not usuarios:
        st.info("📋 Nenhum usuário cadastrado.")
    else:
        for user in usuarios:
            status_icon = "🟢" if user.get('ativo', True) else "🔴"
            perfil_emoji = "👑" if user.get('perfil') == 'ADMIN' else "👷"
            
            with st.expander(f"{status_icon} {user['usuario']} {perfil_emoji}"):
                st.markdown(f"**Perfil:** {user.get('perfil', '-')}")
                st.markdown(f"**Ativo:** {'Sim' if user.get('ativo') else 'Não'}")
                st.markdown(f"**Auth ID:** `{user.get('auth_user_id', '-')}`")
                
                st.markdown("---")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    novo_perfil = st.selectbox(
                        "Alterar Perfil",
                        options=['ADMIN', 'OPERACAO'],
                        index=0 if user.get('perfil') == 'ADMIN' else 1,
                        key=f"perfil_{user['id']}"
                    )
                
                with col2:
                    novo_ativo = st.checkbox("Ativo", value=user.get('ativo', True), key=f"ativo_{user['id']}")
                
                if st.button("💾 Salvar Alterações", key=f"save_{user['id']}"):
                    antes = {'perfil': user.get('perfil'), 'ativo': user.get('ativo')}
                    novos_dados = {'perfil': novo_perfil, 'ativo': novo_ativo}
                    
                    success, msg = update_usuario_app(user['id'], novos_dados)
                    
                    if success:
                        audit_update('usuarios_app', user['id'], antes, novos_dados)
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
    
    st.markdown("---")
    st.info("""
    💡 **Para criar novos usuários:**
    1. Crie o usuário no Supabase Auth (Dashboard > Authentication > Users)
    2. Insira um registro em `public.usuarios_app` com o `auth_user_id` correspondente
    """)

# ============================================
# AUDITORIA
# ============================================

with tab2:
    st.markdown("### 📋 Logs de Auditoria")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        entidade_filter = st.selectbox(
            "Entidade",
            options=['', 'clientes', 'pessoas', 'obras', 'orcamentos', 'alocacoes', 'apontamentos', 'recebimentos', 'pagamentos'],
            format_func=lambda x: 'Todas' if x == '' else x.title()
        )
    
    with col2:
        data_inicio = st.date_input("De", value=date.today() - timedelta(days=7))
    
    with col3:
        data_fim = st.date_input("Até", value=date.today())
    
    busca_usuario = st.text_input("🔍 Buscar por usuário")
    
    # Lista de logs
    logs = get_auditoria(
        entidade=entidade_filter if entidade_filter else None,
        data_inicio=data_inicio,
        data_fim=data_fim,
        busca=busca_usuario if busca_usuario else None
    )
    
    if not logs:
        st.info("📋 Nenhum registro encontrado.")
    else:
        st.markdown(f"**{len(logs)} registro(s) encontrado(s)** (máx. 100)")
        
        for log in logs:
            acao_emoji = {
                'INSERT': '➕',
                'UPDATE': '✏️',
                'DELETE': '🗑️',
                'STATUS_CHANGE': '🔄'
            }.get(log.get('acao', ''), '📋')
            
            with st.expander(f"{acao_emoji} {log.get('entidade', '-')} #{log.get('entidade_id', '-')} por {log.get('usuario', '-')}"):
                st.markdown(f"**Data:** {log.get('criado_em', '-')}")
                st.markdown(f"**Ação:** {log.get('acao', '-')}")
                
                if log.get('antes_json'):
                    st.markdown("**Antes:**")
                    st.json(log['antes_json'])
                
                if log.get('depois_json'):
                    st.markdown("**Depois:**")
                    st.json(log['depois_json'])

# ============================================
# SERVIÇOS (CATÁLOGO)
# ============================================

with tab3:
    st.markdown("### 🔧 Catálogo de Serviços")
    
    servicos = get_servicos(ativo=None)
    
    if servicos:
        for serv in servicos:
            status_icon = "🟢" if serv.get('ativo', True) else "🔴"
            st.markdown(f"{status_icon} **{serv['nome']}** ({serv.get('unidade', '-')})")
    else:
        st.info("📋 Nenhum serviço cadastrado.")
    
    st.markdown("---")
    st.markdown("### ➕ Novo Serviço")
    
    with st.form("form_novo_servico"):
        nome = st.text_input("Nome do Serviço *", placeholder="Ex: Pintura de parede")
        
        unidade = st.selectbox("Unidade", options=['UN', 'M2', 'ML', 'H', 'DIA'])
        
        if st.form_submit_button("✅ Criar Serviço", type="primary"):
            if not nome:
                st.error("⚠️ Informe o nome do serviço!")
            else:
                success, msg, novo = create_servico(nome, unidade)
                
                if success:
                    audit_insert('servicos', novo)
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
