begin;

alter table public.orcamentos
add column if not exists pdf_emitido_em timestamptz;

alter table public.orcamentos
add column if not exists valido_ate date;

commit;
