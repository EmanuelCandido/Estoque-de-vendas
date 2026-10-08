"""PostgreSQL real, isolado no projeto, sem instalação global ou serviço Windows."""
import json
import os
import secrets
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / ".runtime"
LOCAL = ROOT / ".local"
BIN = RUNTIME / "pgsql" / "bin"
DATA = LOCAL / "postgres"
PORT = 55432
URL = "https://get.enterprisedb.com/postgresql/postgresql-17.11-1-windows-x64-binaries.zip"


def run(command, **kwargs):
    return subprocess.run(command, check=True, creationflags=subprocess.CREATE_NO_WINDOW, **kwargs)


def prepare():
    if sys.platform != "win32":
        raise RuntimeError("O iniciador portátil é para Windows. Use PostgreSQL instalado ou Docker nos demais sistemas.")
    RUNTIME.mkdir(exist_ok=True)
    LOCAL.mkdir(exist_ok=True)
    if not (BIN / "pg_ctl.exe").exists():
        archive = RUNTIME / "postgresql.zip"
        if not archive.exists():
            print("Baixando PostgreSQL portátil oficial (aprox. 325 MB)...", flush=True)
            urllib.request.urlretrieve(URL, archive)
        print("Extraindo PostgreSQL...", flush=True)
        with zipfile.ZipFile(archive) as package:
            # Apenas o servidor e suas bibliotecas; dispensa pgAdmin/documentação.
            for member in package.infolist():
                if member.filename.startswith(("pgsql/bin/", "pgsql/lib/", "pgsql/share/")):
                    target = (RUNTIME / member.filename).resolve()
                    if not target.is_relative_to(RUNTIME.resolve()):
                        raise RuntimeError("Caminho inválido no arquivo PostgreSQL.")
                    package.extract(member, RUNTIME)
    credentials_path = LOCAL / "database.json"
    if credentials_path.exists():
        credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    else:
        credentials = {"password": secrets.token_urlsafe(24)}
        credentials_path.write_text(json.dumps(credentials), encoding="utf-8")
    password = credentials["password"]
    if not (DATA / "PG_VERSION").exists():
        password_path = LOCAL / "init-password.txt"
        password_path.write_text(password, encoding="utf-8")
        try:
            run([str(BIN / "initdb.exe"), "-D", str(DATA), "-U", "postgres", "--encoding=UTF8", "--locale=C",
                 "--auth=scram-sha-256", "--pwfile", str(password_path)])
        finally:
            password_path.unlink(missing_ok=True)
        with (DATA / "postgresql.conf").open("a", encoding="utf-8") as config:
            config.write(f"\nlisten_addresses = '127.0.0.1'\nport = {PORT}\ntimezone = 'America/Sao_Paulo'\n")
    result = subprocess.run([str(BIN / "pg_ctl.exe"), "-D", str(DATA), "status"],
                            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode != 0:
        run([str(BIN / "pg_ctl.exe"), "-D", str(DATA), "-l", str(LOCAL / "postgres.log"), "-w", "start"])
    import psycopg
    dsn = f"postgresql://postgres:{password}@127.0.0.1:{PORT}/estoque_facil"
    with psycopg.connect(dsn.rsplit("/", 1)[0] + "/postgres", autocommit=True) as conn:
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", ("estoque_facil",)).fetchone():
            conn.execute("CREATE DATABASE estoque_facil")
    return dsn


def stop():
    if (BIN / "pg_ctl.exe").exists() and (DATA / "PG_VERSION").exists():
        run([str(BIN / "pg_ctl.exe"), "-D", str(DATA), "-w", "stop", "-m", "fast"])


if __name__ == "__main__":
    if "--parar" in sys.argv:
        stop()
    else:
        dsn = prepare()
        os.environ["DATABASE_URL"] = dsn
        sys.path.insert(0, str(ROOT))
        from scripts.setup_db import setup_database
        setup_database()
        if "--somente-banco" not in sys.argv:
            from src.app import create_app
            from waitress import serve
            print("Aplicação disponível em http://127.0.0.1:5000", flush=True)
            serve(create_app(), host="127.0.0.1", port=5000)
