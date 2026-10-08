-- Atualiza também bancos criados com o limite anterior de 30%.
-- A reaplicação preserva as vendas e permite desconto integral com total zero.
ALTER TABLE vendas
    DROP CONSTRAINT IF EXISTS vendas_desconto_percentual_check,
    DROP CONSTRAINT IF EXISTS vendas_valor_total_check,
    ADD CONSTRAINT vendas_desconto_percentual_check
        CHECK (desconto_percentual BETWEEN 0 AND 100),
    ADD CONSTRAINT vendas_valor_total_check CHECK (valor_total >= 0);
