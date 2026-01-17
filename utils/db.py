"""
Módulo de acesso ao banco de dados Supabase
"""

import streamlit as st
from datetime import date, datetime
from typing import Optional
from utils.auth import get_supabase_client


# ============================================
# DASHBOARD / ESTATÍSTICAS
# ============================================

def get_dashboard_stats() -> dict:
    """Retorna estatísticas para o dashboard"""
    try:
        supabase = get_supabase_client()
        
        # Obras ativas
        obras = supabase.table('obras') \
            .select('id', count='exact') \
            .eq('ativo', True) \
            .in_('status', ['AGUARDANDO', 'INICIADO', 'PAUSADO']) \
            .execute()
        
        # Orçamentos pendentes (RASCUNHO ou EMITIDO)
        orcamentos = supabase.table('orcamentos') \
            .select('id', count='exact') \
            .in_('status', ['RASCUNHO', 'EMITIDO']) \
            .execute()
        
        # Pessoas ativas
        pessoas = supabase.table('pessoas') \
            .select('id', count='exact') \
            .eq('ativo', True) \
            .execute()
        
        # Clientes ativos
        clientes = supabase.table('clientes') \
            .select('id', count='exact') \
            .eq('ativo', True) \
            .execute()
        
        return {
            'obras_ativas': obras.count or 0,
            'orcamentos_pendentes': orcamentos.count or 0,
            'pessoas_ativas': pessoas.count or 0,
            'clientes_ativos': clientes.count or 0
        }
    except Exception as e:
        print(f"Erro ao buscar estatísticas: {e}")
        return {}


# ============================================
# CLIENTES
# ============================================

def get_clientes(busca: str = "", ativo: Optional[bool] = None) -> list:
    """Lista clientes com filtros"""
    try:
        supabase = get_supabase_client()
        
        query = supabase.table('clientes').select('*')
        
        if ativo is not None:
            query = query.eq('ativo', ativo)
        
        if busca:
            query = query.or_(f"nome.ilike.%{busca}%,telefone.ilike.%{busca}%")
        
        response = query.order('nome').execute()
        return response.data or []
        
    except Exception as e:
        print(f"Erro ao buscar clientes: {e}")
        return []


def get_cliente(cliente_id: int) -> dict | None:
    """Busca um cliente específico"""
    try:
        supabase = get_supabase_client()
        response = supabase.table('clientes') \
            .select('*') \
            .eq('id', cliente_id) \
            .single() \
            .execute()
        return response.data
    except:
        return None


def create_cliente(nome: str, telefone: str, endereco: str) -> tuple[bool, str, dict]:
    """Cria um novo cliente"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('clientes').insert({
            'nome': nome,
            'telefone': telefone,
            'endereco': endereco,
            'ativo': True
        }).execute()
        
        return True, "Cliente criado com sucesso!", response.data[0]
        
    except Exception as e:
        return False, f"Erro ao criar cliente: {e}", {}


def update_cliente(cliente_id: int, dados: dict) -> tuple[bool, str]:
    """Atualiza um cliente"""
    try:
        supabase = get_supabase_client()
        
        supabase.table('clientes') \
            .update(dados) \
            .eq('id', cliente_id) \
            .execute()
        
        return True, "Cliente atualizado com sucesso!"
        
    except Exception as e:
        return False, f"Erro ao atualizar cliente: {e}"


def toggle_cliente_ativo(cliente_id: int, ativo: bool) -> tuple[bool, str]:
    """Ativa ou inativa um cliente"""
    return update_cliente(cliente_id, {'ativo': ativo})


# ============================================
# PESSOAS / PROFISSIONAIS
# ============================================

def get_pessoas(busca: str = "", ativo: Optional[bool] = None, tipo: Optional[str] = None) -> list:
    """Lista pessoas com filtros"""
    try:
        supabase = get_supabase_client()
        
        query = supabase.table('pessoas').select('*')
        
        if ativo is not None:
            query = query.eq('ativo', ativo)
        
        if tipo:
            query = query.eq('tipo', tipo)
        
        if busca:
            query = query.ilike('nome', f'%{busca}%')
        
        response = query.order('nome').execute()
        return response.data or []
        
    except Exception as e:
        print(f"Erro ao buscar pessoas: {e}")
        return []


def get_pessoa(pessoa_id: int) -> dict | None:
    """Busca uma pessoa específica"""
    try:
        supabase = get_supabase_client()
        response = supabase.table('pessoas') \
            .select('*') \
            .eq('id', pessoa_id) \
            .single() \
            .execute()
        return response.data
    except:
        return None


def create_pessoa(dados: dict) -> tuple[bool, str, dict]:
    """Cria uma nova pessoa"""
    try:
        supabase = get_supabase_client()
        
        dados['ativo'] = True
        response = supabase.table('pessoas').insert(dados).execute()
        
        return True, "Profissional cadastrado com sucesso!", response.data[0]
        
    except Exception as e:
        return False, f"Erro ao cadastrar: {e}", {}


def update_pessoa(pessoa_id: int, dados: dict) -> tuple[bool, str]:
    """Atualiza uma pessoa"""
    try:
        supabase = get_supabase_client()
        
        supabase.table('pessoas') \
            .update(dados) \
            .eq('id', pessoa_id) \
            .execute()
        
        return True, "Profissional atualizado com sucesso!"
        
    except Exception as e:
        return False, f"Erro ao atualizar: {e}"


# ============================================
# OBRAS
# ============================================

def get_obras(busca: str = "", status: Optional[str] = None, ativo: Optional[bool] = None) -> list:
    """Lista obras com filtros"""
    try:
        supabase = get_supabase_client()
        
        query = supabase.table('obras') \
            .select('*, clientes(nome)')
        
        if ativo is not None:
            query = query.eq('ativo', ativo)
        
        if status:
            query = query.eq('status', status)
        
        if busca:
            query = query.or_(f"titulo.ilike.%{busca}%,endereco_obra.ilike.%{busca}%")
        
        response = query.order('criado_em', desc=True).execute()
        return response.data or []
        
    except Exception as e:
        print(f"Erro ao buscar obras: {e}")
        return []


def get_obra(obra_id: int) -> dict | None:
    """Busca uma obra específica com dados do cliente"""
    try:
        supabase = get_supabase_client()
        response = supabase.table('obras') \
            .select('*, clientes(*)') \
            .eq('id', obra_id) \
            .single() \
            .execute()
        return response.data
    except:
        return None


def create_obra(dados: dict) -> tuple[bool, str, dict]:
    """Cria uma nova obra"""
    try:
        supabase = get_supabase_client()
        
        dados['ativo'] = True
        dados['status'] = 'AGUARDANDO'
        response = supabase.table('obras').insert(dados).execute()
        
        return True, "Obra criada com sucesso!", response.data[0]
        
    except Exception as e:
        return False, f"Erro ao criar obra: {e}", {}


def update_obra(obra_id: int, dados: dict) -> tuple[bool, str]:
    """Atualiza uma obra"""
    try:
        supabase = get_supabase_client()
        
        supabase.table('obras') \
            .update(dados) \
            .eq('id', obra_id) \
            .execute()
        
        return True, "Obra atualizada com sucesso!"
        
    except Exception as e:
        return False, f"Erro ao atualizar obra: {e}"


# ============================================
# ORÇAMENTOS
# ============================================

def get_orcamentos_por_obra(obra_id: int) -> list:
    """Lista orçamentos de uma obra"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('orcamentos') \
            .select('*') \
            .eq('obra_id', obra_id) \
            .order('versao', desc=True) \
            .execute()
        
        return response.data or []
        
    except Exception as e:
        print(f"Erro ao buscar orçamentos: {e}")
        return []


def get_orcamento(orcamento_id: int) -> dict | None:
    """Busca um orçamento específico"""
    try:
        supabase = get_supabase_client()
        response = supabase.table('orcamentos') \
            .select('*, obras(*, clientes(*))') \
            .eq('id', orcamento_id) \
            .single() \
            .execute()
        return response.data
    except:
        return None


def create_orcamento(obra_id: int) -> tuple[bool, str, dict]:
    """Cria novo orçamento com versão incrementada"""
    try:
        supabase = get_supabase_client()
        
        # Busca a maior versão existente
        existing = supabase.table('orcamentos') \
            .select('versao') \
            .eq('obra_id', obra_id) \
            .order('versao', desc=True) \
            .limit(1) \
            .execute()
        
        nova_versao = 1
        if existing.data:
            nova_versao = existing.data[0]['versao'] + 1
        
        response = supabase.table('orcamentos').insert({
            'obra_id': obra_id,
            'versao': nova_versao,
            'status': 'RASCUNHO',
            'valor_total': 0,
            'desconto_valor': 0,
            'valor_total_final': 0
        }).execute()
        
        return True, f"Orçamento v{nova_versao} criado!", response.data[0]
        
    except Exception as e:
        return False, f"Erro ao criar orçamento: {e}", {}


def update_orcamento_status(orcamento_id: int, novo_status: str, campos_extra: dict = None) -> tuple[bool, str]:
    """Atualiza o status de um orçamento"""
    try:
        supabase = get_supabase_client()
        
        dados = {'status': novo_status}
        
        if campos_extra:
            dados.update(campos_extra)
        
        if novo_status == 'APROVADO':
            dados['aprovado_em'] = datetime.now().isoformat()
        elif novo_status == 'CANCELADO':
            dados['cancelado_em'] = datetime.now().isoformat()
        
        supabase.table('orcamentos') \
            .update(dados) \
            .eq('id', orcamento_id) \
            .execute()
        
        return True, f"Orçamento {novo_status.lower()} com sucesso!"
        
    except Exception as e:
        return False, f"Erro ao atualizar orçamento: {e}"


def update_orcamento_desconto(orcamento_id: int, desconto: float) -> tuple[bool, str]:
    """Atualiza o desconto do orçamento"""
    try:
        supabase = get_supabase_client()
        
        supabase.table('orcamentos') \
            .update({'desconto_valor': desconto}) \
            .eq('id', orcamento_id) \
            .execute()

        limpar_pdf_orcamento(orcamento_id)
        
        # Recalcula totais
        recalcular_orcamento(orcamento_id)
        
        return True, "Desconto atualizado!"
        
    except Exception as e:
        return False, f"Erro ao atualizar desconto: {e}"


def recalcular_orcamento(orcamento_id: int):
    """Chama a função de recálculo do orçamento"""
    try:
        supabase = get_supabase_client()
        supabase.rpc('fn_recalcular_orcamento', {'p_orcamento_id': orcamento_id}).execute()
    except Exception as e:
        print(f"Erro ao recalcular orçamento: {e}")


def limpar_pdf_orcamento(orcamento_id: int):
    """Limpa a URL do PDF quando o orçamento é alterado"""
    try:
        supabase = get_supabase_client()
        supabase.table('orcamentos') \
            .update({'pdf_url': None, 'pdf_emitido_em': None}) \
            .eq('id', orcamento_id) \
            .execute()
    except Exception as e:
        print(f"Erro ao limpar PDF do orçamento: {e}")


def update_orcamento_validade(orcamento_id: int, valido_ate: date) -> tuple[bool, str]:
    """Atualiza a validade do orçamento"""
    try:
        supabase = get_supabase_client()
        supabase.table('orcamentos') \
            .update({'valido_ate': valido_ate.isoformat()}) \
            .eq('id', orcamento_id) \
            .execute()
        limpar_pdf_orcamento(orcamento_id)
        return True, "Validade atualizada!"
    except Exception as e:
        return False, f"Erro ao atualizar validade: {e}"


# ============================================
# FASES DO ORÇAMENTO
# ============================================

FASES_PADRAO = [
    {'nome_fase': 'Preparação', 'ordem': 1},
    {'nome_fase': 'Proteção', 'ordem': 2},
    {'nome_fase': 'Massa/Lixa', 'ordem': 3},
    {'nome_fase': 'Pintura 1ª demão', 'ordem': 4},
    {'nome_fase': 'Pintura 2ª demão', 'ordem': 5},
    {'nome_fase': 'Acabamento', 'ordem': 6},
    {'nome_fase': 'Limpeza/Entrega', 'ordem': 7},
]


def get_fases_por_orcamento(orcamento_id: int) -> list:
    """Lista fases de um orçamento"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('obra_fases') \
            .select('*') \
            .eq('orcamento_id', orcamento_id) \
            .order('ordem') \
            .execute()
        
        return response.data or []
        
    except Exception as e:
        print(f"Erro ao buscar fases: {e}")
        return []


def create_fases_padrao(obra_id: int, orcamento_id: int) -> tuple[bool, str]:
    """Cria as fases padrão para um orçamento"""
    try:
        supabase = get_supabase_client()
        
        fases = []
        for fase in FASES_PADRAO:
            fases.append({
                'obra_id': obra_id,
                'orcamento_id': orcamento_id,
                'nome_fase': fase['nome_fase'],
                'ordem': fase['ordem'],
                'status': 'PENDENTE',
                'valor_fase': 0
            })
        
        supabase.table('obra_fases').insert(fases).execute()
        
        return True, "Fases padrão criadas!"
        
    except Exception as e:
        return False, f"Erro ao criar fases: {e}"


def update_fase(fase_id: int, dados: dict) -> tuple[bool, str]:
    """Atualiza uma fase"""
    try:
        supabase = get_supabase_client()

        fase_info = supabase.table('obra_fases') \
            .select('orcamento_id') \
            .eq('id', fase_id) \
            .single() \
            .execute()
        
        supabase.table('obra_fases') \
            .update(dados) \
            .eq('id', fase_id) \
            .execute()

        if fase_info.data:
            limpar_pdf_orcamento(fase_info.data['orcamento_id'])
        
        return True, "Fase atualizada!"
        
    except Exception as e:
        return False, f"Erro ao atualizar fase: {e}"


# ============================================
# SERVIÇOS (CATÁLOGO)
# ============================================

def get_servicos(ativo: Optional[bool] = True) -> list:
    """Lista serviços do catálogo"""
    try:
        supabase = get_supabase_client()
        
        query = supabase.table('servicos').select('*')
        
        if ativo is not None:
            query = query.eq('ativo', ativo)
        
        response = query.order('nome').execute()
        return response.data or []
        
    except Exception as e:
        print(f"Erro ao buscar serviços: {e}")
        return []


def create_servico(nome: str, unidade: str) -> tuple[bool, str, dict]:
    """Cria um novo serviço"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('servicos').insert({
            'nome': nome,
            'unidade': unidade,
            'ativo': True
        }).execute()
        
        return True, "Serviço criado!", response.data[0]
        
    except Exception as e:
        return False, f"Erro ao criar serviço: {e}", {}


def update_servico(servico_id: int, dados: dict) -> tuple[bool, str, dict]:
    """Atualiza um serviço do catálogo"""
    try:
        supabase = get_supabase_client()

        response = supabase.table('servicos') \
            .update(dados) \
            .eq('id', servico_id) \
            .execute()

        return True, "Serviço atualizado!", response.data[0] if response.data else {}

    except Exception as e:
        return False, f"Erro ao atualizar serviço: {e}", {}
# ============================================
# SERVIÇOS POR FASE
# ============================================

def get_servicos_fase(obra_fase_id: int) -> list:
    """Lista serviços de uma fase"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('orcamento_fase_servicos') \
            .select('*, servicos(nome, unidade, ativo)') \
            .eq('obra_fase_id', obra_fase_id) \
            .eq('servicos.ativo', True) \
            .execute()
        
        return response.data or []
        
    except Exception as e:
        print(f"Erro ao buscar serviços da fase: {e}")
        return []


def add_servico_fase(obra_fase_id: int, servico_id: int, quantidade: float, 
                     valor_unit: float, observacao: str, orcamento_id: int) -> tuple[bool, str]:
    """Adiciona um serviço a uma fase"""
    try:
        supabase = get_supabase_client()
        
        supabase.table('orcamento_fase_servicos').insert({
            'obra_fase_id': obra_fase_id,
            'servico_id': servico_id,
            'quantidade': quantidade,
            'valor_unit': valor_unit,
            'observacao': observacao
        }).execute()

        limpar_pdf_orcamento(orcamento_id)
        
        # Recalcula o orçamento
        recalcular_orcamento(orcamento_id)
        
        return True, "Serviço adicionado!"
        
    except Exception as e:
        if 'unique' in str(e).lower():
            return False, "Este serviço já existe nesta fase."
        return False, f"Erro ao adicionar serviço: {e}"


def update_servico_fase(item_id: int, dados: dict, orcamento_id: int) -> tuple[bool, str]:
    """Atualiza um serviço de fase"""
    try:
        supabase = get_supabase_client()
        
        supabase.table('orcamento_fase_servicos') \
            .update(dados) \
            .eq('id', item_id) \
            .execute()

        limpar_pdf_orcamento(orcamento_id)
        
        recalcular_orcamento(orcamento_id)
        
        return True, "Serviço atualizado!"
        
    except Exception as e:
        return False, f"Erro ao atualizar: {e}"


def delete_servico_fase(item_id: int, orcamento_id: int) -> tuple[bool, str]:
    """Remove um serviço de fase"""
    try:
        supabase = get_supabase_client()
        
        supabase.table('orcamento_fase_servicos') \
            .delete() \
            .eq('id', item_id) \
            .execute()

        limpar_pdf_orcamento(orcamento_id)
        
        recalcular_orcamento(orcamento_id)
        
        return True, "Serviço removido!"
        
    except Exception as e:
        return False, f"Erro ao remover: {e}"


# ============================================
# ALOCAÇÕES (AGENDA)
# ============================================

def get_alocacoes_dia(data: date) -> list:
    """Lista alocações de um dia"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('alocacoes') \
            .select('*, pessoas(nome), obras(titulo), orcamentos(versao, status), obra_fases(nome_fase)') \
            .eq('data', data.isoformat()) \
            .order('pessoa_id') \
            .execute()
        
        return response.data or []
        
    except Exception as e:
        print(f"Erro ao buscar alocações: {e}")
        return []


def get_alocacoes_obra(obra_id: int) -> list:
    """Lista alocações de uma obra"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('alocacoes') \
            .select('*, pessoas(nome), orcamentos(versao, status), obra_fases(nome_fase)') \
            .eq('obra_id', obra_id) \
            .order('data', desc=True) \
            .execute()
        
        return response.data or []
        
    except Exception as e:
        print(f"Erro ao buscar alocações: {e}")
        return []


def create_alocacao(dados: dict) -> tuple[bool, str, dict]:
    """Cria uma nova alocação"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('alocacoes').insert(dados).execute()
        
        return True, "Alocação criada!", response.data[0]
        
    except Exception as e:
        return False, f"Erro ao criar alocação: {e}", {}


def update_alocacao(alocacao_id: int, dados: dict) -> tuple[bool, str]:
    """Atualiza uma alocação"""
    try:
        supabase = get_supabase_client()
        
        supabase.table('alocacoes') \
            .update(dados) \
            .eq('id', alocacao_id) \
            .execute()
        
        return True, "Alocação atualizada!"
        
    except Exception as e:
        return False, f"Erro ao atualizar alocação: {e}"


def update_alocacao_confirmada(alocacao_id: int, confirmada: bool = True) -> tuple[bool, str]:
    """Confirma ou desfaz confirmação de uma alocação"""
    return update_alocacao(alocacao_id, {'confirmada': confirmada})


def delete_alocacao(alocacao_id: int) -> tuple[bool, str]:
    """Remove uma alocação"""
    try:
        supabase = get_supabase_client()
        
        supabase.table('alocacoes') \
            .delete() \
            .eq('id', alocacao_id) \
            .execute()
        
        return True, "Alocação removida!"
        
    except Exception as e:
        return False, f"Erro ao remover: {e}"


# ============================================
# APONTAMENTOS
# ============================================

def get_apontamentos(obra_id: Optional[int] = None, data_inicio: Optional[date] = None, 
                     data_fim: Optional[date] = None) -> list:
    """Lista apontamentos com filtros"""
    try:
        supabase = get_supabase_client()
        
        query = supabase.table('apontamentos') \
            .select('*, pessoas(nome), obras(titulo), obra_fases(nome_fase)')
        
        if obra_id:
            query = query.eq('obra_id', obra_id)
        
        if data_inicio:
            query = query.gte('data', data_inicio.isoformat())
        
        if data_fim:
            query = query.lte('data', data_fim.isoformat())
        
        response = query.order('data', desc=True).execute()
        return response.data or []
        
    except Exception as e:
        print(f"Erro ao buscar apontamentos: {e}")
        return []


def create_apontamento(dados: dict) -> tuple[bool, str, dict]:
    """Cria um novo apontamento"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('apontamentos').insert(dados).execute()
        
        return True, "Apontamento registrado!", response.data[0]
        
    except Exception as e:
        if 'aprovado' in str(e).lower():
            return False, "O orçamento precisa estar APROVADO.", {}
        return False, f"Erro ao registrar: {e}", {}


def get_apontamento(apontamento_id: int) -> dict | None:
    """Busca um apontamento específico"""
    try:
        supabase = get_supabase_client()
        response = supabase.table('apontamentos') \
            .select('*') \
            .eq('id', apontamento_id) \
            .single() \
            .execute()
        return response.data
    except:
        return None


def update_apontamento(apontamento_id: int, dados: dict) -> tuple[bool, str]:
    """Atualiza um apontamento"""
    try:
        supabase = get_supabase_client()
        
        supabase.table('apontamentos') \
            .update(dados) \
            .eq('id', apontamento_id) \
            .execute()
        
        return True, "Apontamento atualizado!"
        
    except Exception as e:
        if 'aprovado' in str(e).lower():
            return False, "O orçamento precisa estar APROVADO."
        return False, f"Erro ao atualizar: {e}"


def delete_apontamento(apontamento_id: int) -> tuple[bool, str]:
    """Remove um apontamento"""
    try:
        supabase = get_supabase_client()
        
        supabase.table('apontamentos') \
            .delete() \
            .eq('id', apontamento_id) \
            .execute()
        
        return True, "Apontamento removido!"
        
    except Exception as e:
        return False, f"Erro ao remover: {e}"


# ============================================
# FINANCEIRO (ADMIN ONLY)
# ============================================

def get_recebimentos(status: Optional[str] = None) -> list:
    """Lista recebimentos"""
    try:
        supabase = get_supabase_client()
        
        query = supabase.table('recebimentos') \
            .select('*, obra_fases(nome_fase, obras(titulo))')
        
        if status:
            query = query.eq('status', status)
        
        response = query.order('vencimento', desc=True).execute()
        return response.data or []
        
    except Exception as e:
        print(f"Erro ao buscar recebimentos: {e}")
        return []


def create_recebimento(dados: dict) -> tuple[bool, str, dict]:
    """Cria um novo recebimento"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('recebimentos').insert(dados).execute()
        
        return True, "Recebimento criado!", response.data[0]
        
    except Exception as e:
        return False, f"Erro ao criar: {e}", {}


def update_recebimento_status(recebimento_id: int, novo_status: str, recebido_em: Optional[date] = None) -> tuple[bool, str]:
    """Atualiza o status de um recebimento"""
    try:
        supabase = get_supabase_client()
        
        dados = {'status': novo_status}
        if recebido_em:
            dados['recebido_em'] = recebido_em.isoformat()
        
        supabase.table('recebimentos') \
            .update(dados) \
            .eq('id', recebimento_id) \
            .execute()
        
        return True, "Recebimento atualizado!"
        
    except Exception as e:
        return False, f"Erro ao atualizar: {e}"


def get_pagamentos(status: Optional[str] = None) -> list:
    """Lista pagamentos"""
    try:
        supabase = get_supabase_client()
        
        query = supabase.table('pagamentos').select('*')
        
        if status:
            query = query.eq('status', status)
        
        response = query.order('criado_em', desc=True).execute()
        return response.data or []
        
    except Exception as e:
        print(f"Erro ao buscar pagamentos: {e}")
        return []


def get_pagamento_itens(pagamento_id: int) -> list:
    """Lista itens de um pagamento"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('pagamento_itens') \
            .select('*, apontamentos(*, pessoas(nome), obras(titulo), obra_fases(nome_fase))') \
            .eq('pagamento_id', pagamento_id) \
            .order('criado_em') \
            .execute()
        
        return response.data or []
        
    except Exception as e:
        print(f"Erro ao buscar itens de pagamento: {e}")
        return []


def create_pagamento(dados: dict) -> tuple[bool, str, dict]:
    """Cria um novo pagamento"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('pagamentos').insert(dados).execute()
        
        return True, "Pagamento criado!", response.data[0]
        
    except Exception as e:
        return False, f"Erro ao criar pagamento: {e}", {}


def update_pagamento_status(pagamento_id: int, novo_status: str, pago_em: Optional[date] = None) -> tuple[bool, str]:
    """Atualiza o status de um pagamento"""
    try:
        supabase = get_supabase_client()
        
        dados = {'status': novo_status}
        if novo_status == 'PAGO' and pago_em:
            dados['pago_em'] = pago_em.isoformat()
        
        supabase.table('pagamentos') \
            .update(dados) \
            .eq('id', pagamento_id) \
            .execute()
        
        return True, "Pagamento atualizado!"
        
    except Exception as e:
        return False, f"Erro ao atualizar pagamento: {e}"


def create_pagamento_item(pagamento_id: int, apontamento_id: int, valor: float, observacao: str = "") -> tuple[bool, str, dict]:
    """Adiciona um item a um pagamento"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('pagamento_itens').insert({
            'pagamento_id': pagamento_id,
            'apontamento_id': apontamento_id,
            'valor': valor,
            'observacao': observacao
        }).execute()
        
        return True, "Item adicionado!", response.data[0]
        
    except Exception as e:
        return False, f"Erro ao adicionar item: {e}", {}


def delete_pagamento_item(item_id: int) -> tuple[bool, str]:
    """Remove um item de pagamento"""
    try:
        supabase = get_supabase_client()
        
        supabase.table('pagamento_itens') \
            .delete() \
            .eq('id', item_id) \
            .execute()
        
        return True, "Item removido!"
        
    except Exception as e:
        return False, f"Erro ao remover item: {e}"


# ============================================
# USUÁRIOS (ADMIN ONLY)
# ============================================

def get_usuarios_app() -> list:
    """Lista usuários do app"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('usuarios_app') \
            .select('*') \
            .order('usuario') \
            .execute()
        
        return response.data or []
        
    except Exception as e:
        print(f"Erro ao buscar usuários: {e}")
        return []


def update_usuario_app(usuario_id: int, dados: dict) -> tuple[bool, str]:
    """Atualiza um usuário do app"""
    try:
        supabase = get_supabase_client()
        
        supabase.table('usuarios_app') \
            .update(dados) \
            .eq('id', usuario_id) \
            .execute()
        
        return True, "Usuário atualizado!"
        
    except Exception as e:
        return False, f"Erro ao atualizar: {e}"


# ============================================
# AUDITORIA
# ============================================

def get_auditoria(entidade: Optional[str] = None, data_inicio: Optional[date] = None,
                  data_fim: Optional[date] = None, busca: Optional[str] = None) -> list:
    """Lista registros de auditoria"""
    try:
        supabase = get_supabase_client()
        
        query = supabase.table('auditoria').select('*')
        
        if entidade:
            query = query.eq('entidade', entidade)
        
        if data_inicio:
            query = query.gte('criado_em', data_inicio.isoformat())
        
        if data_fim:
            query = query.lte('criado_em', f"{data_fim.isoformat()}T23:59:59")
        
        if busca:
            query = query.ilike('usuario', f'%{busca}%')
        
        response = query.order('criado_em', desc=True).limit(100).execute()
        return response.data or []
        
    except Exception as e:
        print(f"Erro ao buscar auditoria: {e}")
        return []
