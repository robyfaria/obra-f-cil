begin;

-- =========================================================
-- 1) Substituir a função fn_apontamento_calcula_valores()
-- Agora ela só define acrescimo_pct com base no tipo_dia.
-- NÃO calcula valor_final.
-- =========================================================
create or replace function public.fn_apontamento_calcula_valores()
returns trigger
language plpgsql
as $$
declare
  pct numeric(5,2);
begin
  pct := case new.tipo_dia
    when 'SABADO'  then 0.25
    when 'DOMINGO' then 1.00
    when 'FERIADO' then 1.00
    else 0.00
  end;

  new.acrescimo_pct := pct;
  return new;
end;
$$;

-- Garante que o trigger aponta para a versão "nova"
drop trigger if exists trg_apontamento_calcula_valores on public.apontamentos;
create trigger trg_apontamento_calcula_valores
before insert or update of tipo_dia
on public.apontamentos
for each row execute function public.fn_apontamento_calcula_valores();

-- =========================================================
-- 2) Ajustar fn_apontamento_calc_bruto()
-- Agora ela usa o acrescimo_pct já definido e calcula só valor_bruto.
-- NÃO calcula valor_final.
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

  return new;
end;
$$;

-- Recria trigger do bruto (se já existir, ok)
drop trigger if exists trg_apontamento_calc_bruto on public.apontamentos;
create trigger trg_apontamento_calc_bruto
before insert or update of valor_base, acrescimo_pct, desconto_valor, tipo_dia
on public.apontamentos
for each row execute function public.fn_apontamento_calc_bruto();

-- =========================================================
-- 3) (Recomendado) Garantir que o rateio AFTER é a única coisa
-- que escreve valor_rateado e valor_final.
-- (Aqui só re-criamos o trigger para garantir que está ativo)
-- =========================================================
drop trigger if exists trg_apontamento_rateio_after on public.apontamentos;
create trigger trg_apontamento_rateio_after
after insert or update or delete on public.apontamentos
for each row execute function public.trg_apontamento_recalc_rateio();

commit;
