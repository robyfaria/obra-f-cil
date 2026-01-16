"""
Página de Obras - Listagem, CRUD e detalhes com abas
"""

import streamlit as st
from datetime import date
from utils.auth import require_auth
from utils.db import (
    get_obras, get_obra, create_obra, update_obra,
    get_clientes, get_orcamentos_por_obra, get_fases_por_orcamento,
    get_alocacoes_obra, get_apontamentos, get_servicos_fase,
    get_pessoas, create_apontamento, update_apontamento, delete_apontamento
)
from utils.auditoria import audit_insert, audit_update, audit_delete

# Requer autenticação
profile = require_auth()

st.title("🏠 Obras")

# Estado da página
if 'obra_view' not in st.session_state:
    st.session_state['obra_view'] = 'lista'
if 'obra_id' not in st.session_state:
    st.session_state['obra_id'] = None

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
            from utils.db import create_orcamento, create_fases_padrao
            
            success, msg, novo_orc = create_orcamento(obra_id)
            
            if success:
                # Cria fases padrão
                create_fases_padrao(obra_id, novo_orc['id'])
                audit_insert('orcamentos', novo_orc)
                st.success(f"✅ {msg} com fases padrão!")
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
                                    st.success(msg)
                                    st.rerun()
    
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
                
                if not fases:
                    st.info("📋 Nenhuma fase cadastrada.")
                    
                    if st.button("🔧 Gerar Fases Padrão"):
                        from utils.db import create_fases_padrao
                        
                        # Precisamos do obra_id
                        success, msg = create_fases_padrao(obra_id, selected_orc)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    for fase in fases:
                        status_fase = {
                            'PENDENTE': '⏳',
                            'EM_ANDAMENTO': '🔄',
                            'CONCLUIDA': '✅'
                        }.get(fase.get('status', 'PENDENTE'), '📋')
                        
                        with st.expander(f"{fase['ordem']}. {fase['nome_fase']} {status_fase} - R$ {fase.get('valor_fase', 0):,.2f}"):
                            
                            # Serviços da fase
                            servicos = get_servicos_fase(fase['id'])
                            
                            if servicos:
                                st.markdown("**Serviços:**")
                                for serv in servicos:
                                    serv_info = serv.get('servicos', {})
                                    st.markdown(f"- {serv_info.get('nome', '-')} | {serv.get('quantidade', 0)} {serv_info.get('unidade', '')} x R$ {serv.get('valor_unit', 0):,.2f} = **R$ {serv.get('valor_total', 0):,.2f}**")
                            else:
                                st.info("Nenhum serviço nesta fase.")
                            
                            # Link para gerenciar serviços
                            if st.button(f"➕ Gerenciar Serviços", key=f"serv_{fase['id']}"):
                                st.session_state['fase_selecionada'] = fase['id']
                                st.session_state['orcamento_para_fase'] = selected_orc
                                st.switch_page("pages/4_📋_Orcamentos.py")
    
    # ---- ABA AGENDA ----
    with tab4:
        st.markdown("### 📅 Alocações desta Obra")
        
        alocacoes = get_alocacoes_obra(obra_id)
        
        if not alocacoes:
            st.info("📋 Nenhuma alocação para esta obra.")
        else:
            for aloc in alocacoes:
                pessoa_nome = aloc.get('pessoas', {}).get('nome', '-') if aloc.get('pessoas') else '-'
                
                st.markdown(f"""
                📅 **{aloc['data']}** | 👷 {pessoa_nome} | ⏰ {aloc.get('periodo', 'INTEGRAL')}
                """)
        
        if st.button("➕ Nova Alocação"):
            st.switch_page("pages/5_📅_Agenda.py")
    
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
                    
                    with st.expander(f"📅 {apt['data']} | 👷 {pessoa_nome} | 📑 {fase_nome}"):
                        st.markdown(f"""
                        💵 Base: R$ {apt.get('valor_base', 0):,.2f}  
                        💰 Bruto: R$ {apt.get('valor_bruto', 0):,.2f} | Rateado: R$ {apt.get('valor_rateado', 0):,.2f}  
                        ✅ Final: **R$ {apt.get('valor_final', 0):,.2f}**
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
