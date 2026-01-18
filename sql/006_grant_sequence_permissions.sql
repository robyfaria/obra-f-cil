begin;

-- Permite inserts usando colunas bigserial para usuários autenticados
grant usage, select on all sequences in schema public to authenticated;

-- Garante permissões padrão para novas sequences
alter default privileges in schema public grant usage, select on sequences to authenticated;

commit;
