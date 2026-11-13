"""Provedores de embedding. Todos devolvem vetores de 1024 dimensões (bge-m3)."""

import hashlib
import math
import re
from typing import Protocol

import httpx

DIM = 1024


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


def _normalize(v: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v] if norm else v


class FakeEmbedder:
    """Determinístico e sem rede, para testes: saco de palavras com hashing."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            v = [0.0] * DIM
            tokens = re.findall(r"\w+", text.lower()) or ["<vazio>"]
            for tok in tokens:
                h = int.from_bytes(hashlib.sha256(tok.encode()).digest()[:8], "big")
                v[h % DIM] += 1.0 if (h >> 32) & 1 else -1.0
            out.append(_normalize(v))
        return out


class OllamaEmbedder:
    def __init__(self, model: str = "bge-m3", url: str = "http://localhost:11434", timeout: float = 120):
        self.model, self.url, self.timeout = model, url.rstrip("/"), timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        r = httpx.post(f"{self.url}/api/embed", json={"model": self.model, "input": texts}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()["embeddings"]


class WorkersAIEmbedder:
    def __init__(self, account_id: str, token: str, model: str = "@cf/baai/bge-m3", timeout: float = 30):
        self.account_id, self.token, self.model, self.timeout = account_id, token, model, timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/{self.model}"
        r = httpx.post(
            url,
            headers={"Authorization": f"Bearer {self.token}"},
            json={"text": texts},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()["result"]["data"]


def make_embedder(settings) -> Embedder:
    if settings.embed_provider == "fake":
        return FakeEmbedder()
    if settings.embed_provider == "ollama":
        return OllamaEmbedder(url=settings.ollama_url)
    return WorkersAIEmbedder(settings.cf_account_id, settings.cf_api_token)
