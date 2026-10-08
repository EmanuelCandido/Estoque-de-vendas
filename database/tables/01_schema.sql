CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome VARCHAR(120) NOT NULL CHECK (length(btrim(nome)) >= 2),
    email VARCHAR(160) NOT NULL,
    telefone VARCHAR(30) NOT NULL DEFAULT '',
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS clientes_email_unico ON clientes (lower(email));

CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome VARCHAR(120) NOT NULL CHECK (length(btrim(nome)) >= 2),
    categoria VARCHAR(60) NOT NULL DEFAULT 'Geral',
    preco NUMERIC(12,2) NOT NULL CHECK (preco > 0 AND preco <= 1000000),
    estoque INTEGER NOT NULL DEFAULT 0 CHECK (estoque >= 0 AND estoque <= 1000000),
    estoque_minimo INTEGER NOT NULL DEFAULT 5 CHECK (estoque_minimo >= 0 AND estoque_minimo <= 1000000),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vendas (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    cliente_nome VARCHAR(120) NOT NULL,
    data_venda TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    desconto_percentual NUMERIC(5,2) NOT NULL DEFAULT 0
        CHECK (desconto_percentual BETWEEN 0 AND 100),
    valor_total NUMERIC(14,2) NOT NULL CHECK (valor_total >= 0)
);

CREATE TABLE IF NOT EXISTS itens_venda (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    venda_id INTEGER NOT NULL REFERENCES vendas(id),
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    produto_nome VARCHAR(120) NOT NULL,
    quantidade INTEGER NOT NULL CHECK (quantidade BETWEEN 1 AND 1000),
    preco_unitario NUMERIC(12,2) NOT NULL CHECK (preco_unitario > 0),
    UNIQUE (venda_id, produto_id)
);

CREATE INDEX IF NOT EXISTS vendas_data_idx ON vendas(data_venda DESC);
CREATE INDEX IF NOT EXISTS vendas_cliente_idx ON vendas(cliente_id);
CREATE INDEX IF NOT EXISTS itens_produto_idx ON itens_venda(produto_id);
