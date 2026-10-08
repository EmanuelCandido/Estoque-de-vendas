-- Execute com: psql -d estoque_facil -f database/install.sql
\set ON_ERROR_STOP on
BEGIN;
\ir tables/01_schema.sql
\ir tables/02_limite_desconto.sql
\ir migrations/01_simplificar_rotinas.sql
\ir functions/01_calcular_total_venda.sql
\ir procedures/01_baixar_estoque.sql
\ir views/01_relatorio_vendas.sql
-- Este instalador é para um banco novo. Use scripts/setup_db.py em reinicializações.
\ir inserts/01_dados_exemplo.sql
COMMIT;
