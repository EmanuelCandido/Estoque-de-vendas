-- Agrega cabeçalho, cliente e itens sem duplicar o total da venda.
CREATE OR REPLACE VIEW vw_relatorio_vendas AS
SELECT
    v.id AS venda_id,
    v.data_venda,
    c.id AS cliente_id,
    v.cliente_nome,
    COUNT(i.id)::INTEGER AS produtos_diferentes,
    SUM(i.quantidade)::INTEGER AS unidades,
    SUM(i.quantidade * i.preco_unitario)::NUMERIC(14,2) AS subtotal,
    v.desconto_percentual,
    (SUM(i.quantidade * i.preco_unitario) - v.valor_total)::NUMERIC(14,2) AS valor_desconto,
    v.valor_total
FROM vendas v
JOIN clientes c ON c.id = v.cliente_id
JOIN itens_venda i ON i.venda_id = v.id
GROUP BY v.id, c.id;
