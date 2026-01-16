"""
Módulo de auditoria - Registra ações no banco de dados
"""

import json
import streamlit as st
from datetime import datetime
from utils.auth import get_supabase_client, is_admin


def registrar_auditoria(
    entidade: str,
    entidade_id: int | str,
    acao: str,
    antes: dict = None,
    depois: dict = None
):
    """
    Registra uma ação de auditoria no banco
    
    Args:
        entidade: Nome da tabela/entidade (ex: 'clientes', 'obras')
        entidade_id: ID do registro afetado
        acao: Ação realizada (INSERT, UPDATE, DELETE, STATUS_CHANGE, etc.)
        antes: Estado anterior do registro (para UPDATE/DELETE)
        depois: Novo estado do registro (para INSERT/UPDATE)
    """
    if not is_admin():
        return
    try:
        supabase = get_supabase_client()
        
        # Pega o nome do usuário logado
        profile = st.session_state.get('user_profile', {})
        usuario = profile.get('usuario', 'Sistema')
        
        # Prepara os dados
        dados = {
            'usuario': usuario,
            'entidade': entidade,
            'entidade_id': str(entidade_id),
            'acao': acao,
            'antes_json': json.dumps(antes, default=str) if antes else None,
            'depois_json': json.dumps(depois, default=str) if depois else None,
        }
        
        supabase.table('auditoria').insert(dados).execute()
        
    except Exception as e:
        # Não interrompe a operação principal se a auditoria falhar
        print(f"Erro ao registrar auditoria: {e}")


def audit_insert(entidade: str, registro: dict):
    """Helper para auditoria de INSERT"""
    registrar_auditoria(
        entidade=entidade,
        entidade_id=registro.get('id', 0),
        acao='INSERT',
        antes=None,
        depois=registro
    )


def audit_update(entidade: str, entidade_id: int, antes: dict, depois: dict):
    """Helper para auditoria de UPDATE"""
    registrar_auditoria(
        entidade=entidade,
        entidade_id=entidade_id,
        acao='UPDATE',
        antes=antes,
        depois=depois
    )


def audit_delete(entidade: str, registro: dict):
    """Helper para auditoria de DELETE"""
    registrar_auditoria(
        entidade=entidade,
        entidade_id=registro.get('id', 0),
        acao='DELETE',
        antes=registro,
        depois=None
    )


def audit_status_change(entidade: str, entidade_id: int, status_anterior: str, status_novo: str):
    """Helper para auditoria de mudança de status"""
    registrar_auditoria(
        entidade=entidade,
        entidade_id=entidade_id,
        acao='STATUS_CHANGE',
        antes={'status': status_anterior},
        depois={'status': status_novo}
    )
