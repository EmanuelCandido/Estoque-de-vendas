"""Recria os objetos SQL; insere exemplos apenas em banco totalmente vazio."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import connection

SCRIPTS = [
    "tables/01_schema.sql",
    "tables/02_limite_desconto.sql",
    "migrations/01_simplificar_rotinas.sql",
    "functions/01_calcular_total_venda.sql",
    "procedures/01_baixar_estoque.sql",
    "views/01_relatorio_vendas.sql",
]


def setup_database(seed=True):
    with connection() as conn:
        for name in SCRIPTS:
            conn.execute((ROOT / "database" / name).read_text(encoding="utf-8"))
        if seed:
            empty = conn.execute(
                "SELECT NOT EXISTS (SELECT 1 FROM clientes) "
                "AND NOT EXISTS (SELECT 1 FROM produtos) "
                "AND NOT EXISTS (SELECT 1 FROM vendas) AS vazio"
            ).fetchone()["vazio"]
            if empty:
                conn.execute((ROOT / "database/inserts/01_dados_exemplo.sql").read_text(encoding="utf-8"))
                print("Dados de exemplo inseridos.")
    print("Tabelas, View, Function e Procedure prontas.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sem-exemplos", action="store_true")
    args = parser.parse_args()
    setup_database(seed=not args.sem_exemplos)
