"""
Página de Agenda/Alocações - Visão por dia
"""

import streamlit as st
from datetime import date, timedelta
from utils.auth import require_auth
from utils.db import (
    get_alocacoes_dia, create_alocacao, delete_alocacao,
    get_pessoas, get_obras, get_orcamentos_por_obra, get_fases_por_orcamento
)
from utils.auditoria import audit_insert, audit_delete

# Requer autenticação
profile = require_auth()

st.title("📅 Agenda de Alocações")

# ============================================
# SELEÇÃO DE DATA
# ============================================

col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    if st.button("⬅️ Dia Anterior"):
        if 'data_agenda' not in st.session_state:
            st.session_state['data_agenda'] = date.today()
        st.session_state['data_agenda'] = st.session_state['data_agenda'] - timedelta(days=1)
        st.rerun()

with col2:
    if 'data_agenda' not in st.session_state:
        st.session_state['data_agenda'] = date.today()
    
    data_selecionada = st.date_input(
        "📆 Data",
        value=st.session_state['data_agenda'],
        key="input_data_agenda"
    )
    st.session_state['data_agenda'] = data_selecionada

with col3:
    if st.button("➡️ Próximo Dia"):
        st.session_state['data_agenda'] = st.session_state['data_agenda'] + timedelta(days=1)
        st.rerun()

st.markdown(f"### 📋 Alocações para {data_selecionada.strftime('%d/%m/%Y')}")

st.markdown("---")

# ============================================
# LISTA DE ALOCAÇÕES DO DIA
# ============================================

alocacoes = get_alocacoes_dia(data_selecionada)

if not alocacoes:
    st.info("📋 Nenhuma alocação para este dia.")
else:
    for aloc in alocacoes:
        pessoa_nome = aloc.get('pessoas', {}).get('nome', '-') if aloc.get('pessoas') else '-'
        obra_titulo = aloc.get('obras', {}).get('titulo', '-') if aloc.get('obras') else '-'
        
        periodo_emoji = '☀️' if aloc.get('periodo') == 'INTEGRAL' else '🌤️'
        tipo_emoji = '🏠' if aloc.get('tipo') == 'INTERNO' else '🚗'
        
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.markdown(f"""
                **👷 {pessoa_nome}**  
                🏗️ {obra_titulo}
                """)
            
            with col2:
                st.markdown(f"""
                {periodo_emoji} {aloc.get('periodo', 'INTEGRAL')}  
                {tipo_emoji} {aloc.get('tipo', 'INTERNO')}
                """)
            
            with col3:
                if st.button("🗑️ Remover", key=f"del_aloc_{aloc['id']}"):
                    success, msg = delete_alocacao(aloc['id'])
                    if success:
                        audit_delete('alocacoes', aloc)
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
            
            if aloc.get('observacao'):
                st.markdown(f"📝 {aloc['observacao']}")
            
            st.markdown("---")

# ============================================
# NOVA ALOCAÇÃO
# ============================================

st.markdown("### ➕ Nova Alocação")

# Carrega dados
pessoas = get_pessoas(ativo=True)
obras = get_obras(ativo=True)

if not pessoas:
    st.warning("⚠️ Cadastre profissionais primeiro.")
    st.stop()

if not obras:
    st.warning("⚠️ Cadastre obras primeiro.")
    st.stop()

with st.form("form_nova_alocacao"):
    col1, col2 = st.columns(2)
    
    with col1:
        pessoa_id = st.selectbox(
            "👷 Profissional *",
            options=[p['id'] for p in pessoas],
            format_func=lambda x: next((p['nome'] for p in pessoas if p['id'] == x), '-')
        )
    
    with col2:
        obra_id = st.selectbox(
            "🏗️ Obra *",
            options=[o['id'] for o in obras],
            format_func=lambda x: next((o['titulo'] for o in obras if o['id'] == x), '-')
        )
    
    col1, col2 = st.columns(2)
    
    with col1:
        periodo = st.selectbox("⏰ Período", options=['INTEGRAL', 'MEIO'])
    
    with col2:
        tipo = st.selectbox("📍 Tipo", options=['INTERNO', 'EXTERNO'])
    
    # Orçamento e fase opcionais
    st.markdown("**Opcional: Vincular a Orçamento/Fase**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Orçamentos da obra selecionada
        orcamentos = get_orcamentos_por_obra(obra_id)
        orc_options = [{'id': None, 'label': '-- Nenhum --'}] + [
            {'id': o['id'], 'label': f"v{o['versao']} - {o['status']}"} 
            for o in orcamentos
        ]
        
        orcamento_id = st.selectbox(
            "📋 Orçamento",
            options=[o['id'] for o in orc_options],
            format_func=lambda x: next((o['label'] for o in orc_options if o['id'] == x), '-')
        )
    
    with col2:
        # Fases do orçamento selecionado
        if orcamento_id:
            fases = get_fases_por_orcamento(orcamento_id)
            fase_options = [{'id': None, 'label': '-- Nenhuma --'}] + [
                {'id': f['id'], 'label': f['nome_fase']} 
                for f in fases
            ]
        else:
            fase_options = [{'id': None, 'label': '-- Selecione orçamento --'}]
        
        obra_fase_id = st.selectbox(
            "📑 Fase",
            options=[f['id'] for f in fase_options],
            format_func=lambda x: next((f['label'] for f in fase_options if f['id'] == x), '-')
        )
    
    observacao = st.text_input("📝 Observação")
    
    if st.form_submit_button("✅ Criar Alocação", type="primary"):
        dados = {
            'data': data_selecionada.isoformat(),
            'pessoa_id': pessoa_id,
            'obra_id': obra_id,
            'periodo': periodo,
            'tipo': tipo,
            'observacao': observacao
        }
        
        if orcamento_id:
            dados['orcamento_id'] = orcamento_id
        if obra_fase_id:
            dados['obra_fase_id'] = obra_fase_id
        
        success, msg, nova_aloc = create_alocacao(dados)
        
        if success:
            audit_insert('alocacoes', nova_aloc)
            st.success(f"✅ {msg}")
            st.rerun()
        else:
            st.error(msg)
