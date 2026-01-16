"""
Página de Clientes - CRUD simples com busca e filtros
"""

import streamlit as st
from utils.auth import require_auth
from utils.db import get_clientes, get_cliente, create_cliente, update_cliente, toggle_cliente_ativo
from utils.auditoria import audit_insert, audit_update
from utils.layout import render_sidebar, render_top_logo

# Requer autenticação
profile = require_auth()
render_sidebar(profile)
render_top_logo()

st.title("👥 Clientes")

# Estado da página
if 'cliente_view' not in st.session_state:
    st.session_state['cliente_view'] = 'lista'
if 'cliente_edit_id' not in st.session_state:
    st.session_state['cliente_edit_id'] = None

# Função para voltar à lista
def voltar_lista():
    st.session_state['cliente_view'] = 'lista'
    st.session_state['cliente_edit_id'] = None


# ============================================
# LISTA DE CLIENTES
# ============================================

if st.session_state['cliente_view'] == 'lista':
    
    # Botão de novo cliente
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Novo Cliente", type="primary", use_container_width=True):
            st.session_state['cliente_view'] = 'novo'
            st.rerun()
    
    st.markdown("---")
    
    # Filtros
    col1, col2 = st.columns([2, 1])
    
    with col1:
        busca = st.text_input(
            "🔍 Buscar",
            placeholder="Nome ou telefone...",
            key="busca_cliente"
        )
    
    with col2:
        filtro_ativo = st.selectbox(
            "Situação",
            options=[None, True, False],
            format_func=lambda x: 'Todos' if x is None else ('Ativos' if x else 'Inativos'),
            key="filtro_ativo_cliente"
        )
    
    # Lista de clientes
    clientes = get_clientes(busca=busca, ativo=filtro_ativo)
    
    if not clientes:
        st.info("📋 Nenhum cliente encontrado.")
    else:
        st.markdown(f"**{len(clientes)} cliente(s) encontrado(s)**")
        
        for cliente in clientes:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 2])
                
                with col1:
                    status_icon = "🟢" if cliente.get('ativo', True) else "🔴"
                    st.markdown(f"""
                    **{cliente['nome']}** {status_icon}  
                    📞 {cliente.get('telefone', '-')} | 📍 {cliente.get('endereco', '-')}
                    """)
                
                with col2:
                    if st.button("✏️ Editar", key=f"edit_{cliente['id']}", use_container_width=True):
                        st.session_state['cliente_view'] = 'editar'
                        st.session_state['cliente_edit_id'] = cliente['id']
                        st.rerun()
                
                with col3:
                    if cliente.get('ativo', True):
                        if st.button("🔴 Inativar", key=f"inativar_{cliente['id']}", use_container_width=True):
                            antes = {'ativo': True}
                            success, msg = toggle_cliente_ativo(cliente['id'], False)
                            if success:
                                audit_update('clientes', cliente['id'], antes, {'ativo': False})
                                st.success("Cliente inativado!")
                                st.rerun()
                    else:
                        if st.button("🟢 Ativar", key=f"ativar_{cliente['id']}", use_container_width=True):
                            antes = {'ativo': False}
                            success, msg = toggle_cliente_ativo(cliente['id'], True)
                            if success:
                                audit_update('clientes', cliente['id'], antes, {'ativo': True})
                                st.success("Cliente ativado!")
                                st.rerun()
                
                st.markdown("---")


# ============================================
# NOVO CLIENTE
# ============================================

elif st.session_state['cliente_view'] == 'novo':
    
    st.markdown("### ➕ Novo Cliente")
    
    if st.button("⬅️ Voltar"):
        voltar_lista()
        st.rerun()
    
    st.markdown("---")
    
    with st.form("form_novo_cliente", clear_on_submit=True):
        nome = st.text_input("👤 Nome *", placeholder="Nome completo do cliente")
        telefone = st.text_input("📞 Telefone", placeholder="(00) 00000-0000")
        endereco = st.text_input("📍 Endereço", placeholder="Endereço completo")
        
        col1, col2 = st.columns(2)
        
        with col1:
            submitted = st.form_submit_button("✅ Salvar", type="primary", use_container_width=True)
        
        with col2:
            if st.form_submit_button("❌ Cancelar", use_container_width=True):
                voltar_lista()
                st.rerun()
        
        if submitted:
            if not nome:
                st.error("⚠️ O nome é obrigatório!")
            else:
                success, msg, novo_cliente = create_cliente(nome, telefone, endereco)
                
                if success:
                    audit_insert('clientes', novo_cliente)
                    st.success(f"✅ {msg}")
                    voltar_lista()
                    st.rerun()
                else:
                    st.error(msg)


# ============================================
# EDITAR CLIENTE
# ============================================

elif st.session_state['cliente_view'] == 'editar':
    
    cliente_id = st.session_state['cliente_edit_id']
    cliente = get_cliente(cliente_id)
    
    if not cliente:
        st.error("Cliente não encontrado.")
        voltar_lista()
        st.rerun()
    
    st.markdown(f"### ✏️ Editar Cliente")
    
    if st.button("⬅️ Voltar"):
        voltar_lista()
        st.rerun()
    
    st.markdown("---")
    
    with st.form("form_editar_cliente"):
        nome = st.text_input("👤 Nome *", value=cliente['nome'])
        telefone = st.text_input("📞 Telefone", value=cliente.get('telefone', '') or '')
        endereco = st.text_input("📍 Endereço", value=cliente.get('endereco', '') or '')
        ativo = st.checkbox("Cliente Ativo", value=cliente.get('ativo', True))
        
        col1, col2 = st.columns(2)
        
        with col1:
            submitted = st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True)
        
        with col2:
            if st.form_submit_button("❌ Cancelar", use_container_width=True):
                voltar_lista()
                st.rerun()
        
        if submitted:
            if not nome:
                st.error("⚠️ O nome é obrigatório!")
            else:
                antes = {
                    'nome': cliente['nome'],
                    'telefone': cliente.get('telefone'),
                    'endereco': cliente.get('endereco'),
                    'ativo': cliente.get('ativo')
                }
                
                novos_dados = {
                    'nome': nome,
                    'telefone': telefone,
                    'endereco': endereco,
                    'ativo': ativo
                }
                
                success, msg = update_cliente(cliente_id, novos_dados)
                
                if success:
                    audit_update('clientes', cliente_id, antes, novos_dados)
                    st.success(f"✅ {msg}")
                    voltar_lista()
                    st.rerun()
                else:
                    st.error(msg)
