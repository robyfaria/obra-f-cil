begin;

-- =========================================================
-- 1) ALOCAÇÕES: adicionar campo confirmada
-- =========================================================
alter table public.alocacoes
add column if not exists confirmada boolean not null default false;

create index if not exists idx_alocacoes_confirmada on public.alocacoes(confirmada);

-- =========================================================
-- 2) APONTAMENTOS: adicionar colunas de rateio
-- =========================================================
alter table public.apontamentos
add column if not exists valor_bruto numeric(10,2) not null default 0;

alter table public.apontamentos
add column if not exists valor_rateado numeric(10,2) not null default 0;

-- (valor_final já existe no schema)
create index if not exists idx_apont_pessoa_data on public.apontamentos(pessoa_id, data);

-- =========================================================
-- 3) APONTAMENTOS: cálculo do bruto (antes de salvar)
-- - acrescimo_pct no seu modelo é fator (0.25 = 25%)
-- - valor_bruto = valor_base * (1 + acrescimo_pct)
-- =========================================================
create or replace function public.fn_apontamento_calc_bruto()
returns trigger
language plpgsql
as $$
begin
  if new.acrescimo_pct is null then new.acrescimo_pct := 0; end if;
  if new.desconto_valor is null then new.desconto_valor := 0; end if;
  if new.valor_base is null then new.valor_base := 0; end if;

  new.valor_bruto := round(new.valor_base * (1 + new.acrescimo_pct), 2);

  -- valor_rateado e valor_final serão recalculados no AFTER (rateio em grupo)
  return new;
end;
$$;

drop trigger if exists trg_apontamento_calc_bruto on public.apontamentos;
create trigger trg_apontamento_calc_bruto
before insert or update of valor_base, acrescimo_pct, desconto_valor, tipo_dia
on public.apontamentos
for each row execute function public.fn_apontamento_calc_bruto();

-- =========================================================
-- 4) APONTAMENTOS: recalcula rateio por (pessoa_id, data)
-- Regra:
-- n = total de apontamentos do mesmo profissional no mesmo dia
-- valor_rateado = valor_bruto / n
-- valor_final = max(0, valor_rateado - desconto_valor)
-- =========================================================
create or replace function public.fn_apontamento_recalcular_rateio(
  p_pessoa_id bigint,
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
  from public.apontamentos a
  where a.pessoa_id = p_pessoa_id
    and a.data = p_data;

  if v_n <= 0 then
    return;
  end if;

  update public.apontamentos a
     set valor_rateado = round(a.valor_bruto / v_n, 2),
         valor_final   = greatest(0, round((a.valor_bruto / v_n) - coalesce(a.desconto_valor,0), 2))
   where a.pessoa_id = p_pessoa_id
     and a.data = p_data;
end;
$$;

-- Trigger AFTER: recalcula grupo antigo e novo quando mudar pessoa/data
create or replace function public.trg_apontamento_recalc_rateio()
returns trigger
language plpgsql
as $$
begin
  if tg_op = 'INSERT' then
    perform public.fn_apontamento_recalcular_rateio(new.pessoa_id, new.data);
    return new;

  elsif tg_op = 'DELETE' then
    perform public.fn_apontamento_recalcular_rateio(old.pessoa_id, old.data);
    return old;

  elsif tg_op = 'UPDATE' then
    if (old.pessoa_id, old.data) is distinct from (new.pessoa_id, new.data) then
      perform public.fn_apontamento_recalcular_rateio(old.pessoa_id, old.data);
      perform public.fn_apontamento_recalcular_rateio(new.pessoa_id, new.data);
    else
      perform public.fn_apontamento_recalcular_rateio(new.pessoa_id, new.data);
    end if;
    return new;
  end if;

  return null;
end;
$$;

drop trigger if exists trg_apontamento_rateio_after on public.apontamentos;
create trigger trg_apontamento_rateio_after
after insert or update or delete on public.apontamentos
for each row execute function public.trg_apontamento_recalc_rateio();

-- =========================================================
-- 5) ALOCAÇÃO confirmada => gera apontamento
-- - Só quando confirmada mudar para true
-- - Usa pessoas.diaria_base como valor_base
-- - Exige obra_fase_id e orcamento_id coerentes
-- - Não duplica (usa unique existente: obra_id,pessoa_id,data,orcamento_id)
-- =========================================================
create or replace function public.fn_alocacao_confirmada_gera_apontamento()
returns trigger
language plpgsql
as $$
declare
  v_diaria numeric(10,2);
begin
  -- Só age quando confirmada muda para true
  if tg_op = 'UPDATE'
     and (old.confirmada is distinct from new.confirmada)
     and new.confirmada = true then

    if new.pessoa_id is null then
      raise exception 'Alocação sem pessoa_id não pode ser confirmada.';
    end if;

    if new.obra_id is null then
      raise exception 'Alocação sem obra_id não pode ser confirmada.';
    end if;

    if new.orcamento_id is null then
      raise exception 'Alocação sem orcamento_id não pode ser confirmada.';
    end if;

    if new.obra_fase_id is null then
      raise exception 'Alocação sem obra_fase_id não pode ser confirmada.';
    end if;

    -- diária base
    select p.diaria_base into v_diaria
    from public.pessoas p
    where p.id = new.pessoa_id;

    if v_diaria is null then
      raise exception 'Profissional sem diaria_base cadastrada. pessoa_id=%', new.pessoa_id;
    end if;

    -- cria apontamento (se já existir, não duplica)
    insert into public.apontamentos (
      obra_id, orcamento_id, obra_fase_id, pessoa_id,
      data, tipo_dia, valor_base, acrescimo_pct, desconto_valor
    )
    values (
      new.obra_id, new.orcamento_id, new.obra_fase_id, new.pessoa_id,
      new.data, 'NORMAL', v_diaria, 0, 0
    )
    on conflict (obra_id, pessoa_id, data, orcamento_id) do nothing;

  end if;

  return new;
end;
$$;

drop trigger if exists trg_alocacao_confirmada_gera_apontamento on public.alocacoes;
create trigger trg_alocacao_confirmada_gera_apontamento
after update of confirmada on public.alocacoes
for each row execute function public.fn_alocacao_confirmada_gera_apontamento();

-- =========================================================
-- 6) VIEW: apontamentos detalhados (conferência do rateio)
-- =========================================================
create or replace view public.vw_apontamentos_detalhados as
select
  a.data,
  p.nome as profissional,
  o.titulo as obra,
  f.nome_fase as fase,
  a.tipo_dia,
  a.valor_base,
  a.acrescimo_pct,
  a.desconto_valor,
  a.valor_bruto,
  a.valor_rateado,
  a.valor_final
from public.apontamentos a
join public.pessoas p on p.id = a.pessoa_id
join public.obras o on o.id = a.obra_id
left join public.obra_fases f on f.id = a.obra_fase_id;

commit;
