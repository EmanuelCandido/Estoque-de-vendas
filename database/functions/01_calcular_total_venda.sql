CREATE OR REPLACE FUNCTION fn_calcular_total_venda(
    p_subtotal NUMERIC,
    p_desconto NUMERIC DEFAULT 0
)
RETURNS NUMERIC
LANGUAGE plpgsql
AS $$
DECLARE
    v_total NUMERIC;
BEGIN
    -- Confere os valores recebidos antes de calcular.
    IF p_subtotal IS NULL OR p_subtotal <= 0
        OR p_subtotal::TEXT IN ('NaN', 'Infinity', '-Infinity') THEN
        RAISE EXCEPTION 'O subtotal deve ser um número positivo.';
    END IF;
    IF p_desconto IS NULL OR p_desconto NOT BETWEEN 0 AND 100
        OR p_desconto <> round(p_desconto, 2) THEN
        RAISE EXCEPTION 'O desconto deve estar entre 0 e 100, com até duas casas decimais.';
    END IF;

    -- Calcula o desconto e devolve o valor final com duas casas decimais.
    v_total := p_subtotal - (p_subtotal * p_desconto / 100);
    RETURN round(v_total, 2);
END;
$$;
