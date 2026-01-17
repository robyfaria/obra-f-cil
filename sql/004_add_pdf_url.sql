begin;

alter table public.orcamentos
add column if not exists pdf_url text;

commit;
