"""
Página Financeiro - Recebimentos e Pagamentos (ADMIN only)
"""

import streamlit as st
from datetime import date
from utils.auth import require_admin
from utils.db import (
    get_recebimentos, create_recebimento,
    get_pagamentos, get_fases_por_orcamento,
    get_obras, get_orcamentos_por_obra
)
from utils.auditoria import audit_insert

# Requer ADMIN
profile = require_admin()

st.title("💰 Financeiro")

tab1, tab2 = st.tabs(["📥 Recebimentos", "📤 Pagamentos"])

# ============================================
# RECEBIMENTOS
# ============================================

with tab1:
    st.markdown("### 📥 Recebimentos por Fase")
    
    # Filtro de status
    status_filter = st.selectbox(
        "Filtrar por Status",
        options=['', 'ABERTO', 'VENCIDO', 'PAGO', 'CANCELADO'],
        format_func=lambda x: 'Todos' if x == '' else x,
        key="filter_receb"
    )
    
    recebimentos = get_recebimentos(status=status_filter if status_filter else None)
    
    if not recebimentos:
        st.info("📋 Nenhum recebimento encontrado.")
    else:
        for rec in recebimentos:
            fase_info = rec.get('obra_fases', {})
            obra_info = fase_info.get('obras', {}) if fase_info else {}
            
            status_emoji = {
                'ABERTO': '🟡',
                'VENCIDO': '🔴',
                'PAGO': '🟢',
                'CANCELADO': '⚫'
            }.get(rec.get('status', ''), '⚪')
            
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    st.markdown(f"""
                    **{obra_info.get('titulo', '-')}**  
                    📑 Fase: {fase_info.get('nome_fase', '-')}
                    """)
                
                with col2:
                    st.markdown(f"""
                    💵 **R$ {rec.get('valor', 0):,.2f}**  
                    📅 Venc: {rec.get('vencimento', '-')}
                    """)
                
                with col3:
                    st.markdown(f"{status_emoji} **{rec.get('status', '-')}**")
                
                st.markdown("---")
    
    # Novo recebimento
    st.markdown("### ➕ Novo Recebimento")
    
    obras = get_obras(ativo=True)
    
    if obras:
        with st.form("form_novo_recebimento"):
            obra_id = st.selectbox(
                "🏗️ Obra",
                options=[o['id'] for o in obras],
                format_func=lambda x: next((o['titulo'] for o in obras if o['id'] == x), '-'),
                key="rec_obra"
            )
            
            # Busca orçamentos aprovados
            orcamentos = [o for o in get_orcamentos_por_obra(obra_id) if o['status'] == 'APROVADO']
            
            if orcamentos:
                orc_id = st.selectbox(
                    "📋 Orçamento Aprovado",
                    options=[o['id'] for o in orcamentos],
                    format_func=lambda x: f"v{next((o['versao'] for o in orcamentos if o['id'] == x), '-')}",
                    key="rec_orc"
                )
                
                fases = get_fases_por_orcamento(orc_id)
                
                if fases:
                    obra_fase_id = st.selectbox(
                        "📑 Fase",
                        options=[f['id'] for f in fases],
                        format_func=lambda x: next((f['nome_fase'] for f in fases if f['id'] == x), '-'),
                        key="rec_fase"
                    )
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        valor = st.number_input("💵 Valor (R$)", min_value=0.0, step=100.0, key="rec_valor")
                    
                    with col2:
                        vencimento = st.date_input("📅 Vencimento", value=date.today(), key="rec_venc")
                    
                    if st.form_submit_button("✅ Criar Recebimento", type="primary"):
                        dados = {
                            'obra_fase_id': obra_fase_id,
                            'valor': valor,
                            'vencimento': vencimento.isoformat(),
                            'status': 'ABERTO'
                        }
                        
                        success, msg, novo = create_recebimento(dados)
                        
                        if success:
                            audit_insert('recebimentos', novo)
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    st.warning("Este orçamento não possui fases.")
            else:
                st.warning("Esta obra não possui orçamento aprovado.")
    else:
        st.warning("Nenhuma obra ativa encontrada.")

# ============================================
# PAGAMENTOS
# ============================================

with tab2:
    st.markdown("### 📤 Pagamentos")
    
    pagamentos = get_pagamentos()
    
    if not pagamentos:
        st.info("📋 Nenhum pagamento encontrado.")
    else:
        for pag in pagamentos:
            status_emoji = {
                'PENDENTE': '🟡',
                'PAGO': '🟢',
                'CANCELADO': '⚫'
            }.get(pag.get('status', ''), '⚪')
            
            tipo_emoji = {
                'SEMANAL': '📅',
                'EXTRA': '⭐',
                'POR_FASE': '📑'
            }.get(pag.get('tipo', ''), '💵')
            
            with st.container():
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.markdown(f"""
                    {tipo_emoji} **{pag.get('tipo', '-')}**  
                    📅 Ref: {pag.get('referencia_inicio', '-')} a {pag.get('referencia_fim', '-')}
                    """)
                
                with col2:
                    st.markdown(f"""
                    💵 **R$ {pag.get('valor_total', 0):,.2f}**
                    """)
                
                with col3:
                    st.markdown(f"{status_emoji} **{pag.get('status', '-')}**")
                
                st.markdown("---")
    
    st.markdown("### ➕ Novo Pagamento")
    st.info("💡 A criação de pagamentos com itens detalhados será implementada em breve.")
