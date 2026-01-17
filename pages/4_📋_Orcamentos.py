"""
Página de Orçamentos - Gestão de fases e serviços + geração de PDF
"""

import streamlit as st
from utils.auth import require_auth
from utils.db import (
    get_obras, get_orcamentos_por_obra, get_orcamento,
    get_fases_por_orcamento, get_servicos_fase, get_servicos,
    add_servico_fase, update_servico_fase, delete_servico_fase,
    create_servico,
    update_orcamento_desconto, update_fase
)
from utils.auditoria import audit_insert, audit_update, audit_delete
from utils.pdf import gerar_pdf_orcamento, salvar_pdf_storage
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
if 'pdf_orcamento_bytes' not in st.session_state:
    st.session_state['pdf_orcamento_bytes'] = None
if 'pdf_orcamento_id' not in st.session_state:
    st.session_state['pdf_orcamento_id'] = None

# ============================================
# SELEÇÃO DE OBRA E ORÇAMENTO
# ============================================

st.markdown("### 1️⃣ Selecione a Obra")

obras = get_obras(ativo=True)

if not obras:
    st.warning("⚠️ Nenhuma obra ativa encontrada.")
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
if st.session_state['pdf_orcamento_id'] != orc_selecionado:
    st.session_state['pdf_orcamento_bytes'] = None
    st.session_state['pdf_orcamento_id'] = orc_selecionado

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

if not fases:
    st.warning("⚠️ Este orçamento não possui fases. Gere as fases padrão na página de Obras.")
    st.stop()

# Catálogo de serviços
servicos_catalogo = get_servicos(ativo=True)

for fase in fases:
    with st.expander(f"📑 {fase['ordem']}. {fase['nome_fase']} - R$ {fase.get('valor_fase', 0):,.2f}", expanded=False):
        
        # Status da fase
        col1, col2 = st.columns([2, 1])
        with col1:
            novo_status = st.selectbox(
                "Status da Fase",
                options=['PENDENTE', 'EM_ANDAMENTO', 'CONCLUIDA'],
                index=['PENDENTE', 'EM_ANDAMENTO', 'CONCLUIDA'].index(fase.get('status', 'PENDENTE')),
                key=f"status_fase_{fase['id']}"
            )
            
            if novo_status != fase.get('status'):
                if st.button("💾 Atualizar Status", key=f"btn_status_{fase['id']}"):
                    success, msg = update_fase(fase['id'], {'status': novo_status})
                    if success:
                        st.success(msg)
                        st.rerun()
        
        st.markdown("---")
        st.markdown("**Serviços desta fase:**")
        
        # Lista serviços da fase
        servicos_fase = get_servicos_fase(fase['id'])
        
        if servicos_fase:
            for serv in servicos_fase:
                serv_info = serv.get('servicos', {})
                
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.markdown(f"**{serv_info.get('nome', '-')}** ({serv_info.get('unidade', '-')})")
                with col2:
                    st.markdown(f"Qtd: {serv.get('quantidade', 0)}")
                with col3:
                    st.markdown(f"R$ {serv.get('valor_unit', 0):,.2f}")
                with col4:
                    st.markdown(f"**R$ {serv.get('valor_total', 0):,.2f}**")
                
                # Botão de remover (só se orçamento editável)
                if orcamento['status'] in ['RASCUNHO', 'EMITIDO']:
                    if st.button("🗑️ Remover", key=f"del_serv_{serv['id']}"):
                        success, msg = delete_servico_fase(serv['id'], orc_selecionado)
                        if success:
                            audit_delete('orcamento_fase_servicos', serv)
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                
                st.markdown("---")
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
# DESCONTO
# ============================================

st.markdown("### 4️⃣ Desconto")

if orcamento['status'] in ['RASCUNHO', 'EMITIDO']:
    col1, col2 = st.columns([2, 1])
    
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
else:
    st.info(f"Desconto: R$ {orcamento.get('desconto_valor', 0):,.2f} (orçamento não editável)")

st.markdown("---")

# ============================================
# GERAR PDF
# ============================================

st.markdown("### 5️⃣ Gerar PDF")

if st.button("📄 Gerar PDF do Orçamento", type="primary"):
    
    with st.spinner("Gerando PDF..."):
        # Prepara dados
        fases = get_fases_por_orcamento(orc_selecionado)
        servicos_por_fase = {}
        
        for fase in fases:
            servicos_por_fase[fase['id']] = get_servicos_fase(fase['id'])
        
        # Gera o PDF
        pdf_bytes = gerar_pdf_orcamento(orcamento, fases, servicos_por_fase)
        st.session_state['pdf_orcamento_bytes'] = pdf_bytes
        st.session_state['pdf_orcamento_id'] = orc_selecionado
        
        # Oferece download
        obra_titulo = orcamento.get('obras', {}).get('titulo', 'obra')
        
        st.download_button(
            label="⬇️ Baixar PDF",
            data=pdf_bytes,
            file_name=f"orcamento_v{orcamento['versao']}_{obra_titulo}.pdf",
            mime="application/pdf"
        )
        
        st.info("💡 Use o botão abaixo para salvar o PDF no Supabase Storage.")

if st.session_state['pdf_orcamento_bytes']:
    if st.button("☁️ Salvar PDF no servidor"):
        obra_titulo = orcamento.get('obras', {}).get('titulo', 'obra')
        url, error = salvar_pdf_storage(
            st.session_state['pdf_orcamento_bytes'],
            orc_selecionado,
            obra_titulo,
        )
        if url:
            st.success("PDF salvo no servidor!")
            st.markdown(f"[🔗 Abrir PDF]({url})")
        else:
            error_msg = f" (Detalhes: {error})" if error else ""
            st.error(f"Não foi possível salvar o PDF no servidor.{error_msg}")
