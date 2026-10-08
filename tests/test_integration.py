"""Integração com PostgreSQL real em um schema temporário e isolado."""
import json
import os
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from threading import Barrier

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row

from src.app import create_app
from src.config import ROOT
from scripts.setup_db import setup_database


def test_database_url():
    configured = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if configured:
        return configured
    credential_file = ROOT / ".local/database.json"
    if credential_file.exists():
        password = json.loads(credential_file.read_text(encoding="utf-8"))["password"]
        return f"postgresql://postgres:{password}@127.0.0.1:55432/estoque_facil"
    raise RuntimeError("Inicie o banco ou configure TEST_DATABASE_URL antes dos testes.")


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_url = test_database_url()
        cls.old_url = os.environ.get("DATABASE_URL")
        cls.schema = "teste_" + uuid.uuid4().hex
        with psycopg.connect(cls.base_url, autocommit=True) as conn:
            conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(cls.schema)))
        cls.url = make_conninfo(cls.base_url, options=f"-csearch_path={cls.schema}")
        os.environ["DATABASE_URL"] = cls.url
        setup_database(seed=False)
        cls.app = create_app()
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        if cls.old_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = cls.old_url
        with psycopg.connect(cls.base_url, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(cls.schema)))

    def setUp(self):
        with self.connect() as conn:
            conn.execute("TRUNCATE itens_venda, vendas, produtos, clientes RESTART IDENTITY CASCADE")
            conn.execute("INSERT INTO clientes(nome,email) VALUES ('Cliente teste','teste@example.com'),('Outro cliente','outro@example.com')")
            conn.execute("INSERT INTO produtos(nome,categoria,preco,estoque) VALUES ('Mouse sem fio','Periféricos',80,10),('Teclado mecânico','Periféricos',180,5)")
        self.items = [{"produto_id": 1, "quantidade": 2}, {"produto_id": 2, "quantidade": 1}]

    def connect(self):
        return psycopg.connect(self.url, row_factory=dict_row)

    def sale(self, **overrides):
        return self.client.post("/api/vendas", json={"cliente_id": 1, "itens": self.items, "desconto": 10, **overrides})

    def inventory(self):
        with self.connect() as conn:
            return conn.execute("SELECT id,estoque FROM produtos ORDER BY id").fetchall()

    def test_function_calculates_in_database_without_changing_stock(self):
        before = self.inventory()
        result = self.client.post("/api/orcamento", json={"itens": self.items, "desconto": 10})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(Decimal(result.json["total"]), Decimal("306.00"))
        self.assertEqual(before, self.inventory())
        self.assertEqual(self.client.get("/api/relatorio").json["resumo"]["vendas"], 0)

    def test_example_seed_uses_simplified_routines_without_duplicates(self):
        with self.connect() as conn:
            conn.execute("TRUNCATE itens_venda, vendas, produtos, clientes RESTART IDENTITY CASCADE")
        setup_database(seed=True)
        setup_database(seed=True)
        self.assertEqual(len(self.client.get("/api/clientes").json), 3)
        self.assertEqual(len(self.client.get("/api/produtos").json), 6)
        report = self.client.get("/api/relatorio").json
        self.assertEqual(report["resumo"]["vendas"], 3)
        self.assertEqual(Decimal(report["resumo"]["faturamento"]), Decimal("1346.00"))
        self.assertEqual(self.inventory(), [{"id": 1, "estoque": 28}, {"id": 2, "estoque": 19},
                                           {"id": 3, "estoque": 14}, {"id": 4, "estoque": 7},
                                           {"id": 5, "estoque": 3}, {"id": 6, "estoque": 10}])

    def test_sale_uses_procedure_and_registers_items_and_stock(self):
        result = self.sale()
        self.assertEqual(result.status_code, 201, result.json)
        self.assertEqual(Decimal(result.json["valor_total"]), Decimal("306.00"))
        self.assertEqual(self.inventory(), [{"id": 1, "estoque": 8}, {"id": 2, "estoque": 4}])
        detail = self.client.get(f"/api/vendas/{result.json['venda_id']}").json
        self.assertEqual(len(detail["itens"]), 2)
        self.assertEqual(sum(i["quantidade"] for i in detail["itens"]), 3)

    def test_procedure_updates_one_product_without_creating_a_sale(self):
        with self.connect() as conn:
            conn.execute("CALL sp_baixar_estoque(1,2)")
            self.assertEqual(conn.execute("SELECT count(*) AS total FROM vendas").fetchone()["total"], 0)
            self.assertEqual(conn.execute("SELECT count(*) AS total FROM itens_venda").fetchone()["total"], 0)
        self.assertEqual(self.inventory(), [{"id": 1, "estoque": 8}, {"id": 2, "estoque": 5}])

    def test_view_consolidates_one_row_per_sale(self):
        self.sale()
        report = self.client.get("/api/relatorio").json
        self.assertEqual(len(report["vendas"]), 1)
        row = report["vendas"][0]
        self.assertEqual(row["produtos_diferentes"], 2)
        self.assertEqual(row["unidades"], 3)
        self.assertEqual(Decimal(row["subtotal"]), Decimal("340.00"))
        self.assertEqual(Decimal(row["valor_desconto"]), Decimal("34.00"))
        self.assertEqual(Decimal(report["resumo"]["faturamento"]), Decimal("306.00"))

    def test_insufficient_stock_rolls_back_everything(self):
        with self.connect() as conn:
            conn.execute("UPDATE produtos SET estoque=0 WHERE id=2")
        before = self.inventory()
        result = self.sale()
        self.assertEqual(result.status_code, 400)
        self.assertIn("Estoque insuficiente", result.json["erro"])
        self.assertEqual(before, self.inventory())
        with self.connect() as conn:
            self.assertEqual(conn.execute("SELECT count(*) AS total FROM vendas").fetchone()["total"], 0)
            self.assertEqual(conn.execute("SELECT count(*) AS total FROM itens_venda").fetchone()["total"], 0)

    def test_database_itself_rejects_invalid_parameters(self):
        before = self.inventory()
        invalid_items = [(None, 1), (999, 1), (1, None), (1, 0),
                         (1, -1), (1, 1001), (1, 11)]
        for product_id, quantity in invalid_items:
            with self.subTest(product_id=product_id, quantity=quantity), self.connect() as conn:
                with self.assertRaises(psycopg.errors.RaiseException):
                    conn.execute("CALL sp_baixar_estoque(%s::integer,%s::integer)",
                                 (product_id, quantity))
        with self.connect() as conn:
            conn.execute("UPDATE produtos SET ativo=FALSE WHERE id=2")
        with self.connect() as conn:
            with self.assertRaises(psycopg.errors.RaiseException):
                conn.execute("CALL sp_baixar_estoque(2,1)")
        for subtotal in [None, 0, -1, Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")]:
            with self.subTest(subtotal=subtotal), self.connect() as conn:
                with self.assertRaises(psycopg.errors.RaiseException):
                    conn.execute("SELECT fn_calcular_total_venda(%s::numeric,10)", (subtotal,))
        for discount in [None, -1, 101, Decimal("100.01"), Decimal("NaN"),
                         Decimal("Infinity"), Decimal("-Infinity"), Decimal("10.001")]:
            with self.subTest(discount=discount), self.connect() as conn:
                with self.assertRaises(psycopg.errors.RaiseException):
                    conn.execute("SELECT fn_calcular_total_venda(340,%s::numeric)", (discount,))
        self.assertEqual(self.inventory(), before)
        with self.connect() as conn:
            self.assertEqual(conn.execute("SELECT count(*) AS total FROM vendas").fetchone()["total"], 0)
            self.assertEqual(conn.execute("SELECT count(*) AS total FROM itens_venda").fetchone()["total"], 0)

    def test_quote_uses_database_prices_and_rejects_invalid_products(self):
        with self.connect() as conn:
            conn.execute("UPDATE produtos SET preco=120 WHERE id=1")
        items = [{"produto_id": 1, "quantidade": 2, "preco": 0},
                 {"produto_id": 2, "quantidade": 1}]
        quote = self.client.post("/api/orcamento", json={"itens": items, "desconto": 10, "subtotal": 1})
        self.assertEqual(quote.status_code, 200, quote.json)
        self.assertEqual(Decimal(quote.json["total"]), Decimal("378.00"))
        before = self.inventory()
        with self.connect() as conn:
            conn.execute("UPDATE produtos SET ativo=FALSE WHERE id=2")
        for invalid_items in [self.items, [{"produto_id": 999, "quantidade": 1}],
                              [{"produto_id": 1, "quantidade": 1}] * 2]:
            with self.subTest(items=invalid_items):
                self.assertEqual(self.client.post("/api/orcamento", json={"itens": invalid_items}).status_code, 400)
                self.assertEqual(self.sale(itens=invalid_items).status_code, 400)
        self.assertEqual(self.inventory(), before)
        self.assertEqual(self.client.get("/api/relatorio").json["resumo"]["vendas"], 0)

    def test_api_sorts_products_and_keeps_their_quantities(self):
        result = self.sale(itens=list(reversed(self.items)))
        self.assertEqual(result.status_code, 201, result.json)
        self.assertEqual(Decimal(result.json["valor_total"]), Decimal("306.00"))
        self.assertEqual(self.inventory(), [{"id": 1, "estoque": 8}, {"id": 2, "estoque": 4}])
        detail = self.client.get(f"/api/vendas/{result.json['venda_id']}").json
        self.assertEqual([(i["produto_id"], i["quantidade"]) for i in detail["itens"]], [(1, 2), (2, 1)])

    def test_discount_range_including_full_discount(self):
        before = self.inventory()
        for discount, expected in [(0, "340.00"), (31, "234.60"), (43, "193.80"),
                                   ("99.99", "0.03"), (100, "0.00")]:
            with self.subTest(discount=discount):
                result = self.client.post("/api/orcamento", json={"itens": self.items, "desconto": discount})
                self.assertEqual(result.status_code, 200, result.json)
                self.assertEqual(Decimal(result.json["total"]), Decimal(expected))
        self.assertEqual(before, self.inventory())
        self.assertEqual(self.client.get("/api/relatorio").json["resumo"]["vendas"], 0)

    def test_full_discount_sale_updates_stock_and_report(self):
        result = self.sale(desconto=100)
        self.assertEqual(result.status_code, 201, result.json)
        self.assertEqual(Decimal(result.json["valor_total"]), Decimal("0.00"))
        self.assertEqual(self.inventory(), [{"id": 1, "estoque": 8}, {"id": 2, "estoque": 4}])
        detail = self.client.get(f"/api/vendas/{result.json['venda_id']}").json
        self.assertEqual(len(detail["itens"]), 2)
        self.assertEqual(sum(i["quantidade"] for i in detail["itens"]), 3)
        report = self.client.get("/api/relatorio").json
        self.assertEqual(len(report["vendas"]), 1)
        self.assertEqual(Decimal(report["vendas"][0]["desconto_percentual"]), Decimal("100.00"))
        self.assertEqual(Decimal(report["vendas"][0]["subtotal"]), Decimal("340.00"))
        self.assertEqual(Decimal(report["vendas"][0]["valor_desconto"]), Decimal("340.00"))
        self.assertEqual(report["resumo"]["vendas"], 1)
        self.assertEqual(report["resumo"]["unidades"], 3)
        self.assertEqual(Decimal(report["resumo"]["faturamento"]), Decimal("0.00"))
        self.assertEqual(Decimal(report["resumo"]["descontos"]), Decimal("340.00"))

    def test_api_rejects_discounts_outside_range_without_writing(self):
        before = self.inventory()
        for discount in ["-0.01", "100.01", 101, "43.001", "NaN", "Infinity"]:
            with self.subTest(discount=discount):
                quote = self.client.post("/api/orcamento", json={"itens": self.items, "desconto": discount})
                self.assertEqual(quote.status_code, 400)
                self.assertEqual(self.sale(desconto=discount).status_code, 400)
        self.assertEqual(before, self.inventory())
        self.assertEqual(self.client.get("/api/relatorio").json["resumo"]["vendas"], 0)

    def test_sale_table_rejects_invalid_discount_and_negative_total(self):
        for discount, total in [("-0.01", 340), ("100.01", 340), (0, "-0.01")]:
            with self.subTest(discount=discount, total=total), self.connect() as conn:
                with self.assertRaises(psycopg.errors.CheckViolation):
                    conn.execute(
                        "INSERT INTO vendas(cliente_id,cliente_nome,desconto_percentual,valor_total) "
                        "VALUES (1,'Cliente teste',%s,%s)", (discount, total)
                    )

    def test_setup_upgrades_old_discount_constraints_preserving_data(self):
        existing = self.sale().json
        inventory = self.inventory()
        with self.connect() as conn:
            conn.execute("CREATE FUNCTION fn_calcular_total_venda(JSONB,NUMERIC) RETURNS NUMERIC "
                         "LANGUAGE plpgsql AS $$ BEGIN RETURN 0; END; $$")
            conn.execute("CREATE PROCEDURE sp_registrar_venda(INTEGER,JSONB,NUMERIC,INOUT p_venda_id INTEGER) "
                         "LANGUAGE plpgsql AS $$ BEGIN p_venda_id := 0; END; $$")
            conn.execute("CREATE PROCEDURE sp_registrar_venda(INTEGER,INTEGER[],INTEGER[],NUMERIC,INOUT p_venda_id INTEGER) "
                         "LANGUAGE plpgsql AS $$ BEGIN p_venda_id := 0; END; $$")
            conn.execute("ALTER TABLE vendas DROP CONSTRAINT vendas_desconto_percentual_check, "
                         "DROP CONSTRAINT vendas_valor_total_check, "
                         "ADD CONSTRAINT vendas_desconto_percentual_check CHECK (desconto_percentual BETWEEN 0 AND 30), "
                         "ADD CONSTRAINT vendas_valor_total_check CHECK (valor_total > 0)")
        try:
            with self.connect() as conn:
                with self.assertRaises(psycopg.errors.CheckViolation):
                    conn.execute("INSERT INTO vendas(cliente_id,cliente_nome,desconto_percentual,valor_total) "
                                 "VALUES (1,'Cliente teste',100,0)")
            setup_database(seed=False)
            setup_database(seed=False)
            with self.connect() as conn:
                self.assertIsNone(conn.execute(
                    "SELECT to_regprocedure('fn_calcular_total_venda(jsonb,numeric)') AS antigo"
                ).fetchone()["antigo"])
                self.assertIsNone(conn.execute(
                    "SELECT to_regprocedure('sp_registrar_venda(integer,jsonb,numeric,integer)') AS antigo"
                ).fetchone()["antigo"])
                self.assertIsNone(conn.execute(
                    "SELECT to_regprocedure('sp_registrar_venda(integer,integer[],integer[],numeric,integer)') AS antigo"
                ).fetchone()["antigo"])
            preserved = self.client.get(f"/api/vendas/{existing['venda_id']}").json
            self.assertEqual(preserved["venda"]["venda_id"], existing["venda_id"])
            self.assertEqual(Decimal(preserved["venda"]["valor_total"]), Decimal("306.00"))
            self.assertEqual(len(preserved["itens"]), 2)
            self.assertEqual(self.inventory(), inventory)
            self.assertEqual(self.sale(desconto=100).status_code, 201)
            self.assertEqual(self.client.get("/api/relatorio").json["resumo"]["vendas"], 2)
        finally:
            setup_database(seed=False)

    def test_product_and_customer_crud(self):
        customer = self.client.post("/api/clientes", json={"nome": "Novo cliente", "email": "novo@example.com", "telefone": "123"})
        self.assertEqual(customer.status_code, 201)
        customer_id = customer.json["id"]
        changed = self.client.put(f"/api/clientes/{customer_id}", json={"nome": "Cliente editado", "email": "novo@example.com", "telefone": "456", "ativo": False})
        self.assertEqual(changed.json["nome"], "Cliente editado")
        self.assertFalse(changed.json["ativo"])
        self.assertEqual(self.client.delete(f"/api/clientes/{customer_id}").status_code, 200)
        data = {"nome": "Novo produto", "categoria": "Teste", "preco": "12.50", "estoque": 8, "estoque_minimo": 2}
        result = self.client.post("/api/produtos", json=data)
        self.assertEqual(result.status_code, 201)
        product_id = result.json["id"]
        self.assertEqual(self.client.put(f"/api/produtos/{product_id}", json={**data, "preco": "15.00"}).status_code, 200)
        self.assertEqual(self.client.delete(f"/api/produtos/{product_id}").status_code, 200)

    def test_history_survives_changes_and_referenced_deletion_is_blocked(self):
        sale = self.sale().json
        self.assertEqual(self.client.delete("/api/produtos/1").status_code, 409)
        self.assertEqual(self.client.delete("/api/clientes/1").status_code, 409)
        self.client.put("/api/clientes/1", json={"nome": "Nome alterado", "email": "teste@example.com", "ativo": False})
        self.client.put("/api/produtos/1", json={"nome": "Mouse alterado", "categoria": "Periféricos", "preco": 999, "estoque": 8, "ativo": False})
        detail = self.client.get(f"/api/vendas/{sale['venda_id']}").json
        self.assertEqual(detail["venda"]["cliente_nome"], "Cliente teste")
        self.assertEqual(detail["itens"][0]["produto_nome"], "Mouse sem fio")
        self.assertEqual(Decimal(detail["itens"][0]["preco_unitario"]), Decimal("80.00"))
        self.assertEqual(self.sale().status_code, 400)

    def test_api_validation_and_parametrized_customer_names(self):
        result = self.client.post("/api/clientes", json={"nome": "Cliente'); DROP TABLE produtos; --", "email": "seguro@example.com"})
        self.assertEqual(result.status_code, 201)
        self.assertEqual(len(self.client.get("/api/produtos").json), 2)
        for value in [True, 1.5, -1, "abc"]:
            response = self.client.post("/api/orcamento", json={"itens": [{"produto_id": 1, "quantidade": value}], "desconto": 0})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post("/api/clientes", json={"nome": "Duplicado", "email": "TESTE@example.com"}).status_code, 409)
        self.assertEqual(self.client.post("/api/orcamento", json={"itens": self.items}, headers={"Origin": "https://outro.example"}).status_code, 403)

    def test_report_filters_and_real_integration_events(self):
        self.client.post("/api/orcamento", json={"itens": self.items, "desconto": 10})
        sale = self.sale().json
        self.client.get("/api/relatorio")
        self.assertEqual(self.client.get("/api/relatorio?inicio=2100-01-01&fim=2100-01-02").json["resumo"]["vendas"], 0)
        self.assertEqual(self.client.get("/api/relatorio?inicio=2026-02-30").status_code, 400)
        self.assertEqual(self.client.get("/api/relatorio?inicio=2026-10-03&fim=2026-10-02").status_code, 400)
        resources = self.client.get("/api/recursos").json
        self.assertEqual({"View", "Function", "Procedure"}, set(resources["scripts"]))
        self.assertEqual({"View", "Function", "Procedure"}, {e["recurso"] for e in resources["eventos"]})
        procedure_calls = [event for event in resources["eventos"]
                           if event["recurso"] == "Procedure"
                           and event["resultado"]["venda_id"] == sale["venda_id"]]
        # Os eventos mais recentes correspondem aos dois produtos desta venda.
        self.assertEqual([event["parametros"] for event in procedure_calls[:2]], list(reversed(self.items)))
        self.assertEqual([event["resultado"]["estoque_atual"] for event in procedure_calls[:2]], [4, 8])
        self.assertTrue(all(event["sql"] == "CALL sp_baixar_estoque(%s, %s)" for event in procedure_calls[:2]))

    def test_two_concurrent_sales_cannot_sell_the_same_last_unit(self):
        with self.connect() as conn:
            conn.execute("UPDATE produtos SET estoque=1 WHERE id=1")
        barrier = Barrier(2)
        def sell_last_unit(customer_id):
            with self.app.test_client() as client:
                barrier.wait(timeout=10)
                result = client.post("/api/vendas", json={"cliente_id": customer_id,
                                     "itens": [{"produto_id": 1, "quantidade": 1}], "desconto": 0})
                if result.status_code == 400:
                    self.assertIn("Estoque insuficiente", result.json["erro"])
                return result.status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(sell_last_unit, [1, 2]))
        self.assertCountEqual(results, [201, 400])
        with self.connect() as conn:
            self.assertEqual(conn.execute("SELECT estoque FROM produtos WHERE id=1").fetchone()["estoque"], 0)
            self.assertEqual(conn.execute("SELECT count(*) AS total FROM vendas").fetchone()["total"], 1)
            self.assertEqual(conn.execute("SELECT count(*) AS total FROM itens_venda").fetchone()["total"], 1)


if __name__ == "__main__":
    unittest.main()
