"""Consultas parametrizadas e transações de uma requisição."""
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from src.config import database_url


@contextmanager
def connection():
    # O contexto confirma a transação ao terminar e desfaz tudo se ocorrer erro.
    # prepare_threshold=None: o pooler do Supabase não guarda comandos preparados entre conexões.
    with psycopg.connect(database_url(), row_factory=dict_row, connect_timeout=10, prepare_threshold=None) as conn:
        yield conn
