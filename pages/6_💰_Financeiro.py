"""
Página Financeiro - Recebimentos e Pagamentos (ADMIN only)
"""

import streamlit as st
from datetime import date
from utils.auth import require_admin
from utils.db import (
    get_recebimentos, create_recebimento, update_recebimento_status,
    update_recebimento, delete_recebimento,
    get_pagamentos, get_pagamento_itens, create_pagamento, update_pagamento_status,
    update_pagamento, delete_pagamento,
    create_pagamento_item, delete_pagamento_item,
    get_fases_por_orcamento, get_recebimentos_por_orcamento, get_obras, get_orcamentos_por_obra,
    get_apontamentos
)
from utils.auditoria import audit_insert, audit_update, audit_delete
from utils.layout import render_sidebar, render_top_logo

# Requer ADMIN
profile = require_admin()
render_sidebar(profile)
render_top_logo()

st.title("💰 Financeiro")

if 'receb_edit_id' not in st.session_state:
    st.session_state['receb_edit_id'] = None
if 'pag_edit_id' not in st.session_state:
    st.session_state['pag_edit_id'] = None
if 'rec_desconto_rateio' not in st.session_state:
    st.session_state['rec_desconto_rateio'] = {}
if 'rec_valor_fase_id' not in st.session_state:
    st.session_state['rec_valor_fase_id'] = None

tab1, tab2 = st.tabs(["📥 Recebimentos", "📤 Pagamentos"])

# ============================================
# RECEBIMENTOS
# ============================================

with tab1:
    st.markdown("### 📥 Recebimentos por Fase")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        busca_receb = st.text_input(
            "🔍 Buscar",
            placeholder="Obra ou fase...",
            key="busca_receb"
        )
    with col2:
        status_filter = st.selectbox(
            "Situação",
            options=[None, 'ABERTO', 'VENCIDO', 'PAGO', 'CANCELADO'],
            format_func=lambda x: 'Todos' if x is None else x,
            key="filter_receb"
        )
    
    recebimentos = get_recebimentos(status=status_filter)
    if busca_receb:
        busca_lower = busca_receb.lower()
        recebimentos = [
            rec for rec in recebimentos
            if busca_lower in (rec.get('obra_fases', {}).get('nome_fase', '') or '').lower()
            or busca_lower in (rec.get('obra_fases', {}).get('obras', {}).get('titulo', '') or '').lower()
        ]
    
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
                col1, col2, col3, col4 = st.columns([3, 2, 1, 2])
                
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

                with col4:
                    if rec.get('status') in ['ABERTO', 'VENCIDO']:
                        btn_col1, btn_col2, btn_col3 = st.columns(3)
                        with btn_col1:
                            if st.button("✅", key=f"pagar_rec_{rec['id']}"):
                                antes = {'status': rec.get('status')}
                                success, msg = update_recebimento_status(rec['id'], 'PAGO', recebido_em=date.today())
                                if success:
                                    audit_update('recebimentos', rec['id'], antes, {'status': 'PAGO'})
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        with btn_col2:
                            if st.button("✏️", key=f"edit_rec_{rec['id']}"):
                                st.session_state['receb_edit_id'] = rec['id']
                                st.rerun()
                        with btn_col3:
                            if st.button("🗑️", key=f"cancel_rec_{rec['id']}"):
                                antes = {'status': rec.get('status')}
                                success, msg = update_recebimento_status(rec['id'], 'CANCELADO')
                                if success:
                                    audit_update('recebimentos', rec['id'], antes, {'status': 'CANCELADO'})
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                    else:
                        btn_col1, btn_col2, btn_col3 = st.columns(3)
                        with btn_col1:
                            st.markdown("✅" if rec.get('status') == 'PAGO' else "⚪")
                        with btn_col2:
                            if st.button("✏️", key=f"edit_rec_{rec['id']}"):
                                st.session_state['receb_edit_id'] = rec['id']
                                st.rerun()
                        with btn_col3:
                            if st.button("🗑️", key=f"del_rec_{rec['id']}"):
                                success, msg = delete_recebimento(rec['id'])
                                if success:
                                    audit_delete('recebimentos', rec)
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)

                if st.session_state.get('receb_edit_id') == rec['id']:
                    with st.form(f"form_edit_rec_{rec['id']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            valor_edit = st.number_input(
                                "Valor (R$)",
                                min_value=0.0,
                                value=float(rec.get('valor', 0) or 0),
                                step=50.0
                            )
                        with col2:
                            vencimento_edit = st.date_input(
                                "Vencimento",
                                value=date.fromisoformat(rec.get('vencimento'))
                                if rec.get('vencimento') else date.today()
                            )
                        status_edit = st.selectbox(
                            "Status",
                            options=['ABERTO', 'VENCIDO', 'PAGO', 'CANCELADO'],
                            index=['ABERTO', 'VENCIDO', 'PAGO', 'CANCELADO'].index(rec.get('status', 'ABERTO'))
                        )
                        recebido_em_edit = None
                        if status_edit == 'PAGO':
                            recebido_em_edit = st.date_input(
                                "Recebido em",
                                value=date.fromisoformat(rec.get('recebido_em'))
                                if rec.get('recebido_em') else date.today()
                            )
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Salvar", type="primary"):
                                antes = {
                                    'valor': rec.get('valor'),
                                    'vencimento': rec.get('vencimento'),
                                    'status': rec.get('status'),
                                    'recebido_em': rec.get('recebido_em')
                                }
                                novos_dados = {
                                    'valor': valor_edit,
                                    'vencimento': vencimento_edit.isoformat(),
                                    'status': status_edit
                                }
                                if status_edit == 'PAGO':
                                    novos_dados['recebido_em'] = recebido_em_edit.isoformat()
                                success, msg = update_recebimento(rec['id'], novos_dados)
                                if success:
                                    audit_update('recebimentos', rec['id'], antes, novos_dados)
                                    st.session_state['receb_edit_id'] = None
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        with col2:
                            if st.form_submit_button("❌ Cancelar"):
                                st.session_state['receb_edit_id'] = None
                                st.rerun()
                
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
            orc_id = None
            fases = []
            obra_fase_id = None
            valor = 0.0
            vencimento = date.today()
            desconto_orcamento = 0.0

            def atualizar_valor_fase(force: bool = False) -> None:
                fase_id = st.session_state.get("rec_fase")
                if not fase_id:
                    return
                if not force and st.session_state.get('rec_valor_fase_id') == fase_id:
                    return
                fase_info = next((f for f in fases if f['id'] == fase_id), None)
                if not fase_info:
                    return
                valor_fase = float(fase_info.get('valor_fase', 0) or 0)
                desconto_fase = float(
                    st.session_state.get('rec_desconto_rateio', {})
                    .get(orc_id, {})
                    .get(fase_id, 0)
                    or 0
                )
                st.session_state['rec_valor'] = max(0.0, valor_fase - desconto_fase)
                st.session_state['rec_valor_fase_id'] = fase_id
            
            if orcamentos:
                orc_id = st.selectbox(
                    "📋 Orçamento Aprovado",
                    options=[o['id'] for o in orcamentos],
                    format_func=lambda x: f"v{next((o['versao'] for o in orcamentos if o['id'] == x), '-')}",
                    key="rec_orc"
                )

                fases = get_fases_por_orcamento(orc_id)
                desconto_orcamento = float(
                    next((o.get('desconto_valor', 0) for o in orcamentos if o['id'] == orc_id), 0) or 0
                )
                
                if fases:
                    obra_fase_id = st.selectbox(
                        "📑 Fase",
                        options=[f['id'] for f in fases],
                        format_func=lambda x: next((f['nome_fase'] for f in fases if f['id'] == x), '-'),
                        key="rec_fase",
                        on_change=atualizar_valor_fase
                    )

                    atualizar_valor_fase()

                    if desconto_orcamento > 0:
                        st.info(f"Desconto do orçamento: R$ {desconto_orcamento:,.2f}")
                        aplicar_rateio = st.form_submit_button(
                            "💸 Aplicar desconto proporcional às fases restantes",
                            help="Divide o desconto igualmente entre as fases que ainda não têm recebimento."
                        )
                        if aplicar_rateio:
                            recebimentos_existentes = get_recebimentos_por_orcamento(orc_id)
                            fases_com_recebimento = {
                                rec.get('obra_fase_id') for rec in recebimentos_existentes if rec.get('obra_fase_id')
                            }
                            fases_restantes = [f for f in fases if f['id'] not in fases_com_recebimento]
                            if not fases_restantes:
                                st.warning("Todas as fases já possuem recebimento gerado.")
                            else:
                                fases_ordenadas = sorted(fases_restantes, key=lambda f: f.get('ordem', 0))
                                rateio = {}
                                desconto_total = float(desconto_orcamento)
                                desconto_base = round(desconto_total / len(fases_ordenadas), 2)
                                acumulado = 0.0
                                for idx, fase in enumerate(fases_ordenadas):
                                    if idx == len(fases_ordenadas) - 1:
                                        desconto_fase = round(desconto_total - acumulado, 2)
                                    else:
                                        desconto_fase = desconto_base
                                        acumulado += desconto_fase
                                    rateio[fase['id']] = max(0.0, desconto_fase)
                                st.session_state['rec_desconto_rateio'][orc_id] = rateio
                                atualizar_valor_fase(force=True)
                                st.success("Desconto proporcional aplicado às fases restantes.")

                    col1, col2 = st.columns(2)
                    
                    with col1:
                        desconto_aplicado = float(
                            st.session_state.get('rec_desconto_rateio', {})
                            .get(orc_id, {})
                            .get(obra_fase_id, 0)
                            or 0
                        )
                        if desconto_aplicado > 0:
                            st.caption(f"Desconto proporcional aplicado: R$ {desconto_aplicado:,.2f}")
                        valor = st.number_input("💵 Valor (R$)", min_value=0.0, step=100.0, key="rec_valor")
                    
                    with col2:
                        vencimento = st.date_input("📅 Vencimento", value=date.today(), key="rec_venc")
                else:
                    st.warning("Este orçamento não possui fases.")
            else:
                st.warning("Esta obra não possui orçamento aprovado.")

            submit_recebimento = st.form_submit_button(
                "✅ Criar Recebimento",
                type="primary",
                disabled=not (orcamentos and fases)
            )
            if submit_recebimento and orcamentos and fases and obra_fase_id:
                dados = {
                    'obra_fase_id': obra_fase_id,
                    'valor': valor,
                    'vencimento': vencimento.isoformat(),
                    'status': 'ABERTO'
                }

                success, msg, novo = create_recebimento(dados)

                if success:
                    if orc_id in st.session_state.get('rec_desconto_rateio', {}):
                        st.session_state['rec_desconto_rateio'][orc_id].pop(obra_fase_id, None)
                        if not st.session_state['rec_desconto_rateio'][orc_id]:
                            st.session_state['rec_desconto_rateio'].pop(orc_id, None)
                    audit_insert('recebimentos', novo)
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
    else:
        st.warning("Nenhuma obra ativa encontrada.")

# ============================================
# PAGAMENTOS
# ============================================

with tab2:
    st.markdown("### 📤 Pagamentos")

    col1, col2 = st.columns([2, 1])
    with col1:
        busca_pag = st.text_input(
            "🔍 Buscar",
            placeholder="Tipo ou observação...",
            key="busca_pag"
        )
    with col2:
        status_filter_pag = st.selectbox(
            "Situação",
            options=[None, 'PENDENTE', 'PAGO', 'CANCELADO'],
            format_func=lambda x: 'Todos' if x is None else x,
            key="filter_pag"
        )

    pagamentos = get_pagamentos(status=status_filter_pag)
    if busca_pag:
        busca_lower = busca_pag.lower()
        pagamentos = [
            pag for pag in pagamentos
            if busca_lower in (pag.get('tipo', '') or '').lower()
            or busca_lower in (pag.get('observacao', '') or '').lower()
        ]
    
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
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                
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
                with col4:
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    with btn_col1:
                        if pag.get('status') == 'PENDENTE':
                            if st.button("✅", key=f"pago_{pag['id']}"):
                                antes = {'status': pag.get('status')}
                                success, msg = update_pagamento_status(pag['id'], 'PAGO', pago_em=date.today())
                                if success:
                                    audit_update('pagamentos', pag['id'], antes, {'status': 'PAGO'})
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        else:
                            st.markdown("✅" if pag.get('status') == 'PAGO' else "⚪")
                    with btn_col2:
                        if st.button("✏️", key=f"edit_pag_{pag['id']}"):
                            st.session_state['pag_edit_id'] = pag['id']
                            st.rerun()
                    with btn_col3:
                        if pag.get('status') == 'PENDENTE':
                            if st.button("🗑️", key=f"cancel_pag_{pag['id']}"):
                                antes = {'status': pag.get('status')}
                                success, msg = update_pagamento_status(pag['id'], 'CANCELADO')
                                if success:
                                    audit_update('pagamentos', pag['id'], antes, {'status': 'CANCELADO'})
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        else:
                            if st.button("🗑️", key=f"del_pag_{pag['id']}"):
                                success, msg = delete_pagamento(pag['id'])
                                if success:
                                    audit_delete('pagamentos', pag)
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                
                st.markdown("---")
                
                if st.session_state.get('pag_edit_id') == pag['id']:
                    with st.form(f"form_edit_pag_{pag['id']}"):
                        tipo_edit = st.selectbox(
                            "Tipo",
                            options=['SEMANAL', 'EXTRA', 'POR_FASE'],
                            index=['SEMANAL', 'EXTRA', 'POR_FASE'].index(pag.get('tipo', 'SEMANAL'))
                        )
                        col1, col2 = st.columns(2)
                        with col1:
                            ref_ini_edit = st.date_input(
                                "Referência Início",
                                value=date.fromisoformat(pag.get('referencia_inicio'))
                                if pag.get('referencia_inicio') else date.today()
                            )
                        with col2:
                            ref_fim_edit = st.date_input(
                                "Referência Fim",
                                value=date.fromisoformat(pag.get('referencia_fim'))
                                if pag.get('referencia_fim') else date.today()
                            )
                        status_edit = st.selectbox(
                            "Status",
                            options=['PENDENTE', 'PAGO', 'CANCELADO'],
                            index=['PENDENTE', 'PAGO', 'CANCELADO'].index(pag.get('status', 'PENDENTE'))
                        )
                        observacao_edit = st.text_input(
                            "Observação",
                            value=pag.get('observacao', '') or ''
                        )
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Salvar", type="primary"):
                                antes = {
                                    'tipo': pag.get('tipo'),
                                    'referencia_inicio': pag.get('referencia_inicio'),
                                    'referencia_fim': pag.get('referencia_fim'),
                                    'status': pag.get('status'),
                                    'observacao': pag.get('observacao')
                                }
                                novos_dados = {
                                    'tipo': tipo_edit,
                                    'referencia_inicio': ref_ini_edit.isoformat(),
                                    'referencia_fim': ref_fim_edit.isoformat(),
                                    'status': status_edit,
                                    'observacao': observacao_edit
                                }
                                if status_edit == 'PAGO' and not pag.get('pago_em'):
                                    novos_dados['pago_em'] = date.today().isoformat()
                                success, msg = update_pagamento(pag['id'], novos_dados)
                                if success:
                                    audit_update('pagamentos', pag['id'], antes, novos_dados)
                                    st.session_state['pag_edit_id'] = None
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        with col2:
                            if st.form_submit_button("❌ Cancelar"):
                                st.session_state['pag_edit_id'] = None
                                st.rerun()
                
                with st.expander("Detalhes e Itens"):
                    itens = get_pagamento_itens(pag['id'])
                    
                    if itens:
                        for item in itens:
                            apt = item.get('apontamentos', {})
                            pessoa_nome = apt.get('pessoas', {}).get('nome', '-') if apt.get('pessoas') else '-'
                            obra_titulo = apt.get('obras', {}).get('titulo', '-') if apt.get('obras') else '-'
                            fase_nome = apt.get('obra_fases', {}).get('nome_fase', '-') if apt.get('obra_fases') else '-'
                            
                            st.markdown(f"""
                            **{pessoa_nome}** | {obra_titulo} | {fase_nome}  
                            📅 {apt.get('data', '-')} | 💵 R$ {item.get('valor', 0):,.2f}
                            """)
                            
                            if st.button("🗑️", key=f"del_item_{item['id']}"):
                                success, msg = delete_pagamento_item(item['id'])
                                if success:
                                    audit_delete('pagamento_itens', item)
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                            
                            st.markdown("---")
                    else:
                        st.info("Nenhum item cadastrado.")
                    
                    if pag.get('status') == 'PENDENTE':
                        st.markdown("**➕ Adicionar Item**")
                        
                        obras = get_obras(ativo=True)
                        obra_options = {o['id']: o['titulo'] for o in obras}
                        
                        if not obra_options:
                            st.warning("Nenhuma obra ativa encontrada para filtrar apontamentos.")
                            obra_sel = None
                        else:
                            obra_sel = st.selectbox(
                                "Obra",
                                options=list(obra_options.keys()),
                                format_func=lambda x: obra_options[x],
                                key=f"pag_obra_{pag['id']}"
                            )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            data_inicio = st.date_input("De", key=f"pag_ini_{pag['id']}")
                        with col2:
                            data_fim = st.date_input("Até", key=f"pag_fim_{pag['id']}")
                        
                        apontamentos = get_apontamentos(
                            obra_id=obra_sel,
                            data_inicio=data_inicio,
                            data_fim=data_fim
                        ) if obra_sel else []
                        
                        apt_options = {
                            a['id']: f"{a.get('data')} | {a.get('pessoas', {}).get('nome', '-') if a.get('pessoas') else '-'} | {a.get('obra_fases', {}).get('nome_fase', '-') if a.get('obra_fases') else '-'} | R$ {a.get('valor_final', 0):,.2f}"
                            for a in apontamentos
                        }
                        
                        if apt_options:
                            apontamento_id = st.selectbox(
                                "Apontamento",
                                options=list(apt_options.keys()),
                                format_func=lambda x: apt_options[x],
                                key=f"pag_apont_{pag['id']}"
                            )
                            
                            valor_item = st.number_input(
                                "Valor do Item (R$)",
                                min_value=0.0,
                                value=float(next((a.get('valor_final', 0) for a in apontamentos if a['id'] == apontamento_id), 0)),
                                step=10.0,
                                key=f"pag_valor_{pag['id']}"
                            )
                            
                            observacao = st.text_input("Observação", key=f"pag_obs_{pag['id']}")
                            
                            if st.button("✅ Adicionar Item", key=f"btn_add_item_{pag['id']}"):
                                success, msg, novo = create_pagamento_item(pag['id'], apontamento_id, valor_item, observacao)
                                if success:
                                    audit_insert('pagamento_itens', novo)
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        else:
                            st.info("Nenhum apontamento encontrado para os filtros.")
                    
                    if pag.get('status') == 'PENDENTE':
                        st.markdown("---")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅", key=f"pago_exp_{pag['id']}"):
                                antes = {'status': pag.get('status')}
                                success, msg = update_pagamento_status(pag['id'], 'PAGO', pago_em=date.today())
                                if success:
                                    audit_update('pagamentos', pag['id'], antes, {'status': 'PAGO'})
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        with col2:
                            if st.button("🗑️", key=f"cancel_pag_exp_{pag['id']}"):
                                antes = {'status': pag.get('status')}
                                success, msg = update_pagamento_status(pag['id'], 'CANCELADO')
                                if success:
                                    audit_update('pagamentos', pag['id'], antes, {'status': 'CANCELADO'})
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
    
    st.markdown("### ➕ Novo Pagamento")
    
    with st.form("form_novo_pagamento"):
        tipo = st.selectbox("Tipo", options=['SEMANAL', 'EXTRA', 'POR_FASE'])
        
        col1, col2 = st.columns(2)
        with col1:
            referencia_inicio = st.date_input("Referência Início", value=date.today())
        with col2:
            referencia_fim = st.date_input("Referência Fim", value=date.today())
        
        obra_fase_id = None
        if tipo == 'POR_FASE':
            obras = get_obras(ativo=True)
            if obras:
                obra_id = st.selectbox(
                    "Obra",
                    options=[o['id'] for o in obras],
                    format_func=lambda x: next((o['titulo'] for o in obras if o['id'] == x), '-')
                )
                
                orcamentos = [o for o in get_orcamentos_por_obra(obra_id) if o['status'] == 'APROVADO']
                
                if orcamentos:
                    orc_id = st.selectbox(
                        "Orçamento Aprovado",
                        options=[o['id'] for o in orcamentos],
                        format_func=lambda x: f"v{next((o['versao'] for o in orcamentos if o['id'] == x), '-')}"
                    )
                    
                    fases = get_fases_por_orcamento(orc_id)
                    if fases:
                        obra_fase_id = st.selectbox(
                            "Fase",
                            options=[f['id'] for f in fases],
                            format_func=lambda x: next((f['nome_fase'] for f in fases if f['id'] == x), '-')
                        )
                    else:
                        st.warning("Orçamento sem fases cadastradas.")
                else:
                    st.warning("Obra sem orçamento aprovado.")
            else:
                st.warning("Nenhuma obra ativa encontrada.")
        
        observacao = st.text_input("Observação")
        
        if st.form_submit_button("✅ Criar Pagamento", type="primary"):
            dados = {
                'tipo': tipo,
                'referencia_inicio': referencia_inicio.isoformat(),
                'referencia_fim': referencia_fim.isoformat(),
                'status': 'PENDENTE',
                'observacao': observacao
            }
            
            if obra_fase_id:
                dados['obra_fase_id'] = obra_fase_id
            
            success, msg, novo = create_pagamento(dados)
            
            if success:
                audit_insert('pagamentos', novo)
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
