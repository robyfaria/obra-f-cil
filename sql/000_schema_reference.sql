-- ============================================
-- REFERÊNCIA DO SCHEMA (NÃO EXECUTAR)
-- Este arquivo é apenas para referência.
-- O banco já deve estar configurado no Supabase.
-- ============================================

-- TABELA: usuarios_app
-- Vincula usuários do Supabase Auth com perfis do sistema
CREATE TABLE public.usuarios_app (
    id BIGSERIAL PRIMARY KEY,
    auth_user_id UUID UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    usuario VARCHAR(100) NOT NULL,
    perfil VARCHAR(20) NOT NULL CHECK (perfil IN ('ADMIN', 'OPERACAO')),
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- TABELA: clientes
CREATE TABLE public.clientes (
    id BIGSERIAL PRIMARY KEY,
    nome VARCHAR(200) NOT NULL,
    telefone VARCHAR(20),
    endereco TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- TABELA: pessoas (profissionais)
CREATE TABLE public.pessoas (
    id BIGSERIAL PRIMARY KEY,
    nome VARCHAR(200) NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('PINTOR', 'AJUDANTE', 'TERCEIRO')),
    telefone VARCHAR(20),
    diaria_base DECIMAL(10,2) DEFAULT 0,
    observacao TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- TABELA: obras
CREATE TABLE public.obras (
    id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT REFERENCES public.clientes(id),
    titulo VARCHAR(200) NOT NULL,
    endereco_obra TEXT,
    status VARCHAR(20) DEFAULT 'AGUARDANDO' CHECK (status IN ('AGUARDANDO', 'INICIADO', 'PAUSADO', 'CANCELADO', 'CONCLUIDO')),
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- TABELA: orcamentos
CREATE TABLE public.orcamentos (
    id BIGSERIAL PRIMARY KEY,
    obra_id BIGINT REFERENCES public.obras(id),
    versao INT DEFAULT 1,
    status VARCHAR(20) DEFAULT 'RASCUNHO' CHECK (status IN ('RASCUNHO', 'EMITIDO', 'APROVADO', 'REPROVADO', 'CANCELADO')),
    valor_total DECIMAL(12,2) DEFAULT 0,
    desconto_valor DECIMAL(12,2) DEFAULT 0,
    valor_total_final DECIMAL(12,2) DEFAULT 0,
    aprovado_em TIMESTAMP,
    cancelado_em TIMESTAMP,
    observacao TEXT,
    pdf_url TEXT,
    pdf_emitido_em TIMESTAMP,
    valido_ate DATE,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- TABELA: obra_fases
CREATE TABLE public.obra_fases (
    id BIGSERIAL PRIMARY KEY,
    obra_id BIGINT REFERENCES public.obras(id),
    orcamento_id BIGINT REFERENCES public.orcamentos(id),
    nome_fase VARCHAR(100) NOT NULL,
    ordem INT DEFAULT 1,
    status VARCHAR(20) DEFAULT 'PENDENTE' CHECK (status IN ('PENDENTE', 'EM_ANDAMENTO', 'CONCLUIDA')),
    valor_fase DECIMAL(12,2) DEFAULT 0,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- TABELA: servicos (catálogo)
CREATE TABLE public.servicos (
    id BIGSERIAL PRIMARY KEY,
    nome VARCHAR(200) NOT NULL,
    unidade VARCHAR(10) DEFAULT 'UN' CHECK (unidade IN ('UN', 'M2', 'ML', 'H', 'DIA')),
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- TABELA: orcamento_fase_servicos
CREATE TABLE public.orcamento_fase_servicos (
    id BIGSERIAL PRIMARY KEY,
    obra_fase_id BIGINT REFERENCES public.obra_fases(id),
    servico_id BIGINT REFERENCES public.servicos(id),
    quantidade DECIMAL(10,2) DEFAULT 1,
    valor_unit DECIMAL(10,2) DEFAULT 0,
    valor_total DECIMAL(12,2) DEFAULT 0,
    observacao TEXT,
    criado_em TIMESTAMP DEFAULT NOW(),
    UNIQUE(obra_fase_id, servico_id)
);

-- TABELA: alocacoes
CREATE TABLE public.alocacoes (
    id BIGSERIAL PRIMARY KEY,
    data DATE NOT NULL,
    pessoa_id BIGINT REFERENCES public.pessoas(id),
    obra_id BIGINT REFERENCES public.obras(id),
    orcamento_id BIGINT REFERENCES public.orcamentos(id),
    obra_fase_id BIGINT REFERENCES public.obra_fases(id),
    periodo VARCHAR(10) DEFAULT 'INTEGRAL' CHECK (periodo IN ('INTEGRAL', 'MEIO')),
    tipo VARCHAR(10) DEFAULT 'INTERNO' CHECK (tipo IN ('INTERNO', 'EXTERNO')),
    observacao TEXT,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- TABELA: apontamentos
CREATE TABLE public.apontamentos (
    id BIGSERIAL PRIMARY KEY,
    obra_id BIGINT REFERENCES public.obras(id),
    orcamento_id BIGINT REFERENCES public.orcamentos(id),
    obra_fase_id BIGINT REFERENCES public.obra_fases(id),
    pessoa_id BIGINT REFERENCES public.pessoas(id),
    data DATE NOT NULL,
    tipo_dia VARCHAR(20) DEFAULT 'NORMAL' CHECK (tipo_dia IN ('NORMAL', 'FERIADO', 'SABADO', 'DOMINGO')),
    valor_base DECIMAL(10,2) DEFAULT 0,
    acrescimo_pct DECIMAL(5,2) DEFAULT 0,
    desconto_valor DECIMAL(10,2) DEFAULT 0,
    valor_final DECIMAL(10,2) DEFAULT 0,
    observacao TEXT,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- TABELA: recebimentos
CREATE TABLE public.recebimentos (
    id BIGSERIAL PRIMARY KEY,
    obra_fase_id BIGINT REFERENCES public.obra_fases(id),
    valor DECIMAL(12,2) DEFAULT 0,
    vencimento DATE,
    recebido_em DATE,
    status VARCHAR(20) DEFAULT 'ABERTO' CHECK (status IN ('ABERTO', 'VENCIDO', 'PAGO', 'CANCELADO')),
    observacao TEXT,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- TABELA: pagamentos
CREATE TABLE public.pagamentos (
    id BIGSERIAL PRIMARY KEY,
    tipo VARCHAR(20) DEFAULT 'SEMANAL' CHECK (tipo IN ('SEMANAL', 'EXTRA', 'POR_FASE')),
    referencia_inicio DATE,
    referencia_fim DATE,
    obra_fase_id BIGINT REFERENCES public.obra_fases(id),
    pessoa_id BIGINT REFERENCES public.pessoas(id),
    valor_total DECIMAL(12,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'PENDENTE' CHECK (status IN ('PENDENTE', 'PAGO', 'CANCELADO')),
    pago_em DATE,
    observacao TEXT,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- TABELA: pagamento_itens
CREATE TABLE public.pagamento_itens (
    id BIGSERIAL PRIMARY KEY,
    pagamento_id BIGINT REFERENCES public.pagamentos(id),
    apontamento_id BIGINT REFERENCES public.apontamentos(id),
    valor DECIMAL(10,2) DEFAULT 0,
    observacao TEXT,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- TABELA: auditoria
CREATE TABLE public.auditoria (
    id BIGSERIAL PRIMARY KEY,
    usuario VARCHAR(100),
    entidade VARCHAR(50),
    entidade_id VARCHAR(50),
    acao VARCHAR(50),
    antes_json TEXT,
    depois_json TEXT,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- FUNÇÃO IMPORTANTE: fn_recalcular_orcamento
-- Deve ser chamada após modificar itens de serviço
-- ============================================

-- CREATE OR REPLACE FUNCTION public.fn_recalcular_orcamento(p_orcamento_id BIGINT)
-- RETURNS void AS $$
-- BEGIN
--     -- Atualiza valor_fase de cada fase
--     UPDATE public.obra_fases f
--     SET valor_fase = COALESCE((
--         SELECT SUM(valor_total)
--         FROM public.orcamento_fase_servicos ofs
--         WHERE ofs.obra_fase_id = f.id
--     ), 0)
--     WHERE f.orcamento_id = p_orcamento_id;
--     
--     -- Atualiza totais do orçamento
--     UPDATE public.orcamentos o
--     SET 
--         valor_total = COALESCE((
--             SELECT SUM(valor_fase)
--             FROM public.obra_fases f
--             WHERE f.orcamento_id = o.id
--         ), 0),
--         valor_total_final = valor_total - COALESCE(desconto_valor, 0)
--     WHERE o.id = p_orcamento_id;
-- END;
-- $$ LANGUAGE plpgsql;
