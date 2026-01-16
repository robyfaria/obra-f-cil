-- 🧾 SCRIPT SQL BASE (PRONTO PARA SUPABASE)
-- ⚠️ Esse script já assume Supabase Auth e multiempresa.
-- Você pode colar direto no SQL Editor do Supabase.
create extension if not exists pgcrypto;

-- =====================
-- EMPRESAS / MEMBROS
-- =====================
create table empresas (
  id uuid primary key default gen_random_uuid(),
  nome text not null,
  criado_em timestamptz not null default now()
);

create table membros_empresa (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references empresas(id),
  user_id uuid not null,
  perfil text not null check (perfil in ('ADMIN','OPERACAO')),
  ativo boolean not null default true,
  criado_em timestamptz not null default now(),
  unique (empresa_id, user_id)
);

-- =====================
-- CADASTROS
-- =====================
create table clientes (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references empresas(id),
  nome text not null,
  telefone text,
  endereco text,
  ativo boolean not null default true,
  criado_em timestamptz not null default now()
);

create table pessoas (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references empresas(id),
  nome text not null,
  tipo text not null check (tipo in ('PINTOR','AJUDANTE','TERCEIRO')),
  diaria_base numeric(12,2),
  ativo boolean not null default true
);

-- =====================
-- OBRAS / ORÇAMENTOS
-- =====================
create table obras (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references empresas(id),
  cliente_id uuid references clientes(id),
  titulo text not null,
  endereco text,
  status text not null check (status in ('AGUARDANDO','INICIADO','PAUSADO','CONCLUIDO','CANCELADO')),
  ativo boolean not null default true,
  criado_em timestamptz not null default now()
);

create table orcamentos (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references empresas(id),
  obra_id uuid not null references obras(id),
  versao int not null,
  status text not null check (status in ('RASCUNHO','EMITIDO','APROVADO','REPROVADO','CANCELADO')),
  valor_bruto numeric(12,2) default 0,
  desconto_valor numeric(12,2) default 0,
  valor_final numeric(12,2) default 0,
  emitido_em timestamptz,
  aprovado_em timestamptz,
  cancelado_em timestamptz,
  criado_em timestamptz not null default now(),
  unique (obra_id, versao)
);

create unique index ux_orcamento_aprovado_por_obra
on orcamentos(obra_id)
where status = 'APROVADO';

create table obra_fases (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references empresas(id),
  orcamento_id uuid not null references orcamentos(id),
  nome text not null,
  ordem int not null,
  status text not null check (status in ('AGUARDANDO','INICIADO','PAUSADO','CONCLUIDO','CANCELADO')),
  valor_fase numeric(12,2) default 0,
  criado_em timestamptz not null default now(),
  unique (orcamento_id, ordem)
);

create table servicos (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references empresas(id),
  nome text not null,
  unidade text not null check (unidade in ('UN','M2','ML','H','DIA')),
  ativo boolean not null default true,
  unique (empresa_id, nome)
);

create table orcamento_fase_servicos (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references empresas(id),
  obra_fase_id uuid not null references obra_fases(id) on delete cascade,
  servico_id uuid not null references servicos(id),
  quantidade numeric(12,2) not null,
  valor_unit numeric(12,2) not null,
  valor_total numeric(12,2) not null,
  unique (obra_fase_id, servico_id)
);

-- =====================
-- ALOCAÇÕES / APONTAMENTOS
-- =====================
create table alocacoes (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references empresas(id),
  data date not null,
  obra_id uuid not null references obras(id),
  fase_id uuid not null references obra_fases(id),
  pessoa_id uuid not null references pessoas(id),
  tipo text not null check (tipo in ('INTERNO','EXTERNO')),
  confirmada boolean not null default false,
  criado_em timestamptz not null default now(),
  unique (empresa_id, data, pessoa_id)
);

create table apontamentos (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references empresas(id),
  data date not null,
  obra_id uuid not null references obras(id),
  fase_id uuid not null references obra_fases(id),
  pessoa_id uuid not null references pessoas(id),
  tipo_dia text not null check (tipo_dia in ('NORMAL','SABADO','DOMINGO','FERIADO')),
  valor_base numeric(12,2) not null,
  acrescimo_pct numeric(5,2) not null default 0,
  desconto numeric(12,2) not null default 0,
  valor_bruto numeric(12,2),
  valor_rateado numeric(12,2),
  valor_final numeric(12,2),
  criado_em timestamptz not null default now(),
  unique (empresa_id, data, pessoa_id, fase_id)
);

-- =====================
-- FINANCEIRO
-- =====================
create table recebimentos (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references empresas(id),
  fase_id uuid not null unique references obra_fases(id),
  valor_previsto numeric(12,2) not null,
  data_vencimento date,
  valor_pago numeric(12,2),
  data_pagamento date,
  status text not null check (status in ('ABERTO','VENCIDO','PAGO','CANCELADO')),
  criado_em timestamptz not null default now()
);

create table pagamentos (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references empresas(id),
  tipo text not null check (tipo in ('SEMANAL','EXTRA','POR_FASE')),
  data_referencia date not null,
  valor_total numeric(12,2) not null,
  status text not null check (status in ('ABERTO','PAGO','CANCELADO')),
  criado_em timestamptz not null default now()
);

create table pagamento_itens (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references empresas(id),
  pagamento_id uuid not null references pagamentos(id) on delete cascade,
  apontamento_id uuid not null references apontamentos(id),
  valor numeric(12,2) not null
);

-- =====================
-- AUDITORIA
-- =====================
create table auditoria (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid,
  user_id uuid,
  entidade text not null,
  entidade_id uuid,
  acao text not null,
  antes_json jsonb,
  depois_json jsonb,
  criado_em timestamptz not null default now()
);

-- 1) APONTAMENTOS: guard + cálculo bruto + rateio (Regra A)
-- ✅ Regra A implementada
-- valor_bruto = round(valor_base * (1 + acrescimo_pct/100), 2)
-- n = total de apontamentos do mesmo profissional no mesmo dia (empresa + pessoa + data)
-- valor_rateado = round(valor_bruto / n, 2)
-- valor_final = greatest(0, round(valor_rateado - desconto, 2))
-- Recalcula sempre após insert/update/delete, e também quando muda data ou pessoa_id.
-- =========================
-- APONTAMENTOS: GUARD (só em orçamento APROVADO)
-- =========================
create or replace function fn_guard_apontamento_orcamento_aprovado()
returns trigger
language plpgsql
as $$
declare
  v_status text;
begin
  select o.status
    into v_status
  from obra_fases f
  join orcamentos o on o.id = f.orcamento_id
  where f.id = new.fase_id;

  if v_status is null then
    raise exception 'Fase inválida (não encontrada).';
  end if;

  if v_status <> 'APROVADO' then
    raise exception 'Apontamento permitido somente em fase de orçamento APROVADO. Status atual: %', v_status;
  end if;

  -- (Opcional, mas recomendado) garantir coerência de empresa
  if exists (
    select 1
    from obra_fases f
    where f.id = new.fase_id and f.empresa_id <> new.empresa_id
  ) then
    raise exception 'empresa_id do apontamento difere da fase.';
  end if;

  return new;
end;
$$;

-- =========================
-- APONTAMENTOS: CÁLCULO DO BRUTO (antes de salvar)
-- =========================
create or replace function fn_apontamento_calc_bruto()
returns trigger
language plpgsql
as $$
begin
  if new.acrescimo_pct is null then new.acrescimo_pct := 0; end if;
  if new.desconto is null then new.desconto := 0; end if;

  -- acrescimo_pct é percentual (ex.: 50 = 50%)
  new.valor_bruto := round(new.valor_base * (1 + (new.acrescimo_pct / 100.0)), 2);

  -- rateio e final serão recalculados em trigger AFTER (para todo o grupo do dia)
  return new;
end;
$$;

-- =========================
-- APONTAMENTOS: RECALCULA RATEIO PARA (empresa, pessoa, data)
-- =========================
create or replace function fn_apontamento_recalcular_rateio(
  p_empresa uuid,
  p_pessoa uuid,
  p_data date
)
returns void
language plpgsql
as $$
declare
  v_n int;
begin
  select count(*)
    into v_n
  from apontamentos a
  where a.empresa_id = p_empresa
    and a.pessoa_id  = p_pessoa
    and a.data       = p_data;

  if v_n <= 0 then
    return;
  end if;

  update apontamentos a
     set valor_rateado = round(a.valor_bruto / v_n, 2),
         valor_final   = greatest(0, round((a.valor_bruto / v_n) - a.desconto, 2))
   where a.empresa_id = p_empresa
     and a.pessoa_id  = p_pessoa
     and a.data       = p_data;
end;
$$;

-- =========================
-- APONTAMENTOS: TRIGGER AFTER (recalcula grupo antigo e novo)
-- =========================
create or replace function trg_apontamento_recalc_rateio()
returns trigger
language plpgsql
as $$
begin
  if tg_op = 'INSERT' then
    perform fn_apontamento_recalcular_rateio(new.empresa_id, new.pessoa_id, new.data);
    return new;

  elsif tg_op = 'DELETE' then
    perform fn_apontamento_recalcular_rateio(old.empresa_id, old.pessoa_id, old.data);
    return old;

  elsif tg_op = 'UPDATE' then
    -- Se mudou pessoa/data, recalcula o grupo antigo e o novo
    if (old.empresa_id, old.pessoa_id, old.data) is distinct from (new.empresa_id, new.pessoa_id, new.data) then
      perform fn_apontamento_recalcular_rateio(old.empresa_id, old.pessoa_id, old.data);
      perform fn_apontamento_recalcular_rateio(new.empresa_id, new.pessoa_id, new.data);
    else
      perform fn_apontamento_recalcular_rateio(new.empresa_id, new.pessoa_id, new.data);
    end if;
    return new;
  end if;

  return null;
end;
$$;

-- === Triggers na tabela apontamentos ===
drop trigger if exists trg_guard_apontamento_orcamento on apontamentos;
create trigger trg_guard_apontamento_orcamento
before insert or update on apontamentos
for each row execute function fn_guard_apontamento_orcamento_aprovado();

drop trigger if exists trg_apontamento_calc_bruto on apontamentos;
create trigger trg_apontamento_calc_bruto
before insert or update on apontamentos
for each row execute function fn_apontamento_calc_bruto();

drop trigger if exists trg_apontamento_rateio_after on apontamentos;
create trigger trg_apontamento_rateio_after
after insert or update or delete on apontamentos
for each row execute function trg_apontamento_recalc_rateio();

-- 2) FASE: travas + cancelamento que cancela recebimentos abertos
-- Regras implementadas
-- ❌ Não excluir fase se houver apontamento
-- ❌ Não excluir fase se houver recebimento PAGO
-- ❌ Não cancelar fase se houver recebimento PAGO
-- ✅ Cancelar fase → cancela recebimentos ABERTO/VENCIDO
-- ❌ Não concluir fase se houver recebimento ABERTO/VENCIDO (não cancelado)
-- =========================
-- FASE: BLOQUEIOS EM DELETE
-- =========================
create or replace function fn_fase_block_delete()
returns trigger
language plpgsql
as $$
begin
  if exists (select 1 from apontamentos a where a.fase_id = old.id) then
    raise exception 'Não é possível excluir fase com apontamentos.';
  end if;

  if exists (select 1 from recebimentos r where r.fase_id = old.id and r.status = 'PAGO') then
    raise exception 'Não é possível excluir fase com recebimento PAGO.';
  end if;

  return old;
end;
$$;

-- =========================
-- FASE: REGRAS EM MUDANÇA DE STATUS
-- =========================
create or replace function fn_fase_status_rules()
returns trigger
language plpgsql
as $$
begin
  -- Cancelar fase
  if new.status = 'CANCELADO' and old.status is distinct from new.status then
    if exists (select 1 from recebimentos r where r.fase_id = new.id and r.status = 'PAGO') then
      raise exception 'Não é possível CANCELAR fase com recebimento PAGO.';
    end if;

    -- Cancela recebimentos abertos/vencidos
    update recebimentos
       set status = 'CANCELADO'
     where fase_id = new.id
       and status in ('ABERTO','VENCIDO');
  end if;

  -- Concluir fase
  if new.status = 'CONCLUIDO' and old.status is distinct from new.status then
    if exists (select 1 from recebimentos r where r.fase_id = new.id and r.status in ('ABERTO','VENCIDO')) then
      raise exception 'Não é possível CONCLUIR fase com recebimentos ABERTOS/VENCIDOS (cancele ou pague).';
    end if;
  end if;

  return new;
end;
$$;

-- === Triggers em obra_fases ===
drop trigger if exists trg_fase_block_delete on obra_fases;
create trigger trg_fase_block_delete
before delete on obra_fases
for each row execute function fn_fase_block_delete();

drop trigger if exists trg_fase_status_rules on obra_fases;
create trigger trg_fase_status_rules
before update of status on obra_fases
for each row execute function fn_fase_status_rules();

-- 3) RECEBIMENTOS: baixar só se fase CONCLUÍDA + cancelar se não PAGO
-- Regras implementadas
-- ✅ Pode criar previsão desde o início (ABERTO/VENCIDO)
-- ❌ Só pode marcar PAGO se a fase estiver CONCLUIDA
-- ✅ Cancelar sempre, exceto se já for PAGO
-- =========================
-- RECEBIMENTOS: REGRAS DE STATUS (PAGO/CANCELADO)
-- =========================
create or replace function fn_recebimento_rules()
returns trigger
language plpgsql
as $$
declare
  v_fase_status text;
begin
  -- Pagar
  if new.status = 'PAGO' and old.status is distinct from new.status then
    select f.status into v_fase_status
      from obra_fases f
     where f.id = new.fase_id;

    if v_fase_status is null then
      raise exception 'Fase inválida para recebimento.';
    end if;

    if v_fase_status <> 'CONCLUIDO' then
      raise exception 'Só é permitido baixar recebimento (PAGO) quando a fase estiver CONCLUIDA. Fase: %', v_fase_status;
    end if;

    if new.data_pagamento is null then
      new.data_pagamento := current_date;
    end if;

    if new.valor_pago is null then
      new.valor_pago := new.valor_previsto;
    end if;
  end if;

  -- Cancelar
  if new.status = 'CANCELADO' and old.status is distinct from new.status then
    if old.status = 'PAGO' then
      raise exception 'Não é permitido cancelar recebimento já PAGO.';
    end if;
  end if;

  return new;
end;
$$;

-- === Trigger em recebimentos ===
drop trigger if exists trg_recebimento_rules on recebimentos;
create trigger trg_recebimento_rules
before update of status on recebimentos
for each row execute function fn_recebimento_rules();

-- 1) ✅ Alocação confirmada → gera apontamento
-- Regra: quando alocacoes.confirmada mudar para true, cria 1 apontamento (se ainda não existir) para aquele empresa_id + data + pessoa_id + fase_id.
-- tipo_dia padrão: NORMAL
-- valor_base: usa pessoas.diaria_base (obrigatório estar preenchido, senão bloqueia)
create or replace function fn_alocacao_confirmada_gera_apontamento()
returns trigger
language plpgsql
as $$
declare
  v_diaria numeric(12,2);
begin
  -- Só age quando confirmada muda para true
  if (tg_op = 'UPDATE')
     and (old.confirmada is distinct from new.confirmada)
     and (new.confirmada = true) then

    -- Pega diária base do profissional
    select p.diaria_base
      into v_diaria
    from pessoas p
    where p.id = new.pessoa_id
      and p.empresa_id = new.empresa_id;

    if v_diaria is null then
      raise exception 'Profissional sem diaria_base cadastrada. pessoa_id=%', new.pessoa_id;
    end if;

    -- Insere apontamento se não existir (evita duplicidade)
    insert into apontamentos (
      empresa_id, data, obra_id, fase_id, pessoa_id,
      tipo_dia, valor_base, acrescimo_pct, desconto
    )
    values (
      new.empresa_id, new.data, new.obra_id, new.fase_id, new.pessoa_id,
      'NORMAL', v_diaria, 0, 0
    )
    on conflict (empresa_id, data, pessoa_id, fase_id) do nothing;

    -- Obs: os triggers de guard/cálculo/rateio que você já instalou
    -- vão rodar automaticamente ao inserir o apontamento.
  end if;

  return new;
end;
$$;

drop trigger if exists trg_alocacao_confirmada_gera_apontamento on alocacoes;
create trigger trg_alocacao_confirmada_gera_apontamento
after update of confirmada on alocacoes
for each row
execute function fn_alocacao_confirmada_gera_apontamento();

-- 2) ✅ Função: gerar pagamentos semanais (SEMANAL) a partir de apontamentos
-- O que faz:
-- Cria 1 registro em pagamentos (tipo SEMANAL, status ABERTO) para a empresa e período
-- Inclui em pagamento_itens todos os apontamentos ainda não pagos (não vinculados) no intervalo
-- Atualiza pagamentos.valor_total
-- Importante: para evitar duplicidade, ele ignora apontamentos que já aparecem em pagamento_itens.
create or replace function fn_gerar_pagamento_semanal(
  p_empresa_id uuid,
  p_inicio date,
  p_fim date
)
returns uuid
language plpgsql
as $$
declare
  v_pagamento_id uuid;
begin
  if p_inicio is null or p_fim is null or p_fim < p_inicio then
    raise exception 'Intervalo inválido (p_inicio/p_fim).';
  end if;

  -- Cria o pagamento semanal (um por intervalo e empresa)
  insert into pagamentos (empresa_id, tipo, data_referencia, valor_total, status)
  values (p_empresa_id, 'SEMANAL', p_fim, 0, 'ABERTO')
  returning id into v_pagamento_id;

  -- Insere itens (apontamentos ainda não vinculados a nenhum pagamento)
  insert into pagamento_itens (empresa_id, pagamento_id, apontamento_id, valor)
  select
    a.empresa_id,
    v_pagamento_id,
    a.id,
    a.valor_final
  from apontamentos a
  left join pagamento_itens pi on pi.apontamento_id = a.id
  where a.empresa_id = p_empresa_id
    and a.data between p_inicio and p_fim
    and pi.id is null;

  -- Atualiza total
  update pagamentos p
     set valor_total = coalesce((
       select sum(i.valor)
       from pagamento_itens i
       where i.pagamento_id = p.id
     ), 0)
   where p.id = v_pagamento_id;

  return v_pagamento_id;
end;
$$;

-- 3) ✅ Auditoria genérica (com auth.uid() + empresa_id automático)
-- O que faz:
-- Em qualquer tabela com coluna id e (idealmente) empresa_id, grava:
-- user_id = auth.uid()
-- empresa_id = NEW.empresa_id ou OLD.empresa_id (se existir)
-- antes_json / depois_json com to_jsonb(OLD/NEW)
-- Isso é “plugável”: você cria o trigger nas tabelas que quiser auditar.
create or replace function fn_audit_trigger()
returns trigger
language plpgsql
as $$
declare
  v_empresa_id uuid;
  v_user_id uuid;
  v_entidade_id uuid;
begin
  -- user do Supabase Auth (null se rodar como service_role / jobs)
  v_user_id := auth.uid();

  -- tenta capturar empresa_id (se existir no registro)
  if tg_op = 'INSERT' then
    begin
      v_empresa_id := (to_jsonb(new)->>'empresa_id')::uuid;
    exception when others then
      v_empresa_id := null;
    end;
    v_entidade_id := (to_jsonb(new)->>'id')::uuid;

    insert into auditoria (empresa_id, user_id, entidade, entidade_id, acao, antes_json, depois_json)
    values (v_empresa_id, v_user_id, tg_table_name, v_entidade_id, 'INSERT', null, to_jsonb(new));

    return new;

  elsif tg_op = 'UPDATE' then
    begin
      v_empresa_id := coalesce(
        (to_jsonb(new)->>'empresa_id')::uuid,
        (to_jsonb(old)->>'empresa_id')::uuid
      );
    exception when others then
      v_empresa_id := null;
    end;
    v_entidade_id := coalesce(
      (to_jsonb(new)->>'id')::uuid,
      (to_jsonb(old)->>'id')::uuid
    );

    insert into auditoria (empresa_id, user_id, entidade, entidade_id, acao, antes_json, depois_json)
    values (v_empresa_id, v_user_id, tg_table_name, v_entidade_id, 'UPDATE', to_jsonb(old), to_jsonb(new));

    return new;

  elsif tg_op = 'DELETE' then
    begin
      v_empresa_id := (to_jsonb(old)->>'empresa_id')::uuid;
    exception when others then
      v_empresa_id := null;
    end;
    v_entidade_id := (to_jsonb(old)->>'id')::uuid;

    insert into auditoria (empresa_id, user_id, entidade, entidade_id, acao, antes_json, depois_json)
    values (v_empresa_id, v_user_id, tg_table_name, v_entidade_id, 'DELETE', to_jsonb(old), null);

    return old;
  end if;

  return null;
end;
$$;

-- Exemplos de triggers (ative nas tabelas principais)
-- Você pode ajustar a lista conforme quiser.

drop trigger if exists trg_audit_clientes on clientes;
create trigger trg_audit_clientes
after insert or update or delete on clientes
for each row execute function fn_audit_trigger();

drop trigger if exists trg_audit_pessoas on pessoas;
create trigger trg_audit_pessoas
after insert or update or delete on pessoas
for each row execute function fn_audit_trigger();

drop trigger if exists trg_audit_obras on obras;
create trigger trg_audit_obras
after insert or update or delete on obras
for each row execute function fn_audit_trigger();

drop trigger if exists trg_audit_orcamentos on orcamentos;
create trigger trg_audit_orcamentos
after insert or update or delete on orcamentos
for each row execute function fn_audit_trigger();

drop trigger if exists trg_audit_fases on obra_fases;
create trigger trg_audit_fases
after insert or update or delete on obra_fases
for each row execute function fn_audit_trigger();

drop trigger if exists trg_audit_alocacoes on alocacoes;
create trigger trg_audit_alocacoes
after insert or update or delete on alocacoes
for each row execute function fn_audit_trigger();

drop trigger if exists trg_audit_apontamentos on apontamentos;
create trigger trg_audit_apontamentos
after insert or update or delete on apontamentos
for each row execute function fn_audit_trigger();

drop trigger if exists trg_audit_recebimentos on recebimentos;
create trigger trg_audit_recebimentos
after insert or update or delete on recebimentos
for each row execute function fn_audit_trigger();

drop trigger if exists trg_audit_pagamentos on pagamentos;
create trigger trg_audit_pagamentos
after insert or update or delete on pagamentos
for each row execute function fn_audit_trigger();

-- 1) 🔒 Travar alterações retroativas em fase/serviços se já existirem apontamentos
-- 1.1 Bloquear update “estrutural” da fase quando houver apontamentos
-- Permite mudar status, mas bloqueia mudar nome/ordem/valor_fase/orcamento_id se já houve trabalho real.
create or replace function fn_fase_block_structural_update_if_apontado()
returns trigger
language plpgsql
as $$
begin
  -- Só bloqueia alterações estruturais (status continua livre, regido por suas regras)
  if exists (select 1 from apontamentos a where a.fase_id = new.id) then
    if (old.nome, old.ordem, old.valor_fase, old.orcamento_id)
       is distinct from
       (new.nome, new.ordem, new.valor_fase, new.orcamento_id) then
      raise exception 'Fase com apontamentos: alterações estruturais não permitidas (nome/ordem/valor_fase/orcamento).';
    end if;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_fase_block_structural_update_if_apontado on obra_fases;
create trigger trg_fase_block_structural_update_if_apontado
before update on obra_fases
for each row
execute function fn_fase_block_structural_update_if_apontado();

-- 1.2 Bloquear update/delete em serviços por fase quando houver apontamentos
-- Como apontamento é “por fase”, a trava é por obra_fase_id.
create or replace function fn_ofs_block_change_if_apontado()
returns trigger
language plpgsql
as $$
declare
  v_fase_id uuid;
begin
  v_fase_id := coalesce(new.obra_fase_id, old.obra_fase_id);

  if exists (select 1 from apontamentos a where a.fase_id = v_fase_id) then
    raise exception 'Fase com apontamentos: não é permitido alterar/excluir itens de serviços desta fase.';
  end if;

  return coalesce(new, old);
end;
$$;

drop trigger if exists trg_ofs_block_change_if_apontado on orcamento_fase_servicos;
create trigger trg_ofs_block_change_if_apontado
before update or delete on orcamento_fase_servicos
for each row
execute function fn_ofs_block_change_if_apontado();

-- 2) 🧮 Recalcular orçamento automaticamente (serviços → fase → orçamento)
-- 2.1 Cálculo do valor_total do item (quantidade * valor_unit)
-- Antes de salvar.
create or replace function fn_ofs_calc_total()
returns trigger
language plpgsql
as $$
begin
  new.valor_total := round(new.quantidade * new.valor_unit, 2);
  return new;
end;
$$;

drop trigger if exists trg_ofs_calc_total on orcamento_fase_servicos;
create trigger trg_ofs_calc_total
before insert or update on orcamento_fase_servicos
for each row
execute function fn_ofs_calc_total();

-- 2.2 Recalcular fase (soma dos serviços)
-- Atualiza obra_fases.valor_fase = soma orcamento_fase_servicos.valor_total.
create or replace function fn_recalcular_fase(p_fase_id uuid)
returns void
language plpgsql
as $$
begin
  update obra_fases f
     set valor_fase = coalesce((
       select sum(ofs.valor_total)
       from orcamento_fase_servicos ofs
       where ofs.obra_fase_id = f.id
     ), 0)
   where f.id = p_fase_id;
end;
$$;

-- 2.3 Recalcular orçamento (soma das fases) + aplicar desconto
-- valor_bruto = soma valor_fase das fases do orçamento
-- valor_final = greatest(0, valor_bruto - desconto_valor)
create or replace function fn_recalcular_orcamento(p_orcamento_id uuid)
returns void
language plpgsql
as $$
declare
  v_bruto numeric(12,2);
  v_desc  numeric(12,2);
begin
  select coalesce(sum(f.valor_fase), 0)
    into v_bruto
  from obra_fases f
  where f.orcamento_id = p_orcamento_id;

  select coalesce(o.desconto_valor, 0)
    into v_desc
  from orcamentos o
  where o.id = p_orcamento_id;

  update orcamentos o
     set valor_bruto = round(v_bruto, 2),
         valor_final = round(greatest(0, v_bruto - v_desc), 2)
   where o.id = p_orcamento_id;
end;
$$;

-- 2.4 Trigger: ao mexer em itens de serviço, recalcular fase e orçamento
-- Funciona para INSERT/UPDATE/DELETE.
create or replace function trg_ofs_recalc_fase_orcamento()
returns trigger
language plpgsql
as $$
declare
  v_fase_id uuid;
  v_orcamento_id uuid;
begin
  v_fase_id := coalesce(new.obra_fase_id, old.obra_fase_id);

  select f.orcamento_id into v_orcamento_id
  from obra_fases f
  where f.id = v_fase_id;

  perform fn_recalcular_fase(v_fase_id);
  perform fn_recalcular_orcamento(v_orcamento_id);

  return coalesce(new, old);
end;
$$;

drop trigger if exists trg_ofs_recalc_fase_orcamento on orcamento_fase_servicos;
create trigger trg_ofs_recalc_fase_orcamento
after insert or update or delete on orcamento_fase_servicos
for each row
execute function trg_ofs_recalc_fase_orcamento();

-- 2.5 Trigger: se editar desconto do orçamento, recalcular final
-- Pra manter valor_final correto quando mexer em desconto_valor.
create or replace function trg_orcamento_recalc_on_desconto()
returns trigger
language plpgsql
as $$
begin
  perform fn_recalcular_orcamento(new.id);
  return new;
end;
$$;

drop trigger if exists trg_orcamento_recalc_on_desconto on orcamentos;
create trigger trg_orcamento_recalc_on_desconto
after update of desconto_valor on orcamentos
for each row
execute function trg_orcamento_recalc_on_desconto();

-- 3) 💵 Pagamentos: marcar como PAGO + estornar (sem “reabrir PAGO”)
-- A regra que você quer é: não reabre pagamento PAGO.
-- Então o “estorno” vira um pagamento EXTRA separado com valores negativos (histórico perfeito e auditável).
-- 3.1 Marcar pagamento como PAGO
-- Só permite se status = ABERTO
-- Opcional: recalcula total antes de pagar
create or replace function fn_marcar_pagamento_pago(p_pagamento_id uuid)
returns void
language plpgsql
as $$
declare
  v_status text;
begin
  select status into v_status
  from pagamentos
  where id = p_pagamento_id;

  if v_status is null then
    raise exception 'Pagamento não encontrado.';
  end if;

  if v_status <> 'ABERTO' then
    raise exception 'Só é permitido pagar pagamentos em ABERTO. Status atual: %', v_status;
  end if;

  -- garante total consistente
  update pagamentos p
     set valor_total = coalesce((
       select sum(i.valor)
       from pagamento_itens i
       where i.pagamento_id = p.id
     ), 0)
   where p.id = p_pagamento_id;

  update pagamentos
     set status = 'PAGO'
   where id = p_pagamento_id;
end;
$$;

-- 3.2 Estornar pagamento PAGO criando um EXTRA negativo
-- Só permite se o original está PAGO
-- Cria um novo pagamento EXTRA (ABERTO) com total negativo
-- Cria itens negativos espelhando os itens do pago
-- Não altera o pagamento original (não “reabre”)
create or replace function fn_estornar_pagamento(p_pagamento_id uuid)
returns uuid
language plpgsql
as $$
declare
  v_status text;
  v_empresa uuid;
  v_novo_id uuid;
begin
  select status, empresa_id into v_status, v_empresa
  from pagamentos
  where id = p_pagamento_id;

  if v_status is null then
    raise exception 'Pagamento não encontrado.';
  end if;

  if v_status <> 'PAGO' then
    raise exception 'Estorno só é permitido para pagamento PAGO. Status atual: %', v_status;
  end if;

  -- Cria pagamento EXTRA (negativo)
  insert into pagamentos (empresa_id, tipo, data_referencia, valor_total, status)
  values (v_empresa, 'EXTRA', current_date, 0, 'ABERTO')
  returning id into v_novo_id;

  -- Espelha itens com valor negativo
  insert into pagamento_itens (empresa_id, pagamento_id, apontamento_id, valor)
  select
    v_empresa,
    v_novo_id,
    i.apontamento_id,
    round(-1 * i.valor, 2)
  from pagamento_itens i
  where i.pagamento_id = p_pagamento_id;

  -- Atualiza total do EXTRA
  update pagamentos p
     set valor_total = coalesce((
       select sum(i.valor)
       from pagamento_itens i
       where i.pagamento_id = p.id
     ), 0)
   where p.id = v_novo_id;

  return v_novo_id;
end;
$$;

-- 1️⃣ 📊 View — Lucro por Obra (real, baseado em dinheiro pago)
-- Regra:
-- Lucro = Recebimentos PAGO − Pagamentos PAGO
create or replace view vw_lucro_por_obra with (security_invoker = true) as
with receb as (
  select
    f.id           as fase_id,
    o.id           as obra_id,
    o.empresa_id,
    sum(r.valor_pago) as total_recebido
  from recebimentos r
  join obra_fases f on f.id = r.fase_id
  join orcamentos oc on oc.id = f.orcamento_id
  join obras o on o.id = oc.obra_id
  where r.status = 'PAGO'
  group by f.id, o.id, o.empresa_id
),
pag as (
  select
    a.obra_id,
    p.empresa_id,
    sum(pi.valor) as total_pago
  from pagamento_itens pi
  join pagamentos p on p.id = pi.pagamento_id
  join apontamentos a on a.id = pi.apontamento_id
  where p.status = 'PAGO'
  group by a.obra_id, p.empresa_id
)
select
  o.empresa_id,
  o.id as obra_id,
  o.titulo,
  coalesce(r.total_recebido, 0) as total_recebido,
  coalesce(p.total_pago, 0)     as total_pago,
  round(coalesce(r.total_recebido, 0) - coalesce(p.total_pago, 0), 2) as lucro_real
from obras o
left join receb r on r.obra_id = o.id and r.empresa_id = o.empresa_id
left join pag   p on p.obra_id = o.id and p.empresa_id = o.empresa_id;

-- 2️⃣ 💰 View — Financeiro Consolidado por Obra (previsto x realizado)
-- Mostra:
-- Total previsto do orçamento aprovado
-- Total já recebido
-- Total já pago
-- Saldo financeiro real
create or replace view vw_financeiro_por_obra with (security_invoker = true) as
with orc_aprovado as (
  select distinct on (obra_id)
    obra_id,
    empresa_id,
    valor_final
  from orcamentos
  where status = 'APROVADO'
  order by obra_id, versao desc
),
receb as (
  select
    o.id as obra_id,
    o.empresa_id,
    sum(r.valor_pago) as recebido_pago
  from recebimentos r
  join obra_fases f on f.id = r.fase_id
  join orcamentos oc on oc.id = f.orcamento_id
  join obras o on o.id = oc.obra_id
  where r.status = 'PAGO'
  group by o.id, o.empresa_id
),
pag as (
  select
    a.obra_id,
    p.empresa_id,
    sum(pi.valor) as pago_pago
  from pagamento_itens pi
  join pagamentos p on p.id = pi.pagamento_id
  join apontamentos a on a.id = pi.apontamento_id
  where p.status = 'PAGO'
  group by a.obra_id, p.empresa_id
)
select
  o.empresa_id,
  o.id as obra_id,
  o.titulo,
  oa.valor_final        as valor_orcado,
  coalesce(r.recebido_pago, 0) as recebido_pago,
  coalesce(p.pago_pago, 0)     as pago_pago,
  round(coalesce(r.recebido_pago, 0) - coalesce(p.pago_pago, 0), 2) as saldo_real
from obras o
left join orc_aprovado oa on oa.obra_id = o.id and oa.empresa_id = o.empresa_id
left join receb r on r.obra_id = o.id and r.empresa_id = o.empresa_id
left join pag   p on p.obra_id = o.id and p.empresa_id = o.empresa_id;

-- 3️⃣ ⏰ View — Pendências do Dia (o que exige ação)
-- Centraliza:
-- Alocações não confirmadas hoje
-- Recebimentos vencidos
-- Fases bloqueadas por recebimentos
create or replace view vw_pendencias_hoje with (security_invoker = true) as
select
  'ALOCACAO' as tipo,
  a.empresa_id,
  a.id as referencia_id,
  a.data,
  p.nome as pessoa,
  o.titulo as obra,
  f.nome as fase,
  'Alocação não confirmada' as descricao
from alocacoes a
join pessoas p on p.id = a.pessoa_id
join obras o on o.id = a.obra_id
join obra_fases f on f.id = a.fase_id
where a.data = current_date
  and a.confirmada = false

union all

select
  'RECEBIMENTO' as tipo,
  r.empresa_id,
  r.id as referencia_id,
  r.data_vencimento as data,
  null as pessoa,
  o.titulo as obra,
  f.nome as fase,
  'Recebimento vencido' as descricao
from recebimentos r
join obra_fases f on f.id = r.fase_id
join orcamentos oc on oc.id = f.orcamento_id
join obras o on o.id = oc.obra_id
where r.status = 'VENCIDO'

union all

select
  'FASE' as tipo,
  f.empresa_id,
  f.id as referencia_id,
  null as data,
  null as pessoa,
  o.titulo as obra,
  f.nome as fase,
  'Fase bloqueada por recebimentos abertos' as descricao
from obra_fases f
join orcamentos oc on oc.id = f.orcamento_id
join obras o on o.id = oc.obra_id
where exists (
  select 1 from recebimentos r
  where r.fase_id = f.id
    and r.status in ('ABERTO','VENCIDO')
);

-- 4️⃣ 👷 View — Apontamentos por Profissional / Dia (auditoria do rateio)
-- Excelente para:
-- Conferir rateio
-- Conferir descontos
-- Conferir acréscimos
-- Resolver divergência com profissional
create or replace view vw_apontamentos_detalhados with (security_invoker = true) as
select
  a.empresa_id,
  a.data,
  p.nome as profissional,
  o.titulo as obra,
  f.nome as fase,
  a.tipo_dia,
  a.valor_base,
  a.acrescimo_pct,
  a.desconto,
  a.valor_bruto,
  a.valor_rateado,
  a.valor_final
from apontamentos a
join pessoas p on p.id = a.pessoa_id
join obras o on o.id = a.obra_id
join obra_fases f on f.id = a.fase_id;

-- 5️⃣ 📐 View — Orçamento: previsto x executado (desvio)
-- Mostra:
-- Valor orçado por obra
-- Quanto já foi pago (mão de obra)
-- Diferença (estouro / economia)
create or replace view vw_desvio_orcamento with (security_invoker = true) as
with orc_aprovado as (
  select distinct on (obra_id)
    obra_id,
    empresa_id,
    valor_final
  from orcamentos
  where status = 'APROVADO'
  order by obra_id, versao desc
),
mao_obra as (
  select
    a.obra_id,
    p.empresa_id,
    sum(pi.valor) as total_mao_obra
  from pagamento_itens pi
  join pagamentos p on p.id = pi.pagamento_id
  join apontamentos a on a.id = pi.apontamento_id
  where p.status = 'PAGO'
  group by a.obra_id, p.empresa_id
)
select
  o.empresa_id,
  o.id as obra_id,
  o.titulo,
  oa.valor_final as valor_orcado,
  coalesce(m.total_mao_obra, 0) as mao_obra_real,
  round(coalesce(m.total_mao_obra, 0) - oa.valor_final, 2) as desvio
from obras o
join orc_aprovado oa on oa.obra_id = o.id and oa.empresa_id = o.empresa_id
left join mao_obra m on m.obra_id = o.id and m.empresa_id = o.empresa_id;


-- 🧩 Funções auxiliares (reutilizáveis nas policies)
-- Crie primeiro estas funções:
-- Retorna true se o usuário logado é membro ativo da empresa
create or replace function public.fn_is_membro_empresa(p_empresa_id uuid)
returns boolean
language plpgsql
stable
security definer
set search_path = public, pg_temp
as $$
begin
  -- evita recursão/negação ao consultar membros_empresa sob RLS
  perform set_config('row_security', 'off', true);

  return exists (
    select 1
    from public.membros_empresa me
    where me.empresa_id = p_empresa_id
      and me.user_id = auth.uid()
      and me.ativo = true
  );
end;
$$;

-- Retorna true se o usuário logado é ADMIN da empresa
create or replace function public.fn_is_admin_empresa(p_empresa_id uuid)
returns boolean
language plpgsql
stable
security definer
set search_path = public, pg_temp
as $$
begin
  perform set_config('row_security', 'off', true);

  return exists (
    select 1
    from public.membros_empresa me
    where me.empresa_id = p_empresa_id
      and me.user_id = auth.uid()
      and me.ativo = true
      and me.perfil = 'ADMIN'
  );
end;
$$;

revoke all on function public.fn_is_membro_empresa(uuid) from public;
revoke all on function public.fn_is_admin_empresa(uuid) from public;

grant execute on function public.fn_is_membro_empresa(uuid) to authenticated;
grant execute on function public.fn_is_admin_empresa(uuid) to authenticated;

-- 🔐 Ativar RLS em todas as tabelas
alter table empresas enable row level security;
alter table membros_empresa enable row level security;
alter table clientes enable row level security;
alter table pessoas enable row level security;
alter table obras enable row level security;
alter table orcamentos enable row level security;
alter table obra_fases enable row level security;
alter table servicos enable row level security;
alter table orcamento_fase_servicos enable row level security;
alter table alocacoes enable row level security;
alter table apontamentos enable row level security;
alter table recebimentos enable row level security;
alter table pagamentos enable row level security;
alter table pagamento_itens enable row level security;
alter table auditoria enable row level security;

-- 🏢 Tabelas de controle (empresas / membros)
-- empresas
-- ADMIN pode ver sua empresa
create policy empresas_select
on empresas for select
using (fn_is_membro_empresa(id));

-- Somente ADMIN pode alterar
create policy empresas_admin_all
on empresas for all
using (fn_is_admin_empresa(id))
with check (fn_is_admin_empresa(id));

-- membros_empresa
-- Usuário pode ver apenas os vínculos da sua empresa
create policy membros_select
on membros_empresa for select
using (fn_is_membro_empresa(empresa_id));

-- Somente ADMIN pode gerenciar membros
create policy membros_admin_all
on membros_empresa for all
using (fn_is_admin_empresa(empresa_id))
with check (fn_is_admin_empresa(empresa_id));

-- 🧩 Tabelas operacionais (acesso para ADMIN e OPERACAO)
-- Regra: qualquer membro ativo da empresa pode operar.
-- Aplique esse padrão para todas as tabelas abaixo:

-- clientes
-- pessoas
-- obras
-- orcamentos
-- obra_fases
-- servicos
-- orcamento_fase_servicos
-- alocacoes
-- apontamentos


-- 💰 Tabelas financeiras (somente ADMIN)
-- recebimentos
-- pagamentos
-- pagamento_itens
-- Exemplo (recebimentos)
create policy recebimentos_admin_only
on recebimentos for all
using (fn_is_admin_empresa(empresa_id))
with check (fn_is_admin_empresa(empresa_id));
-- Repita o mesmo para pagamentos e pagamento_itens.

-- 💰 Tabelas financeiras (somente ADMIN)
-- recebimentos
-- pagamentos
-- pagamento_itens
-- Exemplo (recebimentos)
create policy recebimentos_admin_only
on recebimentos for all
using (fn_is_admin_empresa(empresa_id))
with check (fn_is_admin_empresa(empresa_id));
-- Repita o mesmo para pagamentos e pagamento_itens.

-- cria empresa
insert into empresas (nome) values ('Sepol Pinturas') returning id;

-- vínculo ADMIN (troque USER_ID_ADMIN)
insert into membros_empresa (empresa_id, user_id, perfil, ativo)
values (id, '', 'ADMIN', true);

-- vínculo OPERACAO (troque USER_ID_OPERACAO)
insert into membros_empresa (empresa_id, user_id, perfil, ativo)
values (id, '', 'OPERACAO', true);
