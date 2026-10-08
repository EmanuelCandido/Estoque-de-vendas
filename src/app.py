"""API Flask: o navegador chama o Python, que executa os recursos PostgreSQL."""
import json
import os
import re
from collections import deque
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from time import perf_counter

import psycopg
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from src.config import ROOT
from src.db import connection


def serializable(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(item) for item in value]
    return value


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
    events = deque(maxlen=20)

    def response(data, status=200):
        return jsonify(serializable(data)), status

    def record(resource, screen, sql, parameters, result, started):
        events.appendleft({
            "recurso": resource, "tela": screen, "sql": sql,
            "parametros": serializable(parameters), "resultado": serializable(result),
            "duracao_ms": round((perf_counter() - started) * 1000, 2),
            "horario": datetime.now(timezone.utc).isoformat(),
        })

    def body():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValueError("Envie os dados do formulário em JSON.")
        return data

    def text_value(data, key, minimum, maximum):
        value = data.get(key, "")
        if not isinstance(value, str):
            raise ValueError(f"O campo {key} deve ser um texto.")
        value = value.strip()
        if not minimum <= len(value) <= maximum:
            raise ValueError(f"O campo {key} deve ter entre {minimum} e {maximum} caracteres.")
        return value

    def integer(value, label, minimum=0, maximum=1000000):
        if isinstance(value, bool) or not re.fullmatch(r"[0-9]+", str(value)):
            raise ValueError(f"{label} deve ser um número inteiro.")
        result = int(value)
        if not minimum <= result <= maximum:
            raise ValueError(f"{label} deve estar entre {minimum} e {maximum}.")
        return result

    def number(value, label, minimum, maximum):
        try:
            result = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValueError(f"{label} deve ser um número válido.") from None
        if not result.is_finite() or not minimum <= result <= maximum:
            raise ValueError(f"{label} deve estar entre {minimum} e {maximum}.")
        if result != result.quantize(Decimal("0.01")):
            raise ValueError(f"{label} deve ter no máximo duas casas decimais.")
        return result

    def active_value(data):
        value = data.get("ativo", True)
        if not isinstance(value, bool):
            raise ValueError("O campo ativo deve ser verdadeiro ou falso.")
        return value

    def sale_input(data):
        items = data.get("itens")
        if not isinstance(items, list) or not 1 <= len(items) <= 50:
            raise ValueError("Adicione entre 1 e 50 produtos à venda.")
        normalized = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Cada item deve conter produto e quantidade.")
            normalized.append({
                "produto_id": integer(item.get("produto_id"), "Produto", 1, 999999999),
                "quantidade": integer(item.get("quantidade"), "Quantidade", 1, 1000),
            })
        product_ids = [item["produto_id"] for item in normalized]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Cada produto deve aparecer apenas uma vez na venda.")
        normalized.sort(key=lambda item: item["produto_id"])
        return normalized, number(data.get("desconto", 0), "Desconto", Decimal(0), Decimal(100))

    @app.errorhandler(ValueError)
    def validation_error(error):
        return response({"erro": str(error)}, 400)

    @app.errorhandler(psycopg.Error)
    def database_error(error):
        if error.sqlstate == "P0001":
            return response({"erro": error.diag.message_primary}, 400)
        if error.sqlstate == "23505":
            return response({"erro": "Já existe um cliente com esse e-mail."}, 409)
        if error.sqlstate == "23503":
            return response({"erro": "Este cadastro tem vendas vinculadas. Inative-o para preservar o histórico."}, 409)
        app.logger.exception("Falha no banco de dados")
        if isinstance(error, psycopg.OperationalError):
            return response({"erro": "Não foi possível conectar ao PostgreSQL. Verifique se o banco está iniciado."}, 503)
        return response({"erro": "O banco não aceitou a operação. Confira os dados informados."}, 400)

    @app.errorhandler(HTTPException)
    def http_error(error):
        return response({"erro": error.description}, error.code)

    @app.errorhandler(Exception)
    def unexpected_error(error):
        app.logger.exception("Falha inesperada")
        return response({"erro": "Ocorreu uma falha ao processar a solicitação."}, 500)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/status")
    def status():
        with connection() as conn:
            info = conn.execute("SELECT version() AS versao, current_database() AS banco").fetchone()
        return response({"status": "ok", **info})

    @app.get("/api/clientes")
    def customers():
        with connection() as conn:
            rows = conn.execute("SELECT * FROM clientes ORDER BY ativo DESC, nome, id").fetchall()
        return response(rows)

    @app.post("/api/clientes")
    @app.put("/api/clientes/<int:customer_id>")
    def save_customer(customer_id=None):
        data = body()
        name = text_value(data, "nome", 2, 120)
        email = text_value(data, "email", 3, 160).lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise ValueError("Informe um e-mail válido.")
        phone = text_value(data, "telefone", 0, 30)
        active = active_value(data)
        with connection() as conn:
            if customer_id is None:
                row = conn.execute(
                    "INSERT INTO clientes(nome,email,telefone,ativo) VALUES (%s,%s,%s,%s) RETURNING *",
                    (name, email, phone, active),
                ).fetchone()
            else:
                row = conn.execute(
                    "UPDATE clientes SET nome=%s,email=%s,telefone=%s,ativo=%s WHERE id=%s RETURNING *",
                    (name, email, phone, active, customer_id),
                ).fetchone()
        if row is None:
            return response({"erro": "Cliente não encontrado."}, 404)
        return response(row, 201 if customer_id is None else 200)

    @app.delete("/api/clientes/<int:customer_id>")
    def delete_customer(customer_id):
        with connection() as conn:
            row = conn.execute("DELETE FROM clientes WHERE id=%s RETURNING id", (customer_id,)).fetchone()
        if row is None:
            return response({"erro": "Cliente não encontrado."}, 404)
        return response({"mensagem": "Cliente excluído."})

    @app.get("/api/produtos")
    def products():
        with connection() as conn:
            rows = conn.execute("SELECT * FROM produtos ORDER BY ativo DESC, nome, id").fetchall()
        return response(rows)

    @app.post("/api/produtos")
    @app.put("/api/produtos/<int:product_id>")
    def save_product(product_id=None):
        data = body()
        values = (
            text_value(data, "nome", 2, 120), text_value(data, "categoria", 2, 60),
            number(data.get("preco"), "Preço", Decimal("0.01"), Decimal(1000000)),
            integer(data.get("estoque"), "Estoque"),
            integer(data.get("estoque_minimo", 5), "Estoque mínimo"), active_value(data),
        )
        with connection() as conn:
            if product_id is None:
                row = conn.execute(
                    "INSERT INTO produtos(nome,categoria,preco,estoque,estoque_minimo,ativo) "
                    "VALUES (%s,%s,%s,%s,%s,%s) RETURNING *", values,
                ).fetchone()
            else:
                row = conn.execute(
                    "UPDATE produtos SET nome=%s,categoria=%s,preco=%s,estoque=%s,estoque_minimo=%s,ativo=%s "
                    "WHERE id=%s RETURNING *", (*values, product_id),
                ).fetchone()
        if row is None:
            return response({"erro": "Produto não encontrado."}, 404)
        return response(row, 201 if product_id is None else 200)

    @app.delete("/api/produtos/<int:product_id>")
    def delete_product(product_id):
        with connection() as conn:
            row = conn.execute("DELETE FROM produtos WHERE id=%s RETURNING id", (product_id,)).fetchone()
        if row is None:
            return response({"erro": "Produto não encontrado."}, 404)
        return response({"mensagem": "Produto excluído."})

    @app.post("/api/orcamento")
    def quote():
        items, discount = sale_input(body())
        sql = "SELECT fn_calcular_total_venda(%s::numeric, %s::numeric) AS total"
        started = perf_counter()
        with connection() as conn:
            subtotal = Decimal(0)
            for item in items:
                product = conn.execute(
                    "SELECT preco FROM produtos WHERE id=%s AND ativo", (item["produto_id"],)
                ).fetchone()
                if product is None:
                    raise ValueError("Produto inexistente ou inativo.")
                subtotal += product["preco"] * item["quantidade"]
            # Function: calcula o total com desconto no PostgreSQL, sem alterar o estoque.
            result = conn.execute(sql, (subtotal, discount)).fetchone()
        record("Function", "Orçamento", sql, {"subtotal": subtotal, "desconto": discount}, result, started)
        return response(result)

    @app.post("/api/vendas")
    def sell():
        data = body()
        items, discount = sale_input(data)
        customer_id = integer(data.get("cliente_id"), "Cliente", 1, 999999999)
        sql = "CALL sp_baixar_estoque(%s, %s)"
        started = perf_counter()
        stock_updates = []
        with connection() as conn:
            customer = conn.execute(
                "SELECT nome FROM clientes WHERE id=%s AND ativo FOR UPDATE", (customer_id,)
            ).fetchone()
            if customer is None:
                raise ValueError("Cliente inexistente ou inativo.")
            sale_id = conn.execute(
                "INSERT INTO vendas(cliente_id,cliente_nome,desconto_percentual,valor_total) "
                "VALUES (%s,%s,%s,0) RETURNING id", (customer_id, customer["nome"], discount)
            ).fetchone()["id"]
            subtotal = Decimal(0)
            for item in items:
                # Procedure: confere e reduz o estoque deste produto.
                conn.execute(sql, (item["produto_id"], item["quantidade"]))
                product = conn.execute(
                    "SELECT nome,preco,estoque FROM produtos WHERE id=%s", (item["produto_id"],)
                ).fetchone()
                conn.execute(
                    "INSERT INTO itens_venda(venda_id,produto_id,produto_nome,quantidade,preco_unitario) "
                    "VALUES (%s,%s,%s,%s,%s)",
                    (sale_id, item["produto_id"], product["nome"], item["quantidade"], product["preco"])
                )
                subtotal += product["preco"] * item["quantidade"]
                stock_updates.append({**item, "estoque": product["estoque"]})
            # Function: calcula o total da venda com o desconto informado.
            conn.execute(
                "UPDATE vendas SET valor_total=fn_calcular_total_venda(%s,%s) WHERE id=%s",
                (subtotal, discount, sale_id)
            )
            # View: consulta os dados consolidados da venda que acabou de ser registrada.
            result = conn.execute(
                "SELECT * FROM vw_relatorio_vendas WHERE venda_id=%s", (sale_id,)
            ).fetchone()
        for item in stock_updates:
            record("Procedure", "Nova venda", sql,
                   {"produto_id": item["produto_id"], "quantidade": item["quantidade"]},
                   {"venda_id": sale_id, "estoque_atual": item["estoque"]}, started)
        return response(result, 201)

    @app.get("/api/vendas/<int:sale_id>")
    def sale_detail(sale_id):
        with connection() as conn:
            # View: obtém o resumo da venda para a tela de detalhes.
            sale = conn.execute("SELECT * FROM vw_relatorio_vendas WHERE venda_id=%s", (sale_id,)).fetchone()
            items = conn.execute("SELECT * FROM itens_venda WHERE venda_id=%s ORDER BY id", (sale_id,)).fetchall()
        if sale is None:
            return response({"erro": "Venda não encontrada."}, 404)
        return response({"venda": sale, "itens": items})

    @app.get("/api/relatorio")
    def report():
        clauses, parameters = [], []
        for name, comparison in (("inicio", ">="), ("fim", "<=")):
            value = request.args.get(name)
            if value:
                try:
                    parsed = date.fromisoformat(value)
                except ValueError:
                    raise ValueError("Informe uma data no formato AAAA-MM-DD.") from None
                clauses.append(f"(data_venda AT TIME ZONE 'America/Sao_Paulo')::date {comparison} %s")
                parameters.append(parsed)
        if len(parameters) == 2 and parameters[0] > parameters[1]:
            raise ValueError("A data inicial não pode ser maior que a final.")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        sql = "SELECT * FROM vw_relatorio_vendas" + where + " ORDER BY data_venda DESC, venda_id DESC"
        started = perf_counter()
        with connection() as conn:
            # View: retorna as vendas com subtotais, descontos e totais para o relatório.
            rows = conn.execute(sql, parameters).fetchall()
        summary = {
            "vendas": len(rows),
            "faturamento": sum((row["valor_total"] for row in rows), Decimal(0)),
            "descontos": sum((row["valor_desconto"] for row in rows), Decimal(0)),
            "unidades": sum(row["unidades"] for row in rows),
        }
        record("View", "Relatório de vendas", sql, parameters, {"linhas": len(rows), **summary}, started)
        return response({"vendas": rows, "resumo": summary})

    @app.get("/api/recursos")
    def resources():
        files = {
            "View": "views/01_relatorio_vendas.sql",
            "Function": "functions/01_calcular_total_venda.sql",
            "Procedure": "procedures/01_baixar_estoque.sql",
        }
        return response({
            "scripts": {key: (ROOT / "database" / path).read_text(encoding="utf-8") for key, path in files.items()},
            "eventos": list(events),
        })

    # A demonstração foi projetada para uso local; bloqueia escritas de outra origem.
    @app.before_request
    def same_origin():
        if request.method in {"POST", "PUT", "DELETE"}:
            origin = request.headers.get("Origin")
            if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
                return response({"erro": "Origem da solicitação não permitida."}, 403)

    return app


if __name__ == "__main__":
    from waitress import serve

    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "5000"))
    print(f"Aplicação disponível em http://{host}:{port}", flush=True)
    serve(create_app(), host=host, port=port)
