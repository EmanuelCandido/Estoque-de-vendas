-- Remove as assinaturas antigas; os registros das tabelas são preservados.
-- Os scripts seguintes criam a Function e a Procedure com os novos parâmetros.
DROP PROCEDURE IF EXISTS sp_registrar_venda(INTEGER, JSONB, NUMERIC, INTEGER);
DROP PROCEDURE IF EXISTS sp_registrar_venda(INTEGER, INTEGER[], INTEGER[], NUMERIC, INTEGER);
DROP FUNCTION IF EXISTS fn_calcular_total_venda(JSONB, NUMERIC);
