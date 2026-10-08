-- Executado somente na primeira inicialização de um banco vazio.
INSERT INTO clientes(nome, email, telefone) VALUES
    ('Ana Oliveira', 'ana@example.com', '(11) 90000-1001'),
    ('Bruno Santos', 'bruno@example.com', '(11) 90000-1002'),
    ('Carla Mendes', 'carla@example.com', '(11) 90000-1003');

INSERT INTO produtos(nome, categoria, preco, estoque, estoque_minimo) VALUES
    ('Mouse sem fio', 'Periféricos', 80.00, 30, 5),
    ('Teclado mecânico', 'Periféricos', 180.00, 20, 5),
    ('Headset USB', 'Áudio', 150.00, 15, 4),
    ('Monitor 24 polegadas', 'Monitores', 900.00, 8, 3),
    ('Cabo HDMI', 'Acessórios', 35.00, 4, 5),
    ('Webcam Full HD', 'Vídeo', 220.00, 10, 3);

INSERT INTO vendas(cliente_id, cliente_nome, desconto_percentual, valor_total) VALUES
    (1, 'Ana Oliveira', 10, fn_calcular_total_venda(340, 10)),
    (2, 'Bruno Santos', 0, fn_calcular_total_venda(185, 0)),
    (3, 'Carla Mendes', 5, fn_calcular_total_venda(900, 5));

INSERT INTO itens_venda(venda_id, produto_id, produto_nome, quantidade, preco_unitario) VALUES
    (1, 1, 'Mouse sem fio', 2, 80),
    (1, 2, 'Teclado mecânico', 1, 180),
    (2, 3, 'Headset USB', 1, 150),
    (2, 5, 'Cabo HDMI', 1, 35),
    (3, 4, 'Monitor 24 polegadas', 1, 900);

-- A Procedure dá baixa no estoque de cada produto vendido.
CALL sp_baixar_estoque(1, 2);
CALL sp_baixar_estoque(2, 1);
CALL sp_baixar_estoque(3, 1);
CALL sp_baixar_estoque(5, 1);
CALL sp_baixar_estoque(4, 1);
