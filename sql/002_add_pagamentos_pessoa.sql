alter table public.pagamentos
  add column if not exists pessoa_id bigint references public.pessoas(id) on update cascade on delete set null;

create index if not exists idx_pag_pessoa on public.pagamentos(pessoa_id);
