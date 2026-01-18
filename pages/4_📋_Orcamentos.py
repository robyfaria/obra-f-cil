"""
Página de Orçamentos - Gestão de fases e serviços + geração de PDF
"""

import streamlit as st
from datetime import date, datetime, timedelta
from utils.auth import require_auth
from utils.db import (
    get_obras, get_orcamentos_por_obra, get_orcamento,
    get_fases_por_orcamento, get_servicos_fase, get_servicos,
    add_servico_fase, update_servico_fase, delete_servico_fase,
    create_servico, create_fase, delete_fase,
    update_orcamento_desconto, update_fase, update_orcamento_validade
)
from utils.auditoria import audit_insert, audit_update, audit_delete
from utils.pdf import gerar_pdf_orcamento
from utils.layout import render_sidebar, render_top_logo

# Requer autenticação
profile = require_auth()
render_sidebar(profile)
render_top_logo()

st.title("📋 Orçamentos")

# Estado
if 'orc_obra_id' not in st.session_state:
    st.session_state['orc_obra_id'] = None
if 'orc_id_selecionado' not in st.session_state:
    st.session_state['orc_id_selecionado'] = None
if 'fase_edit_id' not in st.session_state:
    st.session_state['fase_edit_id'] = None
if 'servico_edit_id' not in st.session_state:
    st.session_state['servico_edit_id'] = None

# ============================================
# SELEÇÃO DE OBRA E ORÇAMENTO
# ============================================

st.markdown("### 1️⃣ Selecione a Obra")

col1, col2 = st.columns([2, 1])
with col1:
    busca_obra = st.text_input(
        "🔍 Buscar",
        placeholder="Nome ou endereço da obra...",
        key="busca_orcamento_obra"
    )
with col2:
    status_obra = st.selectbox(
        "Situação",
        options=[None, 'AGUARDANDO', 'INICIADO', 'PAUSADO', 'CONCLUIDO', 'CANCELADO'],
        format_func=lambda x: 'Todos' if x is None else x.title(),
        key="status_orcamento_obra"
    )

obras = get_obras(busca=busca_obra or "", status=status_obra, ativo=True)

if not obras:
    st.warning("⚠️ Nenhuma obra encontrada com os filtros informados.")
    st.stop()

obra_options = {o['id']: f"{o['titulo']} ({o.get('clientes', {}).get('nome', '-') if o.get('clientes') else '-'})" for o in obras}

obra_selecionada = st.selectbox(
    "Obra",
    options=list(obra_options.keys()),
    format_func=lambda x: obra_options[x]
)

st.session_state['orc_obra_id'] = obra_selecionada

st.markdown("---")

# Lista orçamentos da obra
st.markdown("### 2️⃣ Selecione o Orçamento")

orcamentos = get_orcamentos_por_obra(obra_selecionada)

if not orcamentos:
    st.info("📋 Esta obra não possui orçamentos. Crie um na página de Obras.")
    st.stop()

orc_options = {o['id']: f"v{o['versao']} - {o['status']} (R$ {o.get('valor_total_final', 0):,.2f})" for o in orcamentos}

orc_selecionado = st.selectbox(
    "Orçamento",
    options=list(orc_options.keys()),
    format_func=lambda x: orc_options[x]
)

st.session_state['orc_id_selecionado'] = orc_selecionado

# Carrega dados do orçamento
orcamento = get_orcamento(orc_selecionado)

if not orcamento:
    st.error("Orçamento não encontrado.")
    st.stop()

# Resumo do orçamento
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Versão", orcamento['versao'])
with col2:
    st.metric("Status", orcamento['status'])
with col3:
    st.metric("Valor Total", f"R$ {orcamento.get('valor_total', 0):,.2f}")
with col4:
    st.metric("Valor Final", f"R$ {orcamento.get('valor_total_final', 0):,.2f}")

st.markdown("---")

# ============================================
# FASES E SERVIÇOS
# ============================================

st.markdown("### 3️⃣ Fases e Serviços")

fases = get_fases_por_orcamento(orc_selecionado)

if orcamento['status'] in ['RASCUNHO', 'EMITIDO']:
    with st.form("form_nova_fase"):
        st.markdown("**➕ Nova Fase**")
        col1, col2 = st.columns([3, 1])
        with col1:
            nome_fase = st.text_input("Nome da Fase *")
        with col2:
            ordem_fase = st.number_input(
                "Ordem",
                min_value=1,
                step=1,
                value=int(max([f.get('ordem', 0) for f in fases], default=0) + 1)
            )
        status_fase = st.selectbox(
            "Status",
            options=['PENDENTE', 'EM_ANDAMENTO', 'CONCLUIDA'],
            index=0
        )
        if st.form_submit_button("✅ Adicionar Fase", type="primary"):
            if not nome_fase.strip():
                st.error("⚠️ Informe o nome da fase.")
            else:
                success, msg, nova = create_fase(
                    orcamento['obra_id'],
                    orc_selecionado,
                    nome_fase.strip(),
                    int(ordem_fase),
                    status_fase
                )
                if success:
                    audit_insert('obra_fases', nova)
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

if not fases:
    st.info("📋 Este orçamento ainda não possui fases cadastradas.")

# Catálogo de serviços
servicos_catalogo = get_servicos(ativo=True)

for fase in fases:
    with st.expander(f"📑 {fase['ordem']}. {fase['nome_fase']} - R$ {fase.get('valor_fase', 0):,.2f}", expanded=False):
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown("**Dados da fase**")
        with col2:
            if orcamento['status'] in ['RASCUNHO', 'EMITIDO']:
                if st.button("✏️", key=f"edit_fase_{fase['id']}"):
                    st.session_state['fase_edit_id'] = fase['id']
                    st.rerun()
        with col3:
            if orcamento['status'] in ['RASCUNHO', 'EMITIDO']:
                if st.button("🗑️", key=f"del_fase_{fase['id']}"):
                    success, msg = delete_fase(fase['id'])
                    if success:
                        audit_delete('obra_fases', fase)
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        if st.session_state.get('fase_edit_id') == fase['id'] and orcamento['status'] in ['RASCUNHO', 'EMITIDO']:
            with st.form(f"form_edit_fase_{fase['id']}"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    nome_fase_edit = st.text_input("Nome da Fase", value=fase.get('nome_fase', ''))
                with col2:
                    ordem_edit = st.number_input(
                        "Ordem",
                        min_value=1,
                        step=1,
                        value=int(fase.get('ordem', 1))
                    )
                status_edit = st.selectbox(
                    "Status da Fase",
                    options=['PENDENTE', 'EM_ANDAMENTO', 'CONCLUIDA'],
                    index=['PENDENTE', 'EM_ANDAMENTO', 'CONCLUIDA'].index(fase.get('status', 'PENDENTE'))
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Salvar Fase", type="primary"):
                        antes = {
                            'nome_fase': fase.get('nome_fase'),
                            'ordem': fase.get('ordem'),
                            'status': fase.get('status')
                        }
                        novos_dados = {
                            'nome_fase': nome_fase_edit.strip(),
                            'ordem': int(ordem_edit),
                            'status': status_edit
                        }
                        success, msg = update_fase(fase['id'], novos_dados)
                        if success:
                            audit_update('obra_fases', fase['id'], antes, novos_dados)
                            st.session_state['fase_edit_id'] = None
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                with col2:
                    if st.form_submit_button("❌ Cancelar"):
                        st.session_state['fase_edit_id'] = None
                        st.rerun()
        
        st.markdown("---")
        st.markdown("**Serviços desta fase:**")
        
        # Lista serviços da fase
        servicos_fase = get_servicos_fase(fase['id'])
        servicos_fase = [
            serv for serv in servicos_fase
            if serv.get('servicos', {}).get('ativo', True)
        ]
        
        if servicos_fase:
            for serv in servicos_fase:
                serv_info = serv.get('servicos', {})
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                
                with col1:
                    st.markdown(f"**{serv_info.get('nome', '-')}** ({serv_info.get('unidade', '-')})")
                with col2:
                    st.markdown(f"Qtd: {serv.get('quantidade', 0)}")
                with col3:
                    st.markdown(f"R$ {serv.get('valor_unit', 0):,.2f}")
                with col4:
                    st.markdown(f"**R$ {serv.get('valor_total', 0):,.2f}**")
                with col5:
                    if orcamento['status'] in ['RASCUNHO', 'EMITIDO']:
                        col_edit, col_del = st.columns(2)
                        with col_edit:
                            if st.button("✏️", key=f"edit_serv_{serv['id']}"):
                                st.session_state['servico_edit_id'] = serv['id']
                                st.rerun()
                        with col_del:
                            if st.button("🗑️", key=f"del_serv_{serv['id']}"):
                                success, msg = delete_servico_fase(serv['id'], orc_selecionado)
                                if success:
                                    audit_delete('orcamento_fase_servicos', serv)
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                
                st.markdown("---")
                if st.session_state.get('servico_edit_id') == serv['id'] and orcamento['status'] in ['RASCUNHO', 'EMITIDO']:
                    with st.form(f"form_edit_serv_{serv['id']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            quantidade_edit = st.number_input(
                                "Quantidade",
                                min_value=0.01,
                                value=float(serv.get('quantidade', 1) or 1),
                                step=0.5
                            )
                        with col2:
                            valor_unit_edit = st.number_input(
                                "Valor Unitário (R$)",
                                min_value=0.0,
                                value=float(serv.get('valor_unit', 0) or 0),
                                step=10.0
                            )
                        observacao_edit = st.text_input(
                            "Observação",
                            value=serv.get('observacao', '') or ''
                        )
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Salvar Serviço", type="primary"):
                                antes = {
                                    'quantidade': serv.get('quantidade'),
                                    'valor_unit': serv.get('valor_unit'),
                                    'observacao': serv.get('observacao')
                                }
                                novos_dados = {
                                    'quantidade': quantidade_edit,
                                    'valor_unit': valor_unit_edit,
                                    'observacao': observacao_edit
                                }
                                success, msg = update_servico_fase(
                                    serv['id'],
                                    novos_dados,
                                    orc_selecionado
                                )
                                if success:
                                    audit_update('orcamento_fase_servicos', serv['id'], antes, novos_dados)
                                    st.session_state['servico_edit_id'] = None
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        with col2:
                            if st.form_submit_button("❌ Cancelar"):
                                st.session_state['servico_edit_id'] = None
                                st.rerun()
        else:
            st.info("Nenhum serviço nesta fase.")
        
        # Adicionar novo serviço (só se editável)
        if orcamento['status'] in ['RASCUNHO', 'EMITIDO']:
            st.markdown("**➕ Adicionar Serviço:**")

            with st.expander("🆕 Cadastro rápido de serviço"):
                with st.form(f"form_novo_servico_{fase['id']}"):
                    nome_servico = st.text_input(
                        "Nome do Serviço *",
                        placeholder="Ex: Pintura de parede",
                        key=f"novo_serv_nome_{fase['id']}"
                    )
                    unidade_servico = st.selectbox(
                        "Unidade",
                        options=['UN', 'M2', 'ML', 'H', 'DIA'],
                        key=f"novo_serv_un_{fase['id']}"
                    )

                    if st.form_submit_button("✅ Criar Serviço", type="primary"):
                        if not nome_servico.strip():
                            st.error("⚠️ Informe o nome do serviço!")
                        else:
                            success, msg, novo = create_servico(nome_servico.strip(), unidade_servico)

                            if success:
                                audit_insert('servicos', novo)
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
            
            if servicos_catalogo:
                with st.form(f"form_add_serv_{fase['id']}"):
                    serv_options = {s['id']: f"{s['nome']} ({s['unidade']})" for s in servicos_catalogo}
                    
                    servico_id = st.selectbox(
                        "Serviço",
                        options=list(serv_options.keys()),
                        format_func=lambda x: serv_options[x],
                        key=f"sel_serv_{fase['id']}"
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        quantidade = st.number_input("Quantidade", min_value=0.01, value=1.0, step=0.5, key=f"qtd_{fase['id']}")
                    with col2:
                        valor_unit = st.number_input("Valor Unitário (R$)", min_value=0.0, value=0.0, step=10.0, key=f"val_{fase['id']}")
                    
                    observacao = st.text_input("Observação", key=f"obs_{fase['id']}")
                    
                    if st.form_submit_button("✅ Adicionar Serviço"):
                        success, msg = add_servico_fase(
                            obra_fase_id=fase['id'],
                            servico_id=servico_id,
                            quantidade=quantidade,
                            valor_unit=valor_unit,
                            observacao=observacao,
                            orcamento_id=orc_selecionado
                        )
                        
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
            else:
                st.warning("Cadastre serviços no catálogo primeiro.")

st.markdown("---")

# ============================================
# DESCONTO E VALIDADE
# ============================================

st.markdown("### 4️⃣ Desconto e Validade")

if orcamento['status'] in ['RASCUNHO', 'EMITIDO']:
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        desconto = st.number_input(
            "Valor do Desconto (R$)",
            min_value=0.0,
            value=float(orcamento.get('desconto_valor', 0) or 0),
            step=50.0
        )
    
    with col2:
        st.markdown("")
        st.markdown("")
        if st.button("💾 Aplicar Desconto"):
            success, msg = update_orcamento_desconto(orc_selecionado, desconto)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    with col3:
        valido_ate_atual = orcamento.get('valido_ate')
        if isinstance(valido_ate_atual, str):
            valido_ate_atual = datetime.fromisoformat(valido_ate_atual).date()
        elif isinstance(valido_ate_atual, datetime):
            valido_ate_atual = valido_ate_atual.date()
        elif not valido_ate_atual:
            valido_ate_atual = date.today() + timedelta(days=15)

        validade = st.date_input(
            "Válido até",
            value=valido_ate_atual
        )
        if st.button("💾 Salvar validade"):
            success, msg = update_orcamento_validade(orc_selecionado, validade)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
else:
    st.info(f"Desconto: R$ {orcamento.get('desconto_valor', 0):,.2f} (orçamento não editável)")

st.markdown("---")

# ============================================
# GERAR PDF
# ============================================

st.markdown("### 5️⃣ Gerar PDF")

pdf_state_key = f"pdf_bytes_{orc_selecionado}"

if st.button("📄 Gerar PDF do Orçamento", type="primary"):
    with st.spinner("Gerando PDF..."):
        # Prepara dados
        fases = get_fases_por_orcamento(orc_selecionado)
        servicos_por_fase = {}
        
        for fase in fases:
            servicos_por_fase[fase['id']] = get_servicos_fase(fase['id'])
        
        # Salva no storage e no banco
        valido_ate = orcamento.get('valido_ate')
        if isinstance(valido_ate, str):
            valido_ate = datetime.fromisoformat(valido_ate)
        elif isinstance(valido_ate, date):
            valido_ate = datetime.combine(valido_ate, datetime.min.time())

        if not valido_ate:
            st.error("Defina a validade do orçamento antes de gerar o PDF.")
            st.stop()

        data_emissao = datetime.now()
        orcamento_pdf = dict(orcamento)
        orcamento_pdf['pdf_emitido_em'] = data_emissao.isoformat()
        orcamento_pdf['valido_ate'] = valido_ate.date().isoformat()

        # Gera o PDF
        pdf_bytes = gerar_pdf_orcamento(orcamento_pdf, fases, servicos_por_fase)

        st.session_state[pdf_state_key] = {
            "bytes": pdf_bytes,
            "filename": f"orcamento_{orc_selecionado}.pdf",
        }
        st.success("PDF gerado! Baixe abaixo.")

pdf_payload = st.session_state.get(pdf_state_key)
if pdf_payload:
    st.download_button(
        "⬇️ Baixar PDF",
        data=pdf_payload["bytes"],
        file_name=pdf_payload["filename"],
        mime="application/pdf",
        type="secondary",
    )
