-- No Supabase, as tabelas do schema public também ficam expostas pela API REST (roles anon e authenticated).
-- A aplicação acessa o banco pelo Python com a connection string, então a API pública é fechada:
-- RLS ligado sem políticas bloqueia anon/authenticated; o dono das tabelas (postgres) continua com acesso.
ALTER TABLE clientes ENABLE ROW LEVEL SECURITY;
ALTER TABLE produtos ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendas ENABLE ROW LEVEL SECURITY;
ALTER TABLE itens_venda ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    -- Em um PostgreSQL comum essas roles não existem; o bloco só age no Supabase.
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON vw_relatorio_vendas FROM anon, authenticated;
        REVOKE EXECUTE ON FUNCTION fn_calcular_total_venda(NUMERIC, NUMERIC) FROM anon, authenticated, PUBLIC;
        REVOKE EXECUTE ON PROCEDURE sp_baixar_estoque(INTEGER, INTEGER) FROM anon, authenticated, PUBLIC;
    END IF;
END
$$;
