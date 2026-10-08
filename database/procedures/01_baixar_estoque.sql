CREATE OR REPLACE PROCEDURE sp_baixar_estoque(
    p_produto_id INTEGER,
    p_quantidade INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE produtos SET estoque = estoque - p_quantidade
    WHERE id = p_produto_id AND ativo
        AND p_quantidade BETWEEN 1 AND 1000 AND estoque >= p_quantidade;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Estoque insuficiente ou produto/quantidade inválidos.';
    END IF;
END;
$$;
