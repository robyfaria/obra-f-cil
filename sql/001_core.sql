set statement_timeout = '15min';

begin;

-- =========================================================
-- RESET TOTAL
-- =========================================================
drop schema if exists public cascade;
create schema public;

grant usage on schema public to postgres, anon, authenticated, service_role;
grant all on schema public to postgres, service_role;

alter default privileges in schema public grant all on tables    to postgres, service_role;
alter default privileges in schema public grant all on sequences to postgres, service_role;
alter default privileges in schema public grant all on functions to postgres, service_role;

alter default privileges in schema public grant select, insert, update, delete on tables to authenticated;
alter default privileges in schema public grant select on tables to anon;

-- =========================================================
-- EXTENSÕES
-- =========================================================
create extension if not exists pgcrypto;

-- =========================================================
-- 1) USUÁRIOS DO APP (liga com auth.users)
-- =========================================================
create table public.usuarios_app (
  id bigserial primary key,
  auth_user_id uuid not null unique, -- auth.users.id
  usuario varchar(100) not null unique,
  perfil varchar(20) not null check (perfil in ('ADMIN','OPERACAO')),
  ativo boolean not null default true,
  criado_em timestamptz not null default now()
);

create index idx_usuarios_app_auth_user on public.usuarios_app(auth_user_id);
create index idx_usuarios_app_perfil on public.usuarios_app(perfil);

-- =========================================================
-- 2) AUDITORIA (logs) - jsonb (melhor que text)
-- =========================================================
create table public.auditoria (
  id bigserial primary key,
  usuario varchar(100),
  entidade varchar(50) not null,
  entidade_id varchar(50),
  acao varchar(50) not null,
  antes_json jsonb,
  depois_json jsonb,
  criado_em timestamptz not null default now()
);

create index idx_auditoria_entidade on public.auditoria(entidade);
create index idx_auditoria_data on public.auditoria(criado_em);

-- =========================================================
-- 3) FUNÇÕES DE PERFIL (base das policies)
-- =========================================================
create or replace function public.fn_user_perfil()
returns text
language sql
stable
security definer
set search_path = public
as $$
  select u.perfil
  from public.usuarios_app u
  where u.auth_user_id = auth.uid()
    and u.ativo = true
  limit 1
$$;

create or replace function public.fn_is_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select public.fn_user_perfil() = 'ADMIN'
$$;

create or replace function public.fn_is_operacao()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select public.fn_user_perfil() = 'OPERACAO'
$$;

-- =========================================================
-- 4) CADASTROS
-- =========================================================
create table public.clientes (
  id bigserial primary key,
  nome varchar(200) not null,
  telefone varchar(20),
  endereco text,
  ativo boolean not null default true,
  criado_em timestamptz not null default now()
);

create index idx_clientes_ativo on public.clientes(ativo);
create index idx_clientes_nome on public.clientes(nome);

create table public.pessoas (
  id bigserial primary key,
  nome varchar(200) not null,
  tipo varchar(20) not null check (tipo in ('PINTOR','AJUDANTE','TERCEIRO')),
  telefone varchar(20),
  diaria_base numeric(10,2) not null default 0,
  observacao text,
  ativo boolean not null default true,
  criado_em timestamptz not null default now()
);

create index idx_pessoas_ativo on public.pessoas(ativo);
create index idx_pessoas_tipo on public.pessoas(tipo);
create index idx_pessoas_nome on public.pessoas(nome);

-- =========================================================
-- 5) OBRAS / ORÇAMENTOS / FASES
-- =========================================================
create table public.obras (
  id bigserial primary key,
  cliente_id bigint references public.clientes(id) on update cascade on delete restrict,
  titulo varchar(200) not null,
  endereco_obra text,
  status varchar(20) not null default 'AGUARDANDO'
    check (status in ('AGUARDANDO','INICIADO','PAUSADO','CANCELADO','CONCLUIDO')),
  ativo boolean not null default true,
  criado_em timestamptz not null default now()
);

create index idx_obras_cliente on public.obras(cliente_id);
create index idx_obras_status on public.obras(status);
create index idx_obras_ativo on public.obras(ativo);

create table public.orcamentos (
  id bigserial primary key,
  obra_id bigint not null references public.obras(id) on update cascade on delete cascade,
  versao int not null default 1,
  status varchar(20) not null default 'RASCUNHO'
    check (status in ('RASCUNHO','EMITIDO','APROVADO','REPROVADO','CANCELADO')),
  valor_total numeric(12,2) not null default 0,
  desconto_valor numeric(12,2) not null default 0,
  valor_total_final numeric(12,2) not null default 0,
  aprovado_em timestamptz,
  cancelado_em timestamptz,
  observacao text,
  criado_em timestamptz not null default now(),
  unique (obra_id, versao)
);

create index idx_orcamentos_obra on public.orcamentos(obra_id);
create index idx_orcamentos_status on public.orcamentos(status);

-- 1 APROVADO por obra
create unique index ux_orcamento_aprovado_por_obra
on public.orcamentos (obra_id)
where status='APROVADO';

create table public.obra_fases (
  id bigserial primary key,
  obra_id bigint not null references public.obras(id) on update cascade on delete cascade,
  orcamento_id bigint not null references public.orcamentos(id) on update cascade on delete cascade,
  nome_fase varchar(100) not null,
  ordem int not null default 1 check (ordem >= 1),
  status varchar(20) not null default 'PENDENTE'
    check (status in ('PENDENTE','EM_ANDAMENTO','CONCLUIDA')),
  valor_fase numeric(12,2) not null default 0,
  criado_em timestamptz not null default now(),
  constraint obra_fases_uniq unique (orcamento_id, ordem)
);

create index idx_fases_orcamento on public.obra_fases(orcamento_id);
create index idx_fases_obra on public.obra_fases(obra_id);

-- =========================================================
-- 6) SERVIÇOS (catálogo) + itens por fase
-- =========================================================
create table public.servicos (
  id bigserial primary key,
  nome varchar(200) not null unique,
  unidade varchar(10) not null default 'UN' check (unidade in ('UN','M2','ML','H','DIA')),
  ativo boolean not null default true,
  criado_em timestamptz not null default now()
);

create index idx_servicos_ativo on public.servicos(ativo);
create index idx_servicos_nome on public.servicos(nome);

create table public.orcamento_fase_servicos (
  id bigserial primary key,
  obra_fase_id bigint not null references public.obra_fases(id) on update cascade on delete cascade,
  servico_id bigint not null references public.servicos(id) on update cascade on delete restrict,
  quantidade numeric(10,2) not null default 1 check (quantidade > 0),
  valor_unit numeric(10,2) not null default 0 check (valor_unit >= 0),
  valor_total numeric(12,2) not null default 0 check (valor_total >= 0),
  observacao text,
  criado_em timestamptz not null default now(),
  unique (obra_fase_id, servico_id)
);

create index idx_ofs_fase on public.orcamento_fase_servicos(obra_fase_id);
create index idx_ofs_servico on public.orcamento_fase_servicos(servico_id);

-- =========================================================
-- 7) ALOCAÇÕES (planejamento diário) - sem "confirmada" no schema padrão
-- =========================================================
create table public.alocacoes (
  id bigserial primary key,
  data date not null,
  pessoa_id bigint references public.pessoas(id) on update cascade on delete restrict,
  obra_id bigint references public.obras(id) on update cascade on delete restrict,
  orcamento_id bigint references public.orcamentos(id) on update cascade on delete set null,
  obra_fase_id bigint references public.obra_fases(id) on update cascade on delete set null,
  periodo varchar(10) not null default 'INTEGRAL' check (periodo in ('INTEGRAL','MEIO')),
  tipo varchar(10) not null default 'INTERNO' check (tipo in ('INTERNO','EXTERNO')),
  observacao text,
  criado_em timestamptz not null default now()
);

create index idx_alocacoes_data on public.alocacoes(data);
create index idx_alocacoes_pessoa on public.alocacoes(pessoa_id);
create index idx_alocacoes_obra on public.alocacoes(obra_id);

-- (opcional) evitar duplicidade por pessoa/dia (ajuda a agenda 60+)
-- comente se quiser permitir múltiplas alocações no mesmo dia para a mesma pessoa
-- create unique index ux_aloc_pessoa_dia on public.alocacoes(pessoa_id, data);

-- =========================================================
-- 8) APONTAMENTOS (produção)
-- - regra: só permitido em orçamento APROVADO
-- - cálculo de acrescimo por tipo_dia
-- =========================================================
create table public.apontamentos (
  id bigserial primary key,
  obra_id bigint references public.obras(id) on update cascade on delete restrict,
  orcamento_id bigint references public.orcamentos(id) on update cascade on delete cascade,
  obra_fase_id bigint references public.obra_fases(id) on update cascade on delete set null,
  pessoa_id bigint references public.pessoas(id) on update cascade on delete restrict,
  data date not null,
  tipo_dia varchar(20) not null default 'NORMAL'
    check (tipo_dia in ('NORMAL','FERIADO','SABADO','DOMINGO')),
  valor_base numeric(10,2) not null default 0,
  acrescimo_pct numeric(5,2) not null default 0,
  desconto_valor numeric(10,2) not null default 0,
  valor_final numeric(10,2) not null default 0,
  observacao text,
  criado_em timestamptz not null default now()
);

create index idx_apont_data on public.apontamentos(data);
create index idx_apont_pessoa on public.apontamentos(pessoa_id);
create index idx_apont_orc on public.apontamentos(orcamento_id);
create index idx_apont_obra on public.apontamentos(obra_id);

-- Evita duplicidade básica (ajuste se quiser permitir mais de 1 por dia)
create unique index ux_apont_chave
on public.apontamentos (obra_id, pessoa_id, data, orcamento_id);

-- =========================================================
-- 9) RECEBIMENTOS (ADMIN) — por fase
-- =========================================================
create table public.recebimentos (
  id bigserial primary key,
  obra_fase_id bigint not null unique references public.obra_fases(id) on update cascade on delete cascade,
  valor numeric(12,2) not null default 0,
  vencimento date,
  recebido_em date,
  status varchar(20) not null default 'ABERTO'
    check (status in ('ABERTO','VENCIDO','PAGO','CANCELADO')),
  observacao text,
  criado_em timestamptz not null default now()
);

create index idx_receb_status on public.recebimentos(status);
create index idx_receb_venc on public.recebimentos(vencimento);

-- =========================================================
-- 10) PAGAMENTOS (ADMIN) + ITENS
-- =========================================================
create table public.pagamentos (
  id bigserial primary key,
  tipo varchar(20) not null default 'SEMANAL' check (tipo in ('SEMANAL','EXTRA','POR_FASE')),
  referencia_inicio date,
  referencia_fim date,
  obra_fase_id bigint references public.obra_fases(id) on update cascade on delete set null,
  valor_total numeric(12,2) not null default 0,
  status varchar(20) not null default 'PENDENTE' check (status in ('PENDENTE','PAGO','CANCELADO')),
  pago_em date,
  observacao text,
  criado_em timestamptz not null default now()
);

create index idx_pag_status on public.pagamentos(status);
create index idx_pag_ref on public.pagamentos(referencia_inicio, referencia_fim);

create table public.pagamento_itens (
  id bigserial primary key,
  pagamento_id bigint not null references public.pagamentos(id) on update cascade on delete cascade,
  apontamento_id bigint references public.apontamentos(id) on update cascade on delete set null,
  valor numeric(10,2) not null default 0,
  observacao text,
  criado_em timestamptz not null default now()
);

create index idx_pi_pag on public.pagamento_itens(pagamento_id);
create index idx_pi_apont on public.pagamento_itens(apontamento_id);

-- =========================================================
-- 11) FUNÇÕES / TRIGGERS: ORÇAMENTO (serviços → fase → orçamento)
-- =========================================================

-- 11.1 total item = quantidade * valor_unit
create or replace function public.fn_ofs_calc_total()
returns trigger
language plpgsql
as $$
begin
  new.valor_total := round(coalesce(new.quantidade,0) * coalesce(new.valor_unit,0), 2);
  return new;
end;
$$;

drop trigger if exists trg_ofs_calc_total on public.orcamento_fase_servicos;
create trigger trg_ofs_calc_total
before insert or update of quantidade, valor_unit
on public.orcamento_fase_servicos
for each row execute function public.fn_ofs_calc_total();

-- 11.2 Recalcular fase (soma dos itens)
create or replace function public.fn_recalcular_fase(p_fase_id bigint)
returns void
language plpgsql
as $$
begin
  update public.obra_fases f
     set valor_fase = coalesce((
       select round(sum(ofs.valor_total),2)
       from public.orcamento_fase_servicos ofs
       where ofs.obra_fase_id = f.id
     ), 0)
   where f.id = p_fase_id;
end;
$$;

-- 11.3 Recalcular orçamento (soma das fases) + desconto
create or replace function public.fn_recalcular_orcamento(p_orcamento_id bigint)
returns void
language plpgsql
as $$
declare
  v_total numeric(12,2);
  v_desc  numeric(12,2);
begin
  -- Recalcula valor_fase de todas as fases do orçamento (garante consistência)
  update public.obra_fases f
     set valor_fase = coalesce((
       select round(sum(ofs.valor_total),2)
       from public.orcamento_fase_servicos ofs
       where ofs.obra_fase_id = f.id
     ), 0)
   where f.orcamento_id = p_orcamento_id;

  select coalesce(round(sum(f.valor_fase),2),0)
    into v_total
  from public.obra_fases f
  where f.orcamento_id = p_orcamento_id;

  select coalesce(desconto_valor,0)
    into v_desc
  from public.orcamentos
  where id = p_orcamento_id;

  update public.orcamentos
     set valor_total = v_total,
         valor_total_final = greatest(0, round(v_total - greatest(0, v_desc), 2))
   where id = p_orcamento_id;
end;
$$;

-- 11.4 Trigger: mexeu em itens → recalcula fase e orçamento automaticamente
create or replace function public.trg_ofs_recalc_fase_orcamento()
returns trigger
language plpgsql
as $$
declare
  v_fase_id bigint;
  v_orc_id bigint;
begin
  v_fase_id := coalesce(new.obra_fase_id, old.obra_fase_id);

  select f.orcamento_id into v_orc_id
  from public.obra_fases f
  where f.id = v_fase_id;

  perform public.fn_recalcular_fase(v_fase_id);
  perform public.fn_recalcular_orcamento(v_orc_id);

  return coalesce(new, old);
end;
$$;

drop trigger if exists trg_ofs_recalc_fase_orcamento on public.orcamento_fase_servicos;
create trigger trg_ofs_recalc_fase_orcamento
after insert or update or delete
on public.orcamento_fase_servicos
for each row execute function public.trg_ofs_recalc_fase_orcamento();

-- 11.5 Trigger: mexeu no desconto → recalcula final
create or replace function public.trg_orcamento_recalc_on_desconto()
returns trigger
language plpgsql
as $$
begin
  perform public.fn_recalcular_orcamento(new.id);
  return new;
end;
$$;

drop trigger if exists trg_orcamento_recalc_on_desconto on public.orcamentos;
create trigger trg_orcamento_recalc_on_desconto
after update of desconto_valor
on public.orcamentos
for each row execute function public.trg_orcamento_recalc_on_desconto();

-- =========================================================
-- 12) GUARDS / CÁLCULOS: APONTAMENTOS
-- =========================================================

-- 12.1 Guard: apontamento só em orçamento APROVADO
create or replace function public.fn_guard_apontamento_orcamento_aprovado()
returns trigger
language plpgsql
as $$
declare
  v_status text;
begin
  select o.status into v_status
  from public.orcamentos o
  where o.id = new.orcamento_id;

  if v_status is null then
    raise exception 'Orçamento % não encontrado', new.orcamento_id;
  end if;

  if v_status <> 'APROVADO' then
    raise exception 'Só é permitido lançar apontamento em orçamento APROVADO. Status atual: %', v_status;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_guard_apontamento_orcamento on public.apontamentos;
create trigger trg_guard_apontamento_orcamento
before insert or update of orcamento_id
on public.apontamentos
for each row execute function public.fn_guard_apontamento_orcamento_aprovado();

-- 12.2 Cálculo: sábado 25%, domingo/feriado 100% (igual ao seu script anterior)
create or replace function public.fn_apontamento_calcula_valores()
returns trigger
language plpgsql
as $$
declare
  pct numeric(5,2);
  bruto numeric(10,2);
begin
  pct := case new.tipo_dia
    when 'SABADO'  then 0.25
    when 'DOMINGO' then 1.00
    when 'FERIADO' then 1.00
    else 0.00
  end;

  new.acrescimo_pct := pct;

  bruto := round(coalesce(new.valor_base,0) * (1 + pct), 2);
  new.valor_final := greatest(0, round(bruto - coalesce(new.desconto_valor,0), 2));

  return new;
end;
$$;

drop trigger if exists trg_apontamento_calcula_valores on public.apontamentos;
create trigger trg_apontamento_calcula_valores
before insert or update of tipo_dia, valor_base, desconto_valor
on public.apontamentos
for each row execute function public.fn_apontamento_calcula_valores();

-- =========================================================
-- 13) REGRAS: FASES x RECEBIMENTOS x APONTAMENTOS
-- =========================================================

-- 13.1 Bloquear delete de fase se houver apontamentos ou recebimento PAGO
create or replace function public.fn_fase_block_delete()
returns trigger
language plpgsql
as $$
begin
  if exists (select 1 from public.apontamentos a where a.obra_fase_id = old.id) then
    raise exception 'Não é possível excluir fase com apontamentos.';
  end if;

  if exists (select 1 from public.recebimentos r where r.obra_fase_id = old.id and r.status = 'PAGO') then
    raise exception 'Não é possível excluir fase com recebimento PAGO.';
  end if;

  return old;
end;
$$;

drop trigger if exists trg_fase_block_delete on public.obra_fases;
create trigger trg_fase_block_delete
before delete on public.obra_fases
for each row execute function public.fn_fase_block_delete();

-- 13.2 Não concluir fase se existir recebimento ABERTO/VENCIDO
create or replace function public.fn_fase_status_rules()
returns trigger
language plpgsql
as $$
begin
  if new.status = 'CONCLUIDA' and old.status is distinct from new.status then
    if exists (
      select 1
      from public.recebimentos r
      where r.obra_fase_id = new.id
        and r.status in ('ABERTO','VENCIDO')
    ) then
      raise exception 'Não é possível CONCLUIR fase com recebimentos ABERTOS/VENCIDOS (cancele ou pague).';
    end if;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_fase_status_rules on public.obra_fases;
create trigger trg_fase_status_rules
before update of status on public.obra_fases
for each row execute function public.fn_fase_status_rules();

-- =========================================================
-- 14) REGRAS: RECEBIMENTOS
-- - Só pode marcar PAGO se fase CONCLUIDA
-- - Não pode cancelar se já PAGO
-- - Se marcar PAGO e recebido_em estiver null, preenche
-- =========================================================
create or replace function public.fn_recebimento_rules()
returns trigger
language plpgsql
as $$
declare
  v_fase_status text;
begin
  if new.status = 'PAGO' and old.status is distinct from new.status then
    select f.status into v_fase_status
    from public.obra_fases f
    where f.id = new.obra_fase_id;

    if v_fase_status is null then
      raise exception 'Fase inválida para recebimento.';
    end if;

    if v_fase_status <> 'CONCLUIDA' then
      raise exception 'Só é permitido baixar recebimento (PAGO) quando a fase estiver CONCLUIDA. Fase: %', v_fase_status;
    end if;

    if new.recebido_em is null then
      new.recebido_em := current_date;
    end if;
  end if;

  if new.status = 'CANCELADO' and old.status is distinct from new.status then
    if old.status = 'PAGO' then
      raise exception 'Não é permitido cancelar recebimento já PAGO.';
    end if;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_recebimento_rules on public.recebimentos;
create trigger trg_recebimento_rules
before update of status on public.recebimentos
for each row execute function public.fn_recebimento_rules();

-- (opcional) Auto-marca como VENCIDO via VIEW (sem job)
-- Você pode também criar um job/cron depois, mas view já ajuda no painel.

-- =========================================================
-- 15) PAGAMENTOS: recalcular total automaticamente quando itens mudarem
-- =========================================================
create or replace function public.fn_pagamento_recalc_total(p_pagamento_id bigint)
returns void
language plpgsql
as $$
begin
  update public.pagamentos p
     set valor_total = coalesce((
       select round(sum(i.valor),2)
       from public.pagamento_itens i
       where i.pagamento_id = p.id
     ), 0)
   where p.id = p_pagamento_id;
end;
$$;

create or replace function public.trg_pagamento_itens_recalc_total()
returns trigger
language plpgsql
as $$
declare
  v_pag_id bigint;
begin
  v_pag_id := coalesce(new.pagamento_id, old.pagamento_id);
  perform public.fn_pagamento_recalc_total(v_pag_id);
  return coalesce(new, old);
end;
$$;

drop trigger if exists trg_pagamento_itens_recalc_total on public.pagamento_itens;
create trigger trg_pagamento_itens_recalc_total
after insert or update or delete
on public.pagamento_itens
for each row execute function public.trg_pagamento_itens_recalc_total();

-- =========================================================
-- 16) AUDITORIA AUTOMÁTICA (genérica)
-- - grava INSERT/UPDATE/DELETE em jsonb
-- - usuário: tenta pegar de usuarios_app; fallback auth.uid()
-- =========================================================
create or replace function public.fn_audit_trigger()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_usuario text;
  v_entidade text;
  v_id_text text;
begin
  -- Nome amigável, se existir
  select u.usuario into v_usuario
  from public.usuarios_app u
  where u.auth_user_id = auth.uid()
  limit 1;

  if v_usuario is null then
    v_usuario := coalesce(auth.uid()::text, 'SYSTEM');
  end if;

  v_entidade := tg_table_name;

  if tg_op = 'INSERT' then
    v_id_text := (to_jsonb(new)->>'id');
    insert into public.auditoria(usuario, entidade, entidade_id, acao, antes_json, depois_json)
    values (v_usuario, v_entidade, v_id_text, 'INSERT', null, to_jsonb(new));
    return new;

  elsif tg_op = 'UPDATE' then
    v_id_text := coalesce((to_jsonb(new)->>'id'), (to_jsonb(old)->>'id'));
    insert into public.auditoria(usuario, entidade, entidade_id, acao, antes_json, depois_json)
    values (v_usuario, v_entidade, v_id_text, 'UPDATE', to_jsonb(old), to_jsonb(new));
    return new;

  elsif tg_op = 'DELETE' then
    v_id_text := (to_jsonb(old)->>'id');
    insert into public.auditoria(usuario, entidade, entidade_id, acao, antes_json, depois_json)
    values (v_usuario, v_entidade, v_id_text, 'DELETE', to_jsonb(old), null);
    return old;
  end if;

  return null;
end;
$$;

-- Ative auditoria nas tabelas principais (ajuste se quiser menos log)
drop trigger if exists trg_audit_clientes on public.clientes;
create trigger trg_audit_clientes
after insert or update or delete on public.clientes
for each row execute function public.fn_audit_trigger();

drop trigger if exists trg_audit_pessoas on public.pessoas;
create trigger trg_audit_pessoas
after insert or update or delete on public.pessoas
for each row execute function public.fn_audit_trigger();

drop trigger if exists trg_audit_obras on public.obras;
create trigger trg_audit_obras
after insert or update or delete on public.obras
for each row execute function public.fn_audit_trigger();

drop trigger if exists trg_audit_orcamentos on public.orcamentos;
create trigger trg_audit_orcamentos
after insert or update or delete on public.orcamentos
for each row execute function public.fn_audit_trigger();

drop trigger if exists trg_audit_fases on public.obra_fases;
create trigger trg_audit_fases
after insert or update or delete on public.obra_fases
for each row execute function public.fn_audit_trigger();

drop trigger if exists trg_audit_servicos on public.servicos;
create trigger trg_audit_servicos
after insert or update or delete on public.servicos
for each row execute function public.fn_audit_trigger();

drop trigger if exists trg_audit_ofs on public.orcamento_fase_servicos;
create trigger trg_audit_ofs
after insert or update or delete on public.orcamento_fase_servicos
for each row execute function public.fn_audit_trigger();

drop trigger if exists trg_audit_alocacoes on public.alocacoes;
create trigger trg_audit_alocacoes
after insert or update or delete on public.alocacoes
for each row execute function public.fn_audit_trigger();

drop trigger if exists trg_audit_apontamentos on public.apontamentos;
create trigger trg_audit_apontamentos
after insert or update or delete on public.apontamentos
for each row execute function public.fn_audit_trigger();

drop trigger if exists trg_audit_recebimentos on public.recebimentos;
create trigger trg_audit_recebimentos
after insert or update or delete on public.recebimentos
for each row execute function public.fn_audit_trigger();

drop trigger if exists trg_audit_pagamentos on public.pagamentos;
create trigger trg_audit_pagamentos
after insert or update or delete on public.pagamentos
for each row execute function public.fn_audit_trigger();

drop trigger if exists trg_audit_pagamento_itens on public.pagamento_itens;
create trigger trg_audit_pagamento_itens
after insert or update or delete on public.pagamento_itens
for each row execute function public.fn_audit_trigger();

-- =========================================================
-- 17) VIEWS (ADMIN tende a usar; RLS ainda vale)
-- =========================================================

-- 17.1 Lucro real por obra (Recebimentos PAGO - Pagamentos PAGO)
create or replace view public.vw_lucro_por_obra as
with receb as (
  select
    o.id as obra_id,
    sum(r.valor) as total_recebido
  from public.recebimentos r
  join public.obra_fases f on f.id = r.obra_fase_id
  join public.orcamentos oc on oc.id = f.orcamento_id
  join public.obras o on o.id = oc.obra_id
  where r.status = 'PAGO'
  group by o.id
),
pag as (
  select
    a.obra_id,
    sum(pi.valor) as total_pago
  from public.pagamento_itens pi
  join public.pagamentos p on p.id = pi.pagamento_id
  join public.apontamentos a on a.id = pi.apontamento_id
  where p.status = 'PAGO'
  group by a.obra_id
)
select
  o.id as obra_id,
  o.titulo,
  coalesce(r.total_recebido, 0) as total_recebido,
  coalesce(p.total_pago, 0)     as total_pago,
  round(coalesce(r.total_recebido, 0) - coalesce(p.total_pago, 0), 2) as lucro_real
from public.obras o
left join receb r on r.obra_id = o.id
left join pag   p on p.obra_id = o.id;

-- 17.2 Financeiro por obra (orcado aprovado vs recebido/pago)
create or replace view public.vw_financeiro_por_obra as
with orc_aprovado as (
  select distinct on (obra_id)
    obra_id,
    valor_total_final
  from public.orcamentos
  where status = 'APROVADO'
  order by obra_id, versao desc
),
receb as (
  select
    o.id as obra_id,
    sum(r.valor) as recebido_pago
  from public.recebimentos r
  join public.obra_fases f on f.id = r.obra_fase_id
  join public.orcamentos oc on oc.id = f.orcamento_id
  join public.obras o on o.id = oc.obra_id
  where r.status = 'PAGO'
  group by o.id
),
pag as (
  select
    a.obra_id,
    sum(pi.valor) as pago_pago
  from public.pagamento_itens pi
  join public.pagamentos p on p.id = pi.pagamento_id
  join public.apontamentos a on a.id = pi.apontamento_id
  where p.status = 'PAGO'
  group by a.obra_id
)
select
  o.id as obra_id,
  o.titulo,
  oa.valor_total_final as valor_orcado,
  coalesce(r.recebido_pago, 0) as recebido_pago,
  coalesce(p.pago_pago, 0)     as pago_pago,
  round(coalesce(r.recebido_pago, 0) - coalesce(p.pago_pago, 0), 2) as saldo_real
from public.obras o
left join orc_aprovado oa on oa.obra_id = o.id
left join receb r on r.obra_id = o.id
left join pag   p on p.obra_id = o.id;

-- 17.3 Recebimentos “vencidos” (calculado)
create or replace view public.vw_recebimentos_vencidos as
select
  r.*,
  case
    when r.status in ('PAGO','CANCELADO') then false
    when r.vencimento is not null and r.vencimento < current_date then true
    else false
  end as esta_vencido_calculado
from public.recebimentos r;

-- 17.4 Desvio de orçamento (mão de obra paga vs orçamento aprovado)
create or replace view public.vw_desvio_orcamento as
with orc_aprovado as (
  select distinct on (obra_id)
    obra_id,
    valor_total_final
  from public.orcamentos
  where status = 'APROVADO'
  order by obra_id, versao desc
),
mao_obra as (
  select
    a.obra_id,
    sum(pi.valor) as total_mao_obra
  from public.pagamento_itens pi
  join public.pagamentos p on p.id = pi.pagamento_id
  join public.apontamentos a on a.id = pi.apontamento_id
  where p.status = 'PAGO'
  group by a.obra_id
)
select
  o.id as obra_id,
  o.titulo,
  oa.valor_total_final as valor_orcado,
  coalesce(m.total_mao_obra, 0) as mao_obra_real,
  round(coalesce(m.total_mao_obra, 0) - oa.valor_total_final, 2) as desvio
from public.obras o
join orc_aprovado oa on oa.obra_id = o.id
left join mao_obra m on m.obra_id = o.id;

-- =========================================================
-- 18) RLS (explícito e debugável)
-- =========================================================
alter table public.usuarios_app enable row level security;
alter table public.auditoria enable row level security;

alter table public.clientes enable row level security;
alter table public.pessoas enable row level security;
alter table public.obras enable row level security;
alter table public.orcamentos enable row level security;
alter table public.obra_fases enable row level security;
alter table public.servicos enable row level security;
alter table public.orcamento_fase_servicos enable row level security;
alter table public.alocacoes enable row level security;
alter table public.apontamentos enable row level security;

alter table public.recebimentos enable row level security;
alter table public.pagamentos enable row level security;
alter table public.pagamento_itens enable row level security;

-- --------- CONFIG (ADMIN only) ----------
create policy usuarios_app_admin_select
on public.usuarios_app for select
using (public.fn_is_admin());

create policy usuarios_app_admin_write
on public.usuarios_app for insert
with check (public.fn_is_admin());

create policy usuarios_app_admin_update
on public.usuarios_app for update
using (public.fn_is_admin())
with check (public.fn_is_admin());

create policy usuarios_app_admin_delete
on public.usuarios_app for delete
using (public.fn_is_admin());

create policy auditoria_admin_select
on public.auditoria for select
using (public.fn_is_admin());

create policy auditoria_admin_write
on public.auditoria for insert
with check (public.fn_is_admin());

-- --------- OPERACIONAL (ADMIN + OPERACAO) ----------
create policy clientes_all on public.clientes for all
using (public.fn_user_perfil() in ('ADMIN','OPERACAO'))
with check (public.fn_user_perfil() in ('ADMIN','OPERACAO'));

create policy pessoas_all on public.pessoas for all
using (public.fn_user_perfil() in ('ADMIN','OPERACAO'))
with check (public.fn_user_perfil() in ('ADMIN','OPERACAO'));

create policy obras_all on public.obras for all
using (public.fn_user_perfil() in ('ADMIN','OPERACAO'))
with check (public.fn_user_perfil() in ('ADMIN','OPERACAO'));

create policy orcamentos_all on public.orcamentos for all
using (public.fn_user_perfil() in ('ADMIN','OPERACAO'))
with check (public.fn_user_perfil() in ('ADMIN','OPERACAO'));

create policy fases_all on public.obra_fases for all
using (public.fn_user_perfil() in ('ADMIN','OPERACAO'))
with check (public.fn_user_perfil() in ('ADMIN','OPERACAO'));

create policy servicos_all on public.servicos for all
using (public.fn_user_perfil() in ('ADMIN','OPERACAO'))
with check (public.fn_user_perfil() in ('ADMIN','OPERACAO'));

create policy ofs_all on public.orcamento_fase_servicos for all
using (public.fn_user_perfil() in ('ADMIN','OPERACAO'))
with check (public.fn_user_perfil() in ('ADMIN','OPERACAO'));

create policy alocacoes_all on public.alocacoes for all
using (public.fn_user_perfil() in ('ADMIN','OPERACAO'))
with check (public.fn_user_perfil() in ('ADMIN','OPERACAO'));

create policy apontamentos_all on public.apontamentos for all
using (public.fn_user_perfil() in ('ADMIN','OPERACAO'))
with check (public.fn_user_perfil() in ('ADMIN','OPERACAO'));

-- --------- FINANCEIRO (ADMIN only) ----------
create policy recebimentos_admin_only on public.recebimentos for all
using (public.fn_is_admin())
with check (public.fn_is_admin());

create policy pagamentos_admin_only on public.pagamentos for all
using (public.fn_is_admin())
with check (public.fn_is_admin());

create policy pagamento_itens_admin_only on public.pagamento_itens for all
using (public.fn_is_admin())
with check (public.fn_is_admin());

commit;
