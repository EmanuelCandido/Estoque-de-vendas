"""Consultas parametrizadas e transações de uma requisição."""
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from src.config import database_url


@contextmanager
def connection():
    # O contexto confirma a transação ao terminar e desfaz tudo se ocorrer erro.
    with psycopg.connect(database_url(), row_factory=dict_row, connect_timeout=5) as conn:
        yield conn
