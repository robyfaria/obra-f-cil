"""
Página de Pessoas/Profissionais - CRUD com filtros por tipo
"""

import streamlit as st
from utils.auth import require_auth
from utils.db import get_pessoas, get_pessoa, create_pessoa, update_pessoa
from utils.auditoria import audit_insert, audit_update
from utils.layout import render_sidebar, render_top_logo

# Requer autenticação
profile = require_auth()
render_sidebar(profile)
render_top_logo()

st.title("👷 Profissionais")

# Estado da página
if 'pessoa_view' not in st.session_state:
    st.session_state['pessoa_view'] = 'lista'
if 'pessoa_edit_id' not in st.session_state:
    st.session_state['pessoa_edit_id'] = None

TIPOS_PESSOA = ['PINTOR', 'AJUDANTE', 'TERCEIRO']

def voltar_lista():
    st.session_state['pessoa_view'] = 'lista'
    st.session_state['pessoa_edit_id'] = None


# ============================================
# LISTA DE PESSOAS
# ============================================

if st.session_state['pessoa_view'] == 'lista':
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Novo Profissional", type="primary", use_container_width=True):
            st.session_state['pessoa_view'] = 'novo'
            st.rerun()
    
    st.markdown("---")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        busca = st.text_input("🔍 Buscar", placeholder="Nome...")
    
    with col2:
        tipo_filter = st.selectbox(
            "Tipo",
            options=[''] + TIPOS_PESSOA,
            format_func=lambda x: 'Todos' if x == '' else x
        )
    
    with col3:
        ativo_filter = st.selectbox(
            "Situação",
            options=[None, True, False],
            format_func=lambda x: 'Todos' if x is None else ('Ativos' if x else 'Inativos')
        )
    
    # Lista
    pessoas = get_pessoas(
        busca=busca,
        tipo=tipo_filter if tipo_filter else None,
        ativo=ativo_filter
    )
    
    if not pessoas:
        st.info("📋 Nenhum profissional encontrado.")
    else:
        st.markdown(f"**{len(pessoas)} profissional(is) encontrado(s)**")
        
        for pessoa in pessoas:
            tipo_emoji = {
                'PINTOR': '🎨',
                'AJUDANTE': '🔧',
                'TERCEIRO': '🤝'
            }.get(pessoa.get('tipo', ''), '👷')
            
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    status_icon = "🟢" if pessoa.get('ativo', True) else "🔴"
                    st.markdown(f"""
                    **{pessoa['nome']}** {status_icon}  
                    {tipo_emoji} {pessoa.get('tipo', '-')} | 💵 Diária: R$ {pessoa.get('diaria_base', 0):,.2f}
                    """)
                    if pessoa.get('telefone'):
                        st.markdown(f"📞 {pessoa['telefone']}")
                
                with col2:
                    if st.button("✏️ Editar", key=f"edit_{pessoa['id']}", use_container_width=True):
                        st.session_state['pessoa_view'] = 'editar'
                        st.session_state['pessoa_edit_id'] = pessoa['id']
                        st.rerun()
                
                with col3:
                    if pessoa.get('ativo', True):
                        if st.button("🔴 Inativar", key=f"inativar_{pessoa['id']}", use_container_width=True):
                            antes = {'ativo': True}
                            success, msg = update_pessoa(pessoa['id'], {'ativo': False})
                            if success:
                                audit_update('pessoas', pessoa['id'], antes, {'ativo': False})
                                st.rerun()
                    else:
                        if st.button("🟢 Ativar", key=f"ativar_{pessoa['id']}", use_container_width=True):
                            antes = {'ativo': False}
                            success, msg = update_pessoa(pessoa['id'], {'ativo': True})
                            if success:
                                audit_update('pessoas', pessoa['id'], antes, {'ativo': True})
                                st.rerun()
                
                st.markdown("---")


# ============================================
# NOVO PROFISSIONAL
# ============================================

elif st.session_state['pessoa_view'] == 'novo':
    
    st.markdown("### ➕ Novo Profissional")
    
    if st.button("⬅️ Voltar"):
        voltar_lista()
        st.rerun()
    
    st.markdown("---")
    
    with st.form("form_nova_pessoa"):
        nome = st.text_input("👤 Nome *", placeholder="Nome completo")
        
        tipo = st.selectbox("🏷️ Tipo *", options=TIPOS_PESSOA)
        
        telefone = st.text_input("📞 Telefone", placeholder="(00) 00000-0000")
        
        diaria_base = st.number_input(
            "💵 Diária Base (R$)",
            min_value=0.0,
            step=10.0,
            format="%.2f"
        )
        
        observacao = st.text_area("📝 Observação", placeholder="Anotações sobre o profissional...")
        
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
                dados = {
                    'nome': nome,
                    'tipo': tipo,
                    'telefone': telefone,
                    'diaria_base': diaria_base,
                    'observacao': observacao
                }
                
                success, msg, nova_pessoa = create_pessoa(dados)
                
                if success:
                    audit_insert('pessoas', nova_pessoa)
                    st.success(f"✅ {msg}")
                    voltar_lista()
                    st.rerun()
                else:
                    st.error(msg)


# ============================================
# EDITAR PROFISSIONAL
# ============================================

elif st.session_state['pessoa_view'] == 'editar':
    
    pessoa_id = st.session_state['pessoa_edit_id']
    pessoa = get_pessoa(pessoa_id)
    
    if not pessoa:
        st.error("Profissional não encontrado.")
        voltar_lista()
        st.rerun()
    
    st.markdown("### ✏️ Editar Profissional")
    
    if st.button("⬅️ Voltar"):
        voltar_lista()
        st.rerun()
    
    st.markdown("---")
    
    with st.form("form_editar_pessoa"):
        nome = st.text_input("👤 Nome *", value=pessoa['nome'])
        
        tipo_index = TIPOS_PESSOA.index(pessoa['tipo']) if pessoa.get('tipo') in TIPOS_PESSOA else 0
        tipo = st.selectbox("🏷️ Tipo *", options=TIPOS_PESSOA, index=tipo_index)
        
        telefone = st.text_input("📞 Telefone", value=pessoa.get('telefone', '') or '')
        
        diaria_base = st.number_input(
            "💵 Diária Base (R$)",
            min_value=0.0,
            value=float(pessoa.get('diaria_base', 0) or 0),
            step=10.0,
            format="%.2f"
        )
        
        observacao = st.text_area("📝 Observação", value=pessoa.get('observacao', '') or '')
        
        ativo = st.checkbox("Profissional Ativo", value=pessoa.get('ativo', True))
        
        col1, col2 = st.columns(2)
        
        with col1:
            submitted = st.form_submit_button("💾 Salvar", type="primary", use_container_width=True)
        
        with col2:
            if st.form_submit_button("❌ Cancelar", use_container_width=True):
                voltar_lista()
                st.rerun()
        
        if submitted:
            if not nome:
                st.error("⚠️ O nome é obrigatório!")
            else:
                antes = {
                    'nome': pessoa['nome'],
                    'tipo': pessoa.get('tipo'),
                    'telefone': pessoa.get('telefone'),
                    'diaria_base': pessoa.get('diaria_base'),
                    'observacao': pessoa.get('observacao'),
                    'ativo': pessoa.get('ativo')
                }
                
                novos_dados = {
                    'nome': nome,
                    'tipo': tipo,
                    'telefone': telefone,
                    'diaria_base': diaria_base,
                    'observacao': observacao,
                    'ativo': ativo
                }
                
                success, msg = update_pessoa(pessoa_id, novos_dados)
                
                if success:
                    audit_update('pessoas', pessoa_id, antes, novos_dados)
                    st.success(f"✅ {msg}")
                    voltar_lista()
                    st.rerun()
                else:
                    st.error(msg)
