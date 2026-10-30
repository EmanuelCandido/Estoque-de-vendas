"""Cache das leituras no Redis: evita repetir consultas ao Supabase a cada tela."""
import json
from collections import deque
from datetime import datetime, timezone
from time import perf_counter

import redis

PREFIX = "estoque:cache:"
STATS = "estoque:stats"


class Cache:
    def __init__(self, url=None, ttl=60, client=None):
        self.ttl = ttl
        self.events = deque(maxlen=30)
        self.client = client
        if self.client is None and url:
            self.client = redis.Redis.from_url(url, decode_responses=True, socket_timeout=3,
                                               socket_connect_timeout=3)

    @property
    def enabled(self):
        return self.client is not None

    def _log(self, command, key, result, started):
        self.events.appendleft({
            "comando": command, "chave": key, "resultado": result,
            "duracao_ms": round((perf_counter() - started) * 1000, 2),
            "horario": datetime.now(timezone.utc).isoformat(),
        })

    def remember(self, name, load):
        """Cache-aside: devolve do Redis (HIT) ou consulta o banco e grava com TTL (MISS)."""
        if not self.enabled:
            return load(), "DESLIGADO"
        key = PREFIX + name
        started = perf_counter()
        try:
            stored = self.client.get(key)
        except redis.RedisError:
            # Sem Redis a aplicação continua funcionando direto no banco.
            return load(), "INDISPONIVEL"
        if stored is not None:
            self.client.hincrby(STATS, "hits", 1)
            self._log("GET", key, "HIT", started)
            return json.loads(stored), "HIT"
        self._log("GET", key, "MISS", started)
        value = load()
        started = perf_counter()
        try:
            self.client.set(key, json.dumps(value), ex=self.ttl)
            self.client.hincrby(STATS, "misses", 1)
            self._log("SET", key, f"gravado por {self.ttl}s", started)
        except redis.RedisError:
            pass
        return value, "MISS"

    def invalidate(self, *names):
        """Apaga as chaves afetadas por uma escrita para a próxima leitura vir atualizada."""
        if not self.enabled:
            return
        started = perf_counter()
        try:
            keys = []
            for name in names:
                keys.extend(self.client.scan_iter(PREFIX + name + "*"))
            if keys:
                self.client.delete(*keys)
                self.client.hincrby(STATS, "invalidacoes", len(keys))
            self._log("DEL", ", ".join(PREFIX + name + "*" for name in names), f"{len(keys)} chave(s) apagada(s)", started)
        except redis.RedisError:
            pass

    def clear(self):
        self.invalidate("")

    def info(self):
        if not self.enabled:
            return {"conectado": False, "motivo": "Configure REDIS_URL no .env para ativar o cache."}
        started = perf_counter()
        try:
            self.client.ping()
            latency = round((perf_counter() - started) * 1000, 2)
            try:
                version = self.client.info("server").get("redis_version")
            except redis.ResponseError:
                # Alguns serviços gerenciados bloqueiam o comando INFO.
                version = "não informada"
            keys = [{"chave": key, "ttl": self.client.ttl(key)} for key in sorted(self.client.scan_iter(PREFIX + "*"))]
            stats = self.client.hgetall(STATS)
        except redis.RedisError as error:
            return {"conectado": False, "motivo": f"Redis não respondeu: {error}"}
        return {
            "conectado": True, "versao": version, "latencia_ms": latency, "ttl": self.ttl,
            "chaves": keys, "estatisticas": {name: int(stats.get(name, 0)) for name in ("hits", "misses", "invalidacoes")},
            "eventos": list(self.events),
        }
