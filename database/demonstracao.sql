-- Consultas para mostrar no vídeo, com o sistema funcionando.
SELECT * FROM vw_relatorio_vendas ORDER BY venda_id DESC;

-- 2 mouses a R$ 80 + 1 teclado a R$ 180 = R$ 340; desconto de 10% = R$ 306.
SELECT fn_calcular_total_venda(340, 10) AS total;

-- O ROLLBACK desfaz a baixa de estoque usada nesta demonstração.
BEGIN;
CALL sp_baixar_estoque(1, 2);
SELECT id, nome, estoque FROM produtos WHERE id = 1;
ROLLBACK;
