"""
Página de Obras - Listagem, CRUD e detalhes com abas
"""

import streamlit as st
from datetime import date, datetime, timedelta
from utils.auth import require_auth
from utils.layout import render_sidebar, render_top_logo
from utils.db import (
    get_obras, get_obra, create_obra, update_obra,
    get_clientes, get_orcamentos_por_obra, get_fases_por_orcamento,
    get_apontamentos, get_servicos_fase,
    get_pessoas, create_apontamento, update_apontamento, delete_apontamento,
    get_orcamento, get_servicos, add_servico_fase, update_servico_fase,
    delete_servico_fase, create_servico, create_fase, delete_fase, update_fase,
    update_servico,
    update_orcamento_desconto, update_orcamento_validade,
    get_recebimentos_por_orcamento, create_recebimento,
    get_alocacoes_dia, create_alocacao, delete_alocacao, update_alocacao_confirmada,
    update_alocacao
)
from utils.auditoria import audit_insert, audit_update, audit_delete
from utils.pdf import gerar_pdf_orcamento

# Requer autenticação
profile = require_auth()
render_sidebar(profile)
render_top_logo()

st.title("🏠 Obras")

# Estado da página
if 'obra_view' not in st.session_state:
    st.session_state['obra_view'] = 'lista'
if 'obra_id' not in st.session_state:
    st.session_state['obra_id'] = None
if 'obra_orc_manage_id' not in st.session_state:
    st.session_state['obra_orc_manage_id'] = None
if 'obra_fase_edit_id' not in st.session_state:
    st.session_state['obra_fase_edit_id'] = None
if 'obra_servico_edit_id' not in st.session_state:
    st.session_state['obra_servico_edit_id'] = None
if 'obra_agenda_date' not in st.session_state:
    st.session_state['obra_agenda_date'] = date.today()
elif isinstance(st.session_state['obra_agenda_date'], str):
    st.session_state['obra_agenda_date'] = date.fromisoformat(st.session_state['obra_agenda_date'])
if 'obra_aloc_edit_id' not in st.session_state:
    st.session_state['obra_aloc_edit_id'] = None
if 'obra_nova_orcamento_id' not in st.session_state:
    st.session_state['obra_nova_orcamento_id'] = None
if 'obra_nova_fase_id' not in st.session_state:
    st.session_state['obra_nova_fase_id'] = None

# Função para voltar à lista
def voltar_lista():
    st.session_state['obra_view'] = 'lista'
    st.session_state['obra_id'] = None

# ============================================
# LISTA DE OBRAS
# ============================================

if st.session_state['obra_view'] == 'lista':
    
    # Botão de nova obra
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Nova Obra", type="primary", use_container_width=True):
            st.session_state['obra_view'] = 'nova'
            st.rerun()
    
    st.markdown("---")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        busca = st.text_input("🔍 Buscar", placeholder="Título ou endereço...")
    
    with col2:
        status_filter = st.selectbox(
            "Status",
            options=['', 'AGUARDANDO', 'INICIADO', 'PAUSADO', 'CONCLUIDO', 'CANCELADO'],
            format_func=lambda x: 'Todos' if x == '' else x
        )
    
    with col3:
        ativo_filter = st.selectbox(
            "Situação",
            options=[None, True, False],
            format_func=lambda x: 'Todas' if x is None else ('Ativas' if x else 'Inativas')
        )
    
    # Lista de obras
    obras = get_obras(
        busca=busca,
        status=status_filter if status_filter else None,
        ativo=ativo_filter
    )
    
    if not obras:
        st.info("📋 Nenhuma obra encontrada.")
    else:
        st.markdown(f"**{len(obras)} obra(s) encontrada(s)**")
        
        for obra in obras:
            cliente_nome = obra.get('clientes', {}).get('nome', '-') if obra.get('clientes') else '-'
            
            status_emoji = {
                'AGUARDANDO': '⏳',
                'INICIADO': '🚧',
                'PAUSADO': '⏸️',
                'CONCLUIDO': '✅',
                'CANCELADO': '❌'
            }.get(obra['status'], '📋')
            
            with st.container():
                col1, col2, col3 = st.columns([4, 2, 2])
                
                with col1:
                    st.markdown(f"""
                    **{obra['titulo']}**  
                    👤 {cliente_nome} | 📍 {obra.get('endereco_obra', '-')}
                    """)
                
                with col2:
                    st.markdown(f"{status_emoji} **{obra['status']}**")
                    if not obra.get('ativo', True):
                        st.markdown("🔴 Inativa")
                
                with col3:
                    if st.button("👁️ Ver Detalhes", key=f"ver_{obra['id']}", use_container_width=True):
                        st.session_state['obra_view'] = 'detalhe'
                        st.session_state['obra_id'] = obra['id']
                        st.rerun()
                
                st.markdown("---")


# ============================================
# NOVA OBRA
# ============================================

elif st.session_state['obra_view'] == 'nova':
    
    st.markdown("### ➕ Nova Obra")
    
    if st.button("⬅️ Voltar"):
        voltar_lista()
        st.rerun()
    
    st.markdown("---")
    
    # Busca clientes para o select
    clientes = get_clientes(ativo=True)
    
    if not clientes:
        st.warning("⚠️ Cadastre pelo menos um cliente antes de criar uma obra.")
    else:
        with st.form("form_nova_obra"):
            cliente_id = st.selectbox(
                "👤 Cliente *",
                options=[c['id'] for c in clientes],
                format_func=lambda x: next((c['nome'] for c in clientes if c['id'] == x), '-')
            )
            
            titulo = st.text_input("📝 Título da Obra *", placeholder="Ex: Pintura completa residencial")
            
            endereco = st.text_input("📍 Endereço da Obra", placeholder="Endereço onde será realizada")
            
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("✅ Criar Obra", type="primary", use_container_width=True)
            with col2:
                if st.form_submit_button("❌ Cancelar", use_container_width=True):
                    voltar_lista()
                    st.rerun()
            
            if submitted:
                if not titulo:
                    st.error("⚠️ Informe o título da obra!")
                else:
                    success, msg, nova_obra = create_obra({
                        'cliente_id': cliente_id,
                        'titulo': titulo,
                        'endereco_obra': endereco
                    })
                    
                    if success:
                        audit_insert('obras', nova_obra)
                        st.success(f"✅ {msg}")
                        st.session_state['obra_view'] = 'detalhe'
                        st.session_state['obra_id'] = nova_obra['id']
                        st.rerun()
                    else:
                        st.error(msg)


# ============================================
# DETALHE DA OBRA (COM ABAS)
# ============================================

elif st.session_state['obra_view'] == 'detalhe':
    
    obra_id = st.session_state['obra_id']
    obra = get_obra(obra_id)
    
    if not obra:
        st.error("Obra não encontrada.")
        voltar_lista()
        st.rerun()
    
    # Cabeçalho
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"## {obra['titulo']}")
    with col2:
        if st.button("⬅️ Voltar à Lista"):
            voltar_lista()
            st.rerun()
    
    cliente = obra.get('clientes', {})
    st.markdown(f"👤 **Cliente:** {cliente.get('nome', '-')} | 📍 **Local:** {obra.get('endereco_obra', '-')}")
    
    # Status badges
    status_colors = {
        'AGUARDANDO': 'orange',
        'INICIADO': 'blue',
        'PAUSADO': 'gray',
        'CONCLUIDO': 'green',
        'CANCELADO': 'red'
    }
    st.markdown(f"**Status:** :{status_colors.get(obra['status'], 'gray')}[{obra['status']}]")
    
    st.markdown("---")
    
    # Abas
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Resumo",
        "💰 Orçamentos", 
        "📑 Fases",
        "📅 Agenda",
        "⏱️ Apontamentos"
    ])
    
    # ---- ABA RESUMO ----
    with tab1:
        st.markdown("### Editar Obra")
        
        with st.form("form_editar_obra"):
            # Busca clientes
            clientes = get_clientes(ativo=True)
            
            cliente_id = st.selectbox(
                "👤 Cliente",
                options=[c['id'] for c in clientes],
                index=next((i for i, c in enumerate(clientes) if c['id'] == obra['cliente_id']), 0),
                format_func=lambda x: next((c['nome'] for c in clientes if c['id'] == x), '-')
            )
            
            titulo = st.text_input("📝 Título", value=obra['titulo'])
            endereco = st.text_input("📍 Endereço", value=obra.get('endereco_obra', '') or '')
            
            status = st.selectbox(
                "Status",
                options=['AGUARDANDO', 'INICIADO', 'PAUSADO', 'CONCLUIDO', 'CANCELADO'],
                index=['AGUARDANDO', 'INICIADO', 'PAUSADO', 'CONCLUIDO', 'CANCELADO'].index(obra['status'])
            )
            
            ativo = st.checkbox("Obra Ativa", value=obra.get('ativo', True))
            
            if st.form_submit_button("💾 Salvar Alterações", type="primary"):
                antes = {
                    'cliente_id': obra['cliente_id'],
                    'titulo': obra['titulo'],
                    'endereco_obra': obra.get('endereco_obra'),
                    'status': obra['status'],
                    'ativo': obra.get('ativo')
                }
                
                novos_dados = {
                    'cliente_id': cliente_id,
                    'titulo': titulo,
                    'endereco_obra': endereco,
                    'status': status,
                    'ativo': ativo
                }
                
                success, msg = update_obra(obra_id, novos_dados)
                
                if success:
                    audit_update('obras', obra_id, antes, novos_dados)
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(msg)
    
    # ---- ABA ORÇAMENTOS ----
    with tab2:
        st.markdown("### 💰 Orçamentos desta Obra")
        
        # Botão para novo orçamento
        if st.button("➕ Novo Orçamento", type="primary"):
            from utils.db import create_orcamento
            
            success, msg, novo_orc = create_orcamento(obra_id)
            
            if success:
                audit_insert('orcamentos', novo_orc)
                st.success(f"✅ {msg}")
                st.rerun()
            else:
                st.error(msg)
        
        st.markdown("---")
        
        orcamentos = get_orcamentos_por_obra(obra_id)
        
        if not orcamentos:
            st.info("📋 Nenhum orçamento cadastrado. Clique em 'Novo Orçamento' para começar.")
        else:
            for orc in orcamentos:
                status_emoji = {
                    'RASCUNHO': '📝',
                    'EMITIDO': '📤',
                    'APROVADO': '✅',
                    'REPROVADO': '❌',
                    'CANCELADO': '🚫'
                }.get(orc['status'], '📋')
                
                with st.expander(f"{status_emoji} Versão {orc['versao']} - {orc['status']}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Valor Total", f"R$ {orc.get('valor_total', 0):,.2f}")
                    with col2:
                        st.metric("Desconto", f"R$ {orc.get('desconto_valor', 0) or 0:,.2f}")
                    with col3:
                        st.metric("Valor Final", f"R$ {orc.get('valor_total_final', 0):,.2f}")
                    
                    # Armazena o orçamento selecionado para a aba de fases
                    if st.button(f"📑 Ver Fases", key=f"fases_{orc['id']}"):
                        st.session_state['orcamento_selecionado'] = orc['id']
                        st.session_state['obra_orc_manage_id'] = orc['id']
                        st.rerun()
                    
                    # Ações baseadas no status
                    st.markdown("**Ações:**")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if orc['status'] == 'RASCUNHO':
                            if st.button("📤 Emitir", key=f"emitir_{orc['id']}"):
                                from utils.db import update_orcamento_status
                                from utils.auditoria import audit_status_change
                                
                                success, msg = update_orcamento_status(orc['id'], 'EMITIDO')
                                if success:
                                    audit_status_change('orcamentos', orc['id'], 'RASCUNHO', 'EMITIDO')
                                    st.success(msg)
                                    st.rerun()
                    
                    with col2:
                        if orc['status'] in ['RASCUNHO', 'EMITIDO']:
                            if st.button("✅ Aprovar", key=f"aprovar_{orc['id']}"):
                                from utils.db import update_orcamento_status
                                from utils.auditoria import audit_status_change
                                
                                success, msg = update_orcamento_status(orc['id'], 'APROVADO')
                                if success:
                                    audit_status_change('orcamentos', orc['id'], orc['status'], 'APROVADO')
                                    st.success(msg)
                                    st.rerun()
                    
                    with col3:
                        if orc['status'] == 'EMITIDO':
                            if st.button("❌ Reprovar", key=f"reprovar_{orc['id']}"):
                                from utils.db import update_orcamento_status
                                from utils.auditoria import audit_status_change
                                
                                success, msg = update_orcamento_status(orc['id'], 'REPROVADO')
                                if success:
                                    audit_status_change('orcamentos', orc['id'], 'EMITIDO', 'REPROVADO')
                                    st.success(msg)
                                    st.rerun()
                    
                    with col4:
                        if orc['status'] not in ['CANCELADO', 'CONCLUIDO']:
                            if st.button("🚫 Cancelar", key=f"cancelar_{orc['id']}"):
                                from utils.db import update_orcamento_status
                                from utils.auditoria import audit_status_change
                                
                                success, msg = update_orcamento_status(orc['id'], 'CANCELADO')
                                if success:
                                    audit_status_change('orcamentos', orc['id'], orc['status'], 'CANCELADO')
                                    fases_orcamento = get_fases_por_orcamento(orc['id'])
                                    for fase in fases_orcamento:
                                        if fase.get('status') != 'CANCELADO':
                                            antes = {'status': fase.get('status')}
                                            fase_success, fase_msg = update_fase(
                                                fase['id'],
                                                {'status': 'CANCELADO'}
                                            )
                                            if fase_success:
                                                audit_update(
                                                    'obra_fases',
                                                    fase['id'],
                                                    antes,
                                                    {'status': 'CANCELADO'}
                                                )
                                            else:
                                                st.error(
                                                    f"Erro ao cancelar fase {fase.get('nome_fase', '-')}: {fase_msg}"
                                                )
                                    st.success(msg)
                                    st.rerun()

            st.markdown("---")
            st.markdown("### 🛠️ Gerenciar Orçamento")

            if not st.session_state.get('obra_orc_manage_id'):
                st.session_state['obra_orc_manage_id'] = orcamentos[0]['id']

            orc_manage_id = st.selectbox(
                "Orçamento",
                options=[o['id'] for o in orcamentos],
                format_func=lambda x: f"v{next((o['versao'] for o in orcamentos if o['id'] == x), '-')} - {next((o['status'] for o in orcamentos if o['id'] == x), '-')}",
                key="obra_orc_manage_id"
            )

            orcamento = get_orcamento(orc_manage_id)
            if not orcamento:
                st.error("Orçamento não encontrado.")
                st.stop()

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
            st.markdown("#### 📑 Fases e Serviços")

            fases = get_fases_por_orcamento(orc_manage_id)

            if orcamento['status'] in ['RASCUNHO', 'EMITIDO']:
                with st.form("form_nova_fase_obra"):
                    st.markdown("**➕ Nova Fase**")
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        nome_fase = st.text_input("Nome da Fase *", key="obra_nome_fase")
                    with col2:
                        ordem_fase = st.number_input(
                            "Ordem",
                            min_value=1,
                            step=1,
                            value=int(max([f.get('ordem', 0) for f in fases], default=0) + 1),
                            key="obra_ordem_fase"
                        )
                    status_fase = st.selectbox(
                        "Status",
                        options=['PENDENTE', 'EM_ANDAMENTO', 'CONCLUIDA'],
                        index=0,
                        key="obra_status_fase"
                    )
                    if st.form_submit_button("✅ Adicionar Fase", type="primary"):
                        if not nome_fase.strip():
                            st.error("⚠️ Informe o nome da fase.")
                        else:
                            success, msg, nova = create_fase(
                                orcamento['obra_id'],
                                orc_manage_id,
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

            servicos_catalogo = get_servicos(ativo=True)

            for fase in fases:
                with st.expander(
                    f"📑 {fase['ordem']}. {fase['nome_fase']} - R$ {fase.get('valor_fase', 0):,.2f}",
                    expanded=False
                ):
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    with col1:
                        st.markdown("**Dados da fase**")
                    with col2:
                        if orcamento['status'] in ['RASCUNHO', 'EMITIDO']:
                            if st.button("✏️", key=f"obra_edit_fase_{fase['id']}"):
                                st.session_state['obra_fase_edit_id'] = fase['id']
                                st.rerun()
                    with col3:
                        if orcamento['status'] in ['RASCUNHO', 'EMITIDO']:
                            if st.button("🗑️", key=f"obra_del_fase_{fase['id']}"):
                                success, msg = delete_fase(fase['id'])
                                if success:
                                    audit_delete('obra_fases', fase)
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                    with col4:
                        if fase.get('status') != 'CANCELADO' and orcamento['status'] != 'CANCELADO':
                            if st.button("🚫", key=f"obra_cancel_fase_{fase['id']}"):
                                antes = {
                                    'status': fase.get('status')
                                }
                                novos_dados = {'status': 'CANCELADO'}
                                success, msg = update_fase(fase['id'], novos_dados)
                                if success:
                                    audit_update('obra_fases', fase['id'], antes, novos_dados)
                                    st.success("Fase cancelada!")
                                    st.rerun()
                                else:
                                    st.error(msg)

                    if st.session_state.get('obra_fase_edit_id') == fase['id'] and orcamento['status'] in ['RASCUNHO', 'EMITIDO']:
                        with st.form(f"form_edit_fase_obra_{fase['id']}"):
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
                                options=['PENDENTE', 'EM_ANDAMENTO', 'CONCLUIDA', 'CANCELADO'],
                                index=['PENDENTE', 'EM_ANDAMENTO', 'CONCLUIDA', 'CANCELADO'].index(
                                    fase.get('status', 'PENDENTE')
                                )
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
                                        st.session_state['obra_fase_edit_id'] = None
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            with col2:
                                if st.form_submit_button("❌ Cancelar"):
                                    st.session_state['obra_fase_edit_id'] = None
                                    st.rerun()

                    st.markdown("---")
                    st.markdown("**Serviços desta fase:**")

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
                                        if st.button("✏️", key=f"obra_edit_serv_{serv['id']}"):
                                            st.session_state['obra_servico_edit_id'] = serv['id']
                                            st.rerun()
                                    with col_del:
                                        if st.button("🗑️", key=f"obra_del_serv_{serv['id']}"):
                                            success, msg = delete_servico_fase(serv['id'], orc_manage_id)
                                            if success:
                                                audit_delete('orcamento_fase_servicos', serv)
                                                st.success(msg)
                                                st.rerun()
                                            else:
                                                st.error(msg)

                            st.markdown("---")
                            if st.session_state.get('obra_servico_edit_id') == serv['id'] and orcamento['status'] in ['RASCUNHO', 'EMITIDO']:
                                with st.form(f"form_edit_serv_obra_{serv['id']}"):
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        nome_servico_edit = st.text_input(
                                            "Nome do Serviço",
                                            value=serv_info.get('nome', '') or ''
                                        )
                                    with col2:
                                        unidade_opcoes = ['UN', 'M2', 'ML', 'H', 'DIA']
                                        unidade_atual = serv_info.get('unidade', 'UN') or 'UN'
                                        if unidade_atual not in unidade_opcoes:
                                            unidade_atual = 'UN'
                                        unidade_servico_edit = st.selectbox(
                                            "Unidade",
                                            options=unidade_opcoes,
                                            index=unidade_opcoes.index(unidade_atual)
                                        )
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
                                            servico_id = serv.get('servico_id')
                                            servico_antes = {
                                                'nome': serv_info.get('nome'),
                                                'unidade': serv_info.get('unidade')
                                            }
                                            servico_novos = {
                                                'nome': nome_servico_edit.strip(),
                                                'unidade': unidade_servico_edit
                                            }
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
                                                orc_manage_id
                                            )
                                            if success:
                                                if servico_id and servico_novos != servico_antes:
                                                    serv_success, serv_msg, atualizado = update_servico(
                                                        servico_id,
                                                        servico_novos
                                                    )
                                                    if serv_success:
                                                        audit_update(
                                                            'servicos',
                                                            servico_id,
                                                            servico_antes,
                                                            servico_novos
                                                        )
                                                    else:
                                                        st.error(serv_msg)
                                                        st.stop()
                                                audit_update('orcamento_fase_servicos', serv['id'], antes, novos_dados)
                                                st.session_state['obra_servico_edit_id'] = None
                                                st.success(msg)
                                                st.rerun()
                                            else:
                                                st.error(msg)
                                    with col2:
                                        if st.form_submit_button("❌ Cancelar"):
                                            st.session_state['obra_servico_edit_id'] = None
                                            st.rerun()
                    else:
                        st.info("Nenhum serviço nesta fase.")

                    if orcamento['status'] in ['RASCUNHO', 'EMITIDO']:
                        st.markdown("**➕ Adicionar Serviço:**")

                        with st.expander("🆕 Cadastro rápido de serviço"):
                            with st.form(f"form_novo_servico_obra_{fase['id']}"):
                                nome_servico = st.text_input(
                                    "Nome do Serviço *",
                                    placeholder="Ex: Pintura de parede",
                                    key=f"obra_novo_serv_nome_{fase['id']}"
                                )
                                unidade_servico = st.selectbox(
                                    "Unidade",
                                    options=['UN', 'M2', 'ML', 'H', 'DIA'],
                                    key=f"obra_novo_serv_un_{fase['id']}"
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
                            with st.form(f"form_add_serv_obra_{fase['id']}"):
                                serv_options = {s['id']: f"{s['nome']} ({s['unidade']})" for s in servicos_catalogo}

                                servico_id = st.selectbox(
                                    "Serviço",
                                    options=list(serv_options.keys()),
                                    format_func=lambda x: serv_options[x],
                                    key=f"obra_sel_serv_{fase['id']}"
                                )

                                col1, col2 = st.columns(2)
                                with col1:
                                    quantidade = st.number_input(
                                        "Quantidade",
                                        min_value=0.01,
                                        value=1.0,
                                        step=0.5,
                                        key=f"obra_qtd_{fase['id']}"
                                    )
                                with col2:
                                    valor_unit = st.number_input(
                                        "Valor Unitário (R$)",
                                        min_value=0.0,
                                        value=0.0,
                                        step=10.0,
                                        key=f"obra_val_{fase['id']}"
                                    )

                                observacao = st.text_input("Observação", key=f"obra_obs_{fase['id']}")

                                if st.form_submit_button("✅ Adicionar Serviço"):
                                    success, msg = add_servico_fase(
                                        obra_fase_id=fase['id'],
                                        servico_id=servico_id,
                                        quantidade=quantidade,
                                        valor_unit=valor_unit,
                                        observacao=observacao,
                                        orcamento_id=orc_manage_id
                                    )

                                    if success:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                        else:
                            st.warning("Cadastre serviços no catálogo primeiro.")

            st.markdown("---")
            st.markdown("#### 💸 Desconto e Validade")

            if orcamento['status'] in ['RASCUNHO', 'EMITIDO']:
                col1, col2, col3 = st.columns([2, 1, 2])

                with col1:
                    desconto = st.number_input(
                        "Valor do Desconto (R$)",
                        min_value=0.0,
                        value=float(orcamento.get('desconto_valor', 0) or 0),
                        step=50.0,
                        key="obra_orc_desconto"
                    )

                with col2:
                    st.markdown("")
                    st.markdown("")
                    if st.button("💾 Aplicar Desconto", key="obra_orc_apply_desconto"):
                        success, msg = update_orcamento_desconto(orc_manage_id, desconto)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

                with col3:
                    valido_ate_atual = orcamento.get('valido_ate')
                    if isinstance(valido_ate_atual, str):
                        try:
                            valido_ate_atual = date.fromisoformat(valido_ate_atual)
                        except ValueError:
                            valido_ate_atual = datetime.fromisoformat(valido_ate_atual).date()
                    elif isinstance(valido_ate_atual, datetime):
                        valido_ate_atual = valido_ate_atual.date()
                    elif not valido_ate_atual:
                        valido_ate_atual = date.today() + timedelta(days=15)

                    validade = st.date_input(
                        "Válido até",
                        value=valido_ate_atual,
                        key="obra_orc_validade"
                    )
                    if st.button("💾 Salvar validade", key="obra_orc_save_validade"):
                        success, msg = update_orcamento_validade(orc_manage_id, validade)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
            else:
                st.info(f"Desconto: R$ {orcamento.get('desconto_valor', 0):,.2f} (orçamento não editável)")

            st.markdown("---")
            st.markdown("#### 📄 Gerar PDF")

            pdf_state_key = f"obra_pdf_bytes_{orc_manage_id}"

            if st.button("📄 Gerar PDF do Orçamento", type="primary", key="obra_orc_pdf"):
                with st.spinner("Gerando PDF..."):
                    fases_pdf = get_fases_por_orcamento(orc_manage_id)
                    servicos_por_fase = {}

                    for fase in fases_pdf:
                        servicos_por_fase[fase['id']] = get_servicos_fase(fase['id'])

                    data_emissao = date.today()
                    orcamento_pdf = dict(orcamento)
                    orcamento_pdf['pdf_emitido_em'] = data_emissao.isoformat()

                    pdf_bytes = gerar_pdf_orcamento(orcamento_pdf, fases_pdf, servicos_por_fase)

                    st.session_state[pdf_state_key] = {
                        "bytes": pdf_bytes,
                        "filename": f"orcamento_{orc_manage_id}.pdf",
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
    
    # ---- ABA FASES ----
    with tab3:
        st.markdown("### 📑 Fases do Orçamento")
        
        # Seletor de orçamento
        orcamentos = get_orcamentos_por_obra(obra_id)
        
        if not orcamentos:
            st.info("📋 Crie um orçamento primeiro para ver as fases.")
        else:
            orc_options = {o['id']: f"v{o['versao']} - {o['status']}" for o in orcamentos}
            
            selected_orc = st.selectbox(
                "Selecione o Orçamento",
                options=list(orc_options.keys()),
                format_func=lambda x: orc_options[x],
                index=0
            )
            
            if selected_orc:
                fases = get_fases_por_orcamento(selected_orc)
                recebimentos_existentes = get_recebimentos_por_orcamento(selected_orc)
                fases_com_recebimento = {
                    rec.get('obra_fase_id') for rec in recebimentos_existentes if rec.get('obra_fase_id')
                }
                
                if not fases:
                    st.info("📋 Nenhuma fase cadastrada.")
                else:
                    for fase in fases:
                        status_fase = {
                            'PENDENTE': '⏳',
                            'EM_ANDAMENTO': '🔄',
                            'CONCLUIDA': '✅'
                        }.get(fase.get('status', 'PENDENTE'), '📋')
                        
                        with st.expander(f"{fase['ordem']}. {fase['nome_fase']} {status_fase} - R$ {fase.get('valor_fase', 0):,.2f}"):
                            col1, col2 = st.columns([2, 1])
                            with col1:
                                status_opcoes = ['PENDENTE', 'EM_ANDAMENTO', 'CONCLUIDA', 'CANCELADO']
                                status_atual = fase.get('status', 'PENDENTE')
                                if status_atual not in status_opcoes:
                                    status_atual = 'PENDENTE'
                                novo_status = st.selectbox(
                                    "Status da Fase",
                                    options=status_opcoes,
                                    index=status_opcoes.index(status_atual),
                                    key=f"fase_status_{fase['id']}"
                                )
                            with col2:
                                if st.button("💾 Atualizar Status", key=f"salvar_status_{fase['id']}"):
                                    antes = {'status': fase.get('status')}
                                    success, msg = update_fase(fase['id'], {'status': novo_status})
                                    if success:
                                        audit_update('obra_fases', fase['id'], antes, {'status': novo_status})
                                        if novo_status == 'CONCLUIDA' and fase['id'] not in fases_com_recebimento:
                                            dados_receb = {
                                                'obra_fase_id': fase['id'],
                                                'valor': float(fase.get('valor_fase', 0) or 0),
                                                'vencimento': date.today().isoformat(),
                                                'status': 'ABERTO'
                                            }
                                            rec_success, rec_msg, novo_rec = create_recebimento(dados_receb)
                                            if rec_success:
                                                audit_insert('recebimentos', novo_rec)
                                                st.success("Recebimento gerado para a fase concluída.")
                                            else:
                                                st.error(rec_msg)
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            
                            st.markdown("---")
                            
                            # Serviços da fase
                            servicos = get_servicos_fase(fase['id'])
                            
                            if servicos:
                                st.markdown("**Serviços:**")
                                for serv in servicos:
                                    serv_info = serv.get('servicos', {})
                                    st.markdown(f"- {serv_info.get('nome', '-')} | {serv.get('quantidade', 0)} {serv_info.get('unidade', '')} x R$ {serv.get('valor_unit', 0):,.2f} = **R$ {serv.get('valor_total', 0):,.2f}**")
                            else:
                                st.info("Nenhum serviço nesta fase.")
                            
                            def _selecionar_orcamento_para_fase(fase_id: int, orc_id: int) -> None:
                                st.session_state['fase_selecionada'] = fase_id
                                st.session_state['orcamento_para_fase'] = orc_id
                                st.session_state['obra_orc_manage_id'] = orc_id

                            # Link para gerenciar serviços
                            if st.button(
                                "➕ Gerenciar Serviços",
                                key=f"serv_{fase['id']}",
                                on_click=_selecionar_orcamento_para_fase,
                                args=(fase['id'], selected_orc),
                            ):
                                st.success("Abra a aba Orçamentos para editar os serviços desta fase.")
    
    # ---- ABA AGENDA ----
    with tab4:
        st.markdown("### 📅 Agenda desta Obra")

        col1, col2, col3 = st.columns([1, 2, 1])

        def _shift_agenda_date(delta_days: int) -> None:
            st.session_state['obra_agenda_date'] = st.session_state['obra_agenda_date'] + timedelta(days=delta_days)

        with col1:
            st.button(
                "⬅️ Dia Anterior",
                key="obra_agenda_prev",
                on_click=_shift_agenda_date,
                args=(-1,),
            )
        with col3:
            st.button(
                "➡️ Próximo Dia",
                key="obra_agenda_next",
                on_click=_shift_agenda_date,
                args=(1,),
            )
        st.session_state.setdefault('obra_agenda_date', date.today())
        with col2:
            data_selecionada = st.date_input(
                "📆 Data",
                key="obra_agenda_date",
            )

        st.markdown(f"### 📋 Alocações para {data_selecionada.strftime('%d/%m/%Y')}")
        st.markdown("---")

        alocacoes_dia = get_alocacoes_dia(data_selecionada)
        alocacoes = [a for a in alocacoes_dia if a.get('obra_id') == obra_id]
        pessoas = get_pessoas(ativo=True)

        if not alocacoes:
            st.info("📋 Nenhuma alocação para esta obra neste dia.")
        else:
            orcamentos_obra = get_orcamentos_por_obra(obra_id)
            orc_status_por_id = {o['id']: o.get('status') for o in orcamentos_obra}

            for aloc in alocacoes:
                pessoa_nome = aloc.get('pessoas', {}).get('nome', '-') if aloc.get('pessoas') else '-'
                fase_nome = aloc.get('obra_fases', {}).get('nome_fase', '-') if aloc.get('obra_fases') else '-'
                orcamento_info = aloc.get('orcamentos', {})
                orcamento_label = (
                    f"v{orcamento_info.get('versao')} - {orcamento_info.get('status')}"
                    if orcamento_info else '--'
                )

                periodo_emoji = '☀️' if aloc.get('periodo') == 'INTEGRAL' else '🌤️'
                tipo_emoji = '🏠' if aloc.get('tipo') == 'INTERNO' else '🚗'
                confirmada = aloc.get('confirmada', False)

                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

                    with col1:
                        st.markdown(f"""
                        **👷 {pessoa_nome}**  
                        🏗️ {obra.get('titulo', '-')}
                        """)

                    with col2:
                        st.markdown(f"""
                        {periodo_emoji} {aloc.get('periodo', 'INTEGRAL')}  
                        {tipo_emoji} {aloc.get('tipo', 'INTERNO')}
                        """)

                    with col3:
                        st.markdown(f"""
                        📋 {orcamento_label}  
                        📑 {fase_nome}
                        """)

                    with col4:
                        btn_col1, btn_col2, btn_col3 = st.columns(3)
                        with btn_col1:
                            if confirmada:
                                st.markdown("✅")
                            else:
                                if st.button("✅", key=f"obra_confirm_{aloc['id']}"):
                                    if not aloc.get('orcamento_id') or not aloc.get('obra_fase_id'):
                                        st.error("Selecione orçamento e fase para confirmar.")
                                    elif orcamento_info and orcamento_info.get('status') != 'APROVADO':
                                        st.error(
                                            f"Orçamento precisa estar APROVADO para confirmar. "
                                            f"Status atual: {orcamento_info.get('status')}"
                                        )
                                    else:
                                        antes = {'confirmada': False}
                                        success, msg = update_alocacao_confirmada(aloc['id'], True)
                                        if success:
                                            audit_update('alocacoes', aloc['id'], antes, {'confirmada': True})
                                            st.success(msg)
                                            st.rerun()
                                        else:
                                            st.error(msg)
                        with btn_col2:
                            if st.button("✏️", key=f"obra_edit_aloc_{aloc['id']}"):
                                st.session_state['obra_aloc_edit_id'] = aloc['id']
                                st.rerun()
                        with btn_col3:
                            if st.button("🗑️", key=f"obra_del_aloc_{aloc['id']}"):
                                success, msg = delete_alocacao(aloc['id'])
                                if success:
                                    audit_delete('alocacoes', aloc)
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)

                    if aloc.get('observacao'):
                        st.markdown(f"📝 {aloc['observacao']}")

                    if st.session_state.get('obra_aloc_edit_id') == aloc['id']:
                        st.markdown("**✏️ Editar Alocação**")
                        if not pessoas:
                            st.warning("⚠️ Cadastre profissionais para editar.")
                        else:
                            with st.form(f"form_edit_aloc_obra_{aloc['id']}"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    pessoa_id_edit = st.selectbox(
                                        "👷 Profissional *",
                                        options=[p['id'] for p in pessoas],
                                        index=next(
                                            (i for i, p in enumerate(pessoas) if p['id'] == aloc.get('pessoa_id')),
                                            0
                                        ),
                                        format_func=lambda x: next((p['nome'] for p in pessoas if p['id'] == x), '-')
                                    )
                                with col2:
                                    periodo_edit = st.selectbox(
                                        "⏰ Período",
                                        options=['INTEGRAL', 'MEIO'],
                                        index=['INTEGRAL', 'MEIO'].index(aloc.get('periodo', 'INTEGRAL'))
                                    )

                                col1, col2 = st.columns(2)
                                with col1:
                                    tipo_edit = st.selectbox(
                                        "📍 Tipo",
                                        options=['INTERNO', 'EXTERNO'],
                                        index=['INTERNO', 'EXTERNO'].index(aloc.get('tipo', 'INTERNO'))
                                    )
                                with col2:
                                    st.markdown("")

                                st.markdown("**Opcional: Vincular a Orçamento/Fase**")
                                col1, col2 = st.columns(2)
                                with col1:
                                    orc_options_edit = [{'id': None, 'label': '-- Nenhum --'}] + [
                                        {'id': o['id'], 'label': f"v{o['versao']} - {o['status']}"}
                                        for o in orcamentos_obra
                                    ]
                                    orcamento_id_edit = st.selectbox(
                                        "📋 Orçamento",
                                        options=[o['id'] for o in orc_options_edit],
                                        index=next(
                                            (i for i, o in enumerate(orc_options_edit) if o['id'] == aloc.get('orcamento_id')),
                                            0
                                        ),
                                        format_func=lambda x: next((o['label'] for o in orc_options_edit if o['id'] == x), '-')
                                    )
                                with col2:
                                    if orcamento_id_edit:
                                        fases_edit = get_fases_por_orcamento(orcamento_id_edit)
                                        fase_options_edit = [{'id': None, 'label': '-- Nenhuma --'}] + [
                                            {'id': f['id'], 'label': f['nome_fase']}
                                            for f in fases_edit
                                        ]
                                    else:
                                        fase_options_edit = [{'id': None, 'label': '-- Selecione orçamento --'}]

                                    obra_fase_id_edit = st.selectbox(
                                        "📑 Fase",
                                        options=[f['id'] for f in fase_options_edit],
                                        index=next(
                                            (i for i, f in enumerate(fase_options_edit) if f['id'] == aloc.get('obra_fase_id')),
                                            0
                                        ),
                                        format_func=lambda x: next((f['label'] for f in fase_options_edit if f['id'] == x), '-')
                                    )

                                observacao_edit = st.text_input(
                                    "📝 Observação",
                                    value=aloc.get('observacao', '') or ''
                                )

                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.form_submit_button("💾 Salvar Alterações", type="primary"):
                                        if orcamento_id_edit and orc_status_por_id.get(orcamento_id_edit) != 'APROVADO':
                                            st.error(
                                                f"Orçamento precisa estar APROVADO para salvar. "
                                                f"Status atual: {orc_status_por_id.get(orcamento_id_edit)}"
                                            )
                                            st.stop()
                                        antes = {
                                            'pessoa_id': aloc.get('pessoa_id'),
                                            'obra_id': aloc.get('obra_id'),
                                            'periodo': aloc.get('periodo'),
                                            'tipo': aloc.get('tipo'),
                                            'orcamento_id': aloc.get('orcamento_id'),
                                            'obra_fase_id': aloc.get('obra_fase_id'),
                                            'observacao': aloc.get('observacao')
                                        }
                                        novos_dados = {
                                            'pessoa_id': pessoa_id_edit,
                                            'obra_id': obra_id,
                                            'periodo': periodo_edit,
                                            'tipo': tipo_edit,
                                            'observacao': observacao_edit,
                                            'orcamento_id': orcamento_id_edit,
                                            'obra_fase_id': obra_fase_id_edit
                                        }
                                        success, msg = update_alocacao(aloc['id'], novos_dados)
                                        if success:
                                            audit_update('alocacoes', aloc['id'], antes, novos_dados)
                                            st.session_state['obra_aloc_edit_id'] = None
                                            st.success(msg)
                                            st.rerun()
                                        else:
                                            st.error(msg)
                                with col2:
                                    if st.form_submit_button("❌ Cancelar"):
                                        st.session_state['obra_aloc_edit_id'] = None
                                        st.rerun()

                    st.markdown("---")

        st.markdown("### ➕ Nova Alocação")

        if not pessoas:
            st.warning("⚠️ Cadastre profissionais primeiro.")
        else:
            if st.session_state.get("obra_nova_orcamento_id_prev") != st.session_state.get("obra_nova_orcamento_id"):
                st.session_state["obra_nova_fase_id"] = None
                st.session_state["obra_nova_orcamento_id_prev"] = st.session_state.get("obra_nova_orcamento_id")

            with st.form("form_nova_alocacao_obra"):
                col1, col2 = st.columns(2)

                with col1:
                    pessoa_id = st.selectbox(
                        "👷 Profissional *",
                        options=[p['id'] for p in pessoas],
                        format_func=lambda x: next((p['nome'] for p in pessoas if p['id'] == x), '-'),
                        key="obra_nova_aloc_pessoa"
                    )

                with col2:
                    periodo = st.selectbox("⏰ Período", options=['INTEGRAL', 'MEIO'], key="obra_nova_aloc_periodo")

                col1, col2 = st.columns(2)
                with col1:
                    tipo = st.selectbox("📍 Tipo", options=['INTERNO', 'EXTERNO'], key="obra_nova_aloc_tipo")
                with col2:
                    st.markdown("")

                st.markdown("**Opcional: Vincular a Orçamento/Fase**")
                col1, col2 = st.columns(2)

                with col1:
                    orcamentos = get_orcamentos_por_obra(obra_id)
                    orc_status_por_id = {o['id']: o.get('status') for o in orcamentos}
                    orc_options = [{'id': None, 'label': '-- Nenhum --'}] + [
                        {'id': o['id'], 'label': f"v{o['versao']} - {o['status']}"}
                        for o in orcamentos
                    ]

                    orcamento_id = st.selectbox(
                        "📋 Orçamento",
                        options=[o['id'] for o in orc_options],
                        index=next(
                            (i for i, o in enumerate(orc_options) if o['id'] == st.session_state.get('obra_nova_orcamento_id')),
                            0
                        ),
                        format_func=lambda x: next((o['label'] for o in orc_options if o['id'] == x), '-'),
                        key="obra_nova_orcamento_id"
                    )

                with col2:
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
                        index=next(
                            (i for i, f in enumerate(fase_options) if f['id'] == st.session_state.get('obra_nova_fase_id')),
                            0
                        ),
                        format_func=lambda x: next((f['label'] for f in fase_options if f['id'] == x), '-'),
                        key="obra_nova_fase_id"
                    )

                observacao = st.text_input("📝 Observação", key="obra_nova_aloc_obs")

                if st.form_submit_button("✅ Criar Alocação", type="primary"):
                    if orcamento_id and orc_status_por_id.get(orcamento_id) != 'APROVADO':
                        st.error(
                            f"Orçamento precisa estar APROVADO para salvar. "
                            f"Status atual: {orc_status_por_id.get(orcamento_id)}"
                        )
                        st.stop()
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
    
    # ---- ABA APONTAMENTOS ----
    with tab5:
        st.markdown("### ⏱️ Apontamentos (Produção)")
        
        # Só mostra apontamentos se houver orçamento aprovado
        orcamentos = get_orcamentos_por_obra(obra_id)
        orc_aprovados = [o for o in orcamentos if o['status'] == 'APROVADO']
        
        if not orc_aprovados:
            st.warning("⚠️ É necessário ter um orçamento APROVADO para registrar apontamentos.")
        else:
            st.markdown("#### ➕ Novo Apontamento")
            
            pessoas = get_pessoas(ativo=True)
            orc_options = {o['id']: f"v{o['versao']} - {o['status']}" for o in orc_aprovados}
            
            if not pessoas:
                st.warning("⚠️ Cadastre profissionais antes de registrar apontamentos.")
            else:
                with st.form("form_novo_apontamento"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        pessoa_id = st.selectbox(
                            "👷 Profissional *",
                            options=[p['id'] for p in pessoas],
                            format_func=lambda x: next((p['nome'] for p in pessoas if p['id'] == x), '-')
                        )
                    
                    with col2:
                        orcamento_id = st.selectbox(
                            "📋 Orçamento *",
                            options=list(orc_options.keys()),
                            format_func=lambda x: orc_options[x]
                        )
                    
                    fases = get_fases_por_orcamento(orcamento_id)
                    if fases:
                        fase_id = st.selectbox(
                            "📑 Fase *",
                            options=[f['id'] for f in fases],
                            format_func=lambda x: next((f['nome_fase'] for f in fases if f['id'] == x), '-')
                        )
                    else:
                        st.warning("⚠️ Este orçamento não possui fases.")
                        fase_id = None
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        data_apont = st.date_input("📅 Data")
                    with col2:
                        tipo_dia = st.selectbox("Tipo do Dia", options=['NORMAL', 'SABADO', 'DOMINGO', 'FERIADO'])
                    with col3:
                        valor_base = st.number_input("💵 Valor Base (R$)", min_value=0.0, step=10.0)
                    
                    desconto_valor = st.number_input("Desconto (R$)", min_value=0.0, step=10.0)
                    observacao = st.text_input("📝 Observação")
                    
                    if st.form_submit_button("✅ Registrar Apontamento", type="primary"):
                        if not fase_id:
                            st.error("Selecione uma fase válida para registrar o apontamento.")
                            st.stop()
                        dados = {
                            'obra_id': obra_id,
                            'orcamento_id': orcamento_id,
                            'obra_fase_id': fase_id,
                            'pessoa_id': pessoa_id,
                            'data': data_apont.isoformat(),
                            'tipo_dia': tipo_dia,
                            'valor_base': valor_base,
                            'desconto_valor': desconto_valor,
                            'observacao': observacao
                        }
                        
                        success, msg, novo = create_apontamento(dados)
                        if success:
                            audit_insert('apontamentos', novo)
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
            
            st.markdown("---")
            st.markdown("#### 📋 Apontamentos Registrados")
            
            apontamentos = get_apontamentos(obra_id=obra_id)
            
            if not apontamentos:
                st.info("📋 Nenhum apontamento registrado.")
            else:
                for apt in apontamentos:
                    pessoa_nome = apt.get('pessoas', {}).get('nome', '-') if apt.get('pessoas') else '-'
                    fase_nome = apt.get('obra_fases', {}).get('nome_fase', '-') if apt.get('obra_fases') else '-'
                    valor_bruto = float(apt.get('valor_bruto', 0) or 0)
                    desconto_prof = float(apt.get('desconto_valor', 0) or 0)
                    valor_final = max(0.0, valor_bruto - desconto_prof)
                    
                    with st.expander(f"📅 {apt['data']} | 👷 {pessoa_nome} | 📑 {fase_nome}"):
                        st.markdown(f"""
                        💵 Base: R$ {apt.get('valor_base', 0):,.2f}  
                        💰 Bruto: R$ {valor_bruto:,.2f} | Desconto: R$ {desconto_prof:,.2f}  
                        ✅ Final: **R$ {valor_final:,.2f}**
                        """)
                        
                        with st.form(f"form_edit_apont_{apt['id']}"):
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                data_edit = st.date_input(
                                    "Data",
                                    value=date.fromisoformat(apt['data']) if isinstance(apt.get('data'), str) else apt.get('data'),
                                    key=f"data_{apt['id']}"
                                )
                            with col2:
                                tipo_edit = st.selectbox(
                                    "Tipo do Dia",
                                    options=['NORMAL', 'SABADO', 'DOMINGO', 'FERIADO'],
                                    index=['NORMAL', 'SABADO', 'DOMINGO', 'FERIADO'].index(apt.get('tipo_dia', 'NORMAL')),
                                    key=f"tipo_{apt['id']}"
                                )
                            with col3:
                                valor_base_edit = st.number_input(
                                    "Valor Base (R$)",
                                    min_value=0.0,
                                    value=float(apt.get('valor_base', 0) or 0),
                                    step=10.0,
                                    key=f"valor_{apt['id']}"
                                )
                            
                            desconto_edit = st.number_input(
                                "Desconto (R$)",
                                min_value=0.0,
                                value=float(apt.get('desconto_valor', 0) or 0),
                                step=10.0,
                                key=f"desc_{apt['id']}"
                            )
                            
                            observacao_edit = st.text_input(
                                "Observação",
                                value=apt.get('observacao', '') or '',
                                key=f"obs_{apt['id']}"
                            )
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 Atualizar"):
                                    antes = {
                                        'data': apt['data'],
                                        'tipo_dia': apt.get('tipo_dia'),
                                        'valor_base': apt.get('valor_base'),
                                        'desconto_valor': apt.get('desconto_valor'),
                                        'observacao': apt.get('observacao')
                                    }
                                    
                                    novos_dados = {
                                        'data': data_edit.isoformat(),
                                        'tipo_dia': tipo_edit,
                                        'valor_base': valor_base_edit,
                                        'desconto_valor': desconto_edit,
                                        'observacao': observacao_edit
                                    }
                                    
                                    success, msg = update_apontamento(apt['id'], novos_dados)
                                    if success:
                                        audit_update('apontamentos', apt['id'], antes, novos_dados)
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            
                            with col2:
                                if st.form_submit_button("🗑️ Remover"):
                                    success, msg = delete_apontamento(apt['id'])
                                    if success:
                                        audit_delete('apontamentos', apt)
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
