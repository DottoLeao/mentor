# Mentor — Servidor de Conhecimento (Python) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Servidor MCP remoto em Python que responde `buscar_docs` com trechos citados da documentação oficial (MDN JavaScript, TypeScript Handbook, Node.js), expõe os prompts com o "jeito de ensinar" e limita o uso por instalação.

**Architecture:** Um coletor lê o Markdown dos repositórios oficiais (clone raso), divide em trechos por título e grava em Postgres com pgvector. A busca é híbrida: vetor (bge-m3, multilíngue, para pergunta em português sobre doc em inglês) mais full-text `simple` (para identificadores como `Map.prototype.get`), combinados por Reciprocal Rank Fusion. Um servidor FastMCP (transporte streamable HTTP) expõe a ferramenta e os prompts. Nenhum dado pessoal entra ou é guardado.

**Tech Stack:** Python 3.12, uv, `mcp` (SDK oficial, FastMCP), psycopg 3 + pgvector, httpx, pytest, Docker (Postgres `pgvector/pgvector:pg17` local), Ollama (bge-m3) para indexar localmente.

**Spec:** `Vagas/docs/specs/2026-11-12-mentor-programacao-design.md` (seções 5, 6 e 7). Plane: projeto MENTOR, tickets MENTOR-3, 4, 5, 7, 12, 31.

**Planos irmãos (depois deste):** extensão do VS Code + MCP local (M1/M2), evals no CI + reindexação (M3), página do portfólio (M3).

## Global Constraints

- Repositório: `mentor/` (a criar no MENTOR-1), este código em `mentor/server/`.
- Idioma de tudo que o usuário lê (mensagens, prompts, erros): português do Brasil.
- Nenhuma marca de autoria de IA em commits, código, README ou docs.
- O servidor recebe só a pergunta; não recebe nem guarda código ou dados pessoais. Não logar o texto da pergunta junto com o id da instalação.
- Cada trecho guarda: fonte, URL, versão (SHA do commit da fonte) e data de coleta.
- Atribuição obrigatória da MDN (CC-BY-SA 2.5) em toda resposta que citar MDN.
- Dimensão do embedding: 1024 (bge-m3).
- Limite de uso: 200 chamadas de `buscar_docs` por instalação por dia (UTC), identificadas pelo cabeçalho `X-Mentor-Install`.
- Custo: só free tiers (Neon, host do servidor); embeddings do corpus calculados localmente.

## Review Focus

1. **Pergunta em português sobre doc em inglês** ("como pego um valor de um Map?") deve trazer `Map.prototype.get()` no top 5. Teste em Task 5 (com embedder real, marcado `slow`) e no conjunto de recuperação da Task 8.
2. **Pergunta vazia ou gigante** (vazia, só espaços, mais de 2000 caracteres): erro claro em pt-BR, sem consultar o banco. Teste na Task 6.
3. **Fonte desconhecida** (`fonte="python"`): erro claro listando as fontes válidas, não lista vazia silenciosa. Teste na Task 6.
4. **Banco fora do ar ou lento**: a ferramenta devolve mensagem de indisponibilidade em pt-BR em até 5 s, sem stack trace para o usuário. Teste na Task 6.
5. **Chamada sem `X-Mentor-Install`**: recusada com instrução de atualizar a extensão, sem contar no limite de ninguém. Teste na Task 7.

---

### Task 1: Esqueleto do projeto e banco local

**Files:**
- Create: `server/pyproject.toml`, `server/docker-compose.yml`, `server/src/mentor_server/__init__.py`, `server/src/mentor_server/config.py`, `server/src/mentor_server/db/schema.sql`, `server/src/mentor_server/db/connection.py`, `server/tests/conftest.py`
- Test: `server/tests/test_db.py`

**Interfaces:**
- Produces: `Settings` (pydantic-settings) com `database_url: str`, `embed_provider: Literal["fake","ollama","workers_ai"]`, `daily_limit: int = 200`; `get_conn() -> psycopg.Connection` (context manager, com pgvector registrado); `apply_schema(conn) -> None`.
- Produces: fixture pytest `db` que aplica o schema num banco de teste e trunca as tabelas entre testes; testes que usam banco são marcados `@pytest.mark.db` e pulados se `DATABASE_URL` não existir.

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.db
def test_schema_cria_tabelas(db):
    tabelas = {r[0] for r in db.execute(
        "select tablename from pg_tables where schemaname='public'").fetchall()}
    assert {"chunks", "usage"} <= tabelas

@pytest.mark.db
def test_chunks_tem_vetor_1024(db):
    tipo = db.execute(
        "select format_type(atttypid, atttypmod) from pg_attribute "
        "where attrelid='chunks'::regclass and attname='embedding'").fetchone()[0]
    assert tipo == "vector(1024)"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose up -d && uv run pytest tests/test_db.py -v`
Expected: FAIL (tabela `chunks` não existe)

- [ ] **Step 3: Implement schema e conexão**

`schema.sql`: `create extension if not exists vector;` tabela `chunks(id bigserial pk, source text not null, url text not null, title_path text not null, content text not null, version text not null, collected_at timestamptz not null, embedding vector(1024) not null, tsv tsvector generated always as (to_tsvector('simple', title_path || ' ' || content)) stored, unique(source, url, title_path))`; índice HNSW `vector_cosine_ops` em `embedding`; GIN em `tsv`. Tabela `usage(install_id text, day date, count int not null default 0, primary key(install_id, day))`. Tudo idempotente (`if not exists`).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_db.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add server/
git commit -m "feat(server): esqueleto, configuração e schema com pgvector"
```

---

### Task 2: Divisão do Markdown em trechos

**Files:**
- Create: `server/src/mentor_server/ingest/chunker.py`
- Test: `server/tests/ingest/test_chunker.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) class Chunk: source: str; url: str; title_path: str; content: str`
- Produces: `split_markdown(text: str, *, source: str, url: str, max_chars: int = 1200) -> list[Chunk]`

- [ ] **Step 1: Write the failing tests**

```python
def test_divide_por_titulo_e_guarda_caminho():
    md = "---\ntitle: Map\n---\n# Map\nIntro.\n## get()\nRetorna o valor.\n### Exemplo\n```js\nm.get(1)\n```"
    chunks = split_markdown(md, source="mdn", url="https://developer.mozilla.org/x")
    assert [c.title_path for c in chunks] == ["Map", "Map > get()", "Map > get() > Exemplo"]
    assert "m.get(1)" in chunks[2].content

def test_remove_front_matter():
    chunks = split_markdown("---\ntitle: X\n---\n# X\ncorpo", source="s", url="u")
    assert "title:" not in chunks[0].content

def test_secao_longa_vira_varios_trechos_sem_partir_bloco_de_codigo():
    corpo = ("palavra " * 300) + "\n```js\n" + ("x;\n" * 50) + "```\n"
    chunks = split_markdown("# T\n" + corpo, source="s", url="u", max_chars=1200)
    assert len(chunks) > 1
    assert all(c.content.count("```") % 2 == 0 for c in chunks)

def test_secao_vazia_e_ignorada():
    assert [c.title_path for c in split_markdown("# A\n## B\ntexto", source="s", url="u")] == ["A > B"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/ingest/test_chunker.py -v`
Expected: FAIL (`split_markdown` não existe)

- [ ] **Step 3: Implement `split_markdown`**

Percorre linhas mantendo a pilha de títulos (`#`, `##`, `###`) e o estado "dentro de bloco de código". Ao estourar `max_chars`, quebra no último parágrafo fora de bloco de código; um bloco de código maior que `max_chars` fica inteiro num trecho só.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/ingest/test_chunker.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add server/src/mentor_server/ingest/chunker.py server/tests/ingest/
git commit -m "feat(server): divisão do markdown em trechos por título"
```

---

### Task 3: Fontes oficiais (MDN, TypeScript, Node.js)

**Files:**
- Create: `server/src/mentor_server/ingest/sources.py`
- Test: `server/tests/ingest/test_sources.py`, `server/tests/fixtures/` (3 arquivos .md pequenos, um por fonte)

**Interfaces:**
- Produces: `@dataclass(frozen=True) class Source: name: str; repo: str; subdir: str; license: str; url_for: Callable[[Path], str | None]`
- Produces: `SOURCES: dict[str, Source]` com exatamente `"mdn"`, `"typescript"`, `"node"`.
- Produces: `fetch_source(src: Source, workdir: Path) -> tuple[str, list[Path]]` (clone raso + sparse checkout; devolve SHA do commit e os `.md`)

Valores fixos:
- `mdn`: repo `https://github.com/mdn/content`, subdir `files/en-us/web/javascript`, license `CC-BY-SA-2.5`, URL `https://developer.mozilla.org/en-US/docs/Web/JavaScript/<caminho sem index.md>`.
- `typescript`: repo `https://github.com/microsoft/TypeScript-Website`, subdir `packages/documentation/copy/en/handbook-v2`, license a confirmar no MENTOR-5 (registrar `"verificar"` até lá), URL `https://www.typescriptlang.org/docs/handbook/2/<slug>.html` (slug do front matter `permalink`).
- `node`: repo `https://github.com/nodejs/node`, subdir `doc/api`, license `MIT`, URL `https://nodejs.org/docs/latest/api/<arquivo>.html`.

- [ ] **Step 1: Write the failing tests** (sem rede: só `url_for` com os fixtures)

```python
def test_url_mdn():
    p = Path("files/en-us/web/javascript/reference/global_objects/map/get/index.md")
    assert SOURCES["mdn"].url_for(p) == "https://developer.mozilla.org/en-US/docs/Web/JavaScript/reference/global_objects/map/get"

def test_url_node():
    assert SOURCES["node"].url_for(Path("doc/api/fs.md")) == "https://nodejs.org/docs/latest/api/fs.html"

def test_url_typescript_usa_permalink(tmp_path):
    f = tmp_path / "Everyday Types.md"
    f.write_text("---\npermalink: /docs/handbook/2/everyday-types.html\n---\n# T")
    assert SOURCES["typescript"].url_for(f) == "https://www.typescriptlang.org/docs/handbook/2/everyday-types.html"

def test_arquivo_sem_url_e_pulado(tmp_path):
    f = tmp_path / "sem.md"; f.write_text("# sem permalink")
    assert SOURCES["typescript"].url_for(f) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/ingest/test_sources.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `SOURCES` e `fetch_source`** (`git clone --depth 1 --filter=blob:none --sparse` + `git sparse-checkout set <subdir>`, via `subprocess.run(check=True)`)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/ingest/test_sources.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add server/src/mentor_server/ingest/sources.py server/tests/
git commit -m "feat(server): fontes oficiais com URL canônica por arquivo"
```

---

### Task 4: Embeddings e indexação

**Files:**
- Create: `server/src/mentor_server/embed.py`, `server/src/mentor_server/ingest/indexer.py`, `server/src/mentor_server/cli.py`
- Test: `server/tests/test_embed.py`, `server/tests/ingest/test_indexer.py`

**Interfaces:**
- Consumes: `Chunk`, `split_markdown` (Task 2); `SOURCES`, `fetch_source` (Task 3); `get_conn` (Task 1).
- Produces: `class Embedder(Protocol): def embed(self, texts: list[str]) -> list[list[float]]: ...`; `FakeEmbedder` (determinístico por hash, 1024 dims, normalizado); `OllamaEmbedder(model="bge-m3", url="http://localhost:11434")`; `WorkersAIEmbedder(account_id, token, model="@cf/baai/bge-m3")`; `make_embedder(settings) -> Embedder`.
- Produces: `index_source(conn, name: str, embedder: Embedder, workdir: Path) -> int` (devolve nº de trechos gravados); substitui atomicamente os trechos daquela fonte numa transação.
- Produces: comando `uv run mentor-index <fonte|all>`.

- [ ] **Step 1: Write the failing tests**

```python
def test_fake_embedder_e_deterministico_e_1024():
    a, b = FakeEmbedder().embed(["oi", "oi"])
    assert a == b and len(a) == 1024

@pytest.mark.db
def test_indexar_grava_versao_data_e_substitui(db, tmp_path, monkeypatch):
    monkeypatch.setattr(indexer, "fetch_source", fake_fetch(sha="abc123", files=FIXTURE_MDN))
    n1 = index_source(db, "mdn", FakeEmbedder(), tmp_path)
    n2 = index_source(db, "mdn", FakeEmbedder(), tmp_path)
    assert n1 == n2 > 0
    rows = db.execute("select count(*), min(version), max(collected_at) is not null from chunks where source='mdn'").fetchone()
    assert rows == (n1, "abc123", True)

@pytest.mark.db
def test_falha_no_meio_nao_apaga_indice_antigo(db, tmp_path, monkeypatch):
    monkeypatch.setattr(indexer, "fetch_source", fake_fetch(sha="abc123", files=FIXTURE_MDN))
    n = index_source(db, "mdn", FakeEmbedder(), tmp_path)
    with pytest.raises(RuntimeError):
        index_source(db, "mdn", EmbedderQueFalha(), tmp_path)  # levanta RuntimeError no 2º lote
    assert db.execute("select count(*) from chunks where source='mdn'").fetchone()[0] == n
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_embed.py tests/ingest/test_indexer.py -v`
Expected: FAIL

- [ ] **Step 3: Implement embedders, `index_source` e o CLI** (embeddings em lotes de 32; delete + insert da fonte dentro de uma única transação)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_embed.py tests/ingest/test_indexer.py -v`
Expected: all passed

- [ ] **Step 5: Index de verdade, localmente** (requer Ollama com `bge-m3`)

Run: `EMBED_PROVIDER=ollama uv run mentor-index all`
Expected: três linhas `mdn: N trechos`, `typescript: N trechos`, `node: N trechos`, com N > 0.

- [ ] **Step 6: Commit**

```bash
git add server/
git commit -m "feat(server): embeddings e indexação atômica por fonte"
```

---

### Task 5: Busca híbrida

**Files:**
- Create: `server/src/mentor_server/search.py`
- Test: `server/tests/test_search.py`

**Interfaces:**
- Consumes: `Embedder` (Task 4), `get_conn` (Task 1).
- Produces: `@dataclass(frozen=True) class Hit: source: str; url: str; title_path: str; content: str; version: str; collected_at: datetime; score: float`
- Produces: `search(conn, embedder: Embedder, query: str, *, source: str | None = None, k: int = 5) -> list[Hit]`

- Produces (testes): fixture `db_indexado_fake` (fixtures das 3 fontes indexadas com `FakeEmbedder`, incluindo um trecho `Map.prototype.get()` e um de `fs.readFile` do Node) e `db_indexado_bge` (mesmos fixtures com `OllamaEmbedder`; pulado se o Ollama não responder).

Algoritmo: top 20 por distância de cosseno + top 20 por `ts_rank_cd` com `websearch_to_tsquery('simple', query)`, combinados por RRF `score = Σ 1/(60 + rank)`; devolve os `k` maiores, sem repetir `(url, title_path)`.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.db
def test_identificador_exato_vence_pelo_full_text(db_indexado_fake):
    hits = search(db_indexado_fake, FakeEmbedder(), "Map.prototype.get")
    assert hits[0].title_path.startswith("Map.prototype.get()")

@pytest.mark.db
def test_filtro_por_fonte(db_indexado_fake):
    assert {h.source for h in search(db_indexado_fake, FakeEmbedder(), "read file", source="node")} == {"node"}

@pytest.mark.db
def test_sem_duplicatas_e_respeita_k(db_indexado_fake):
    hits = search(db_indexado_fake, FakeEmbedder(), "array", k=3)
    assert len(hits) <= 3 and len({(h.url, h.title_path) for h in hits}) == len(hits)

@pytest.mark.db
@pytest.mark.slow
def test_pergunta_em_portugues_acha_map_get(db_indexado_bge):  # Review Focus 1
    hits = search(db_indexado_bge, OllamaEmbedder(), "como pego um valor de um Map?")
    assert any("Map.prototype.get" in h.title_path for h in hits[:5])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_search.py -v -m "not slow"`
Expected: FAIL

- [ ] **Step 3: Implement `search`** (uma query SQL com duas CTEs e a fusão RRF em SQL)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_search.py -v` (com Ollama ligado para o teste `slow`)
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add server/src/mentor_server/search.py server/tests/test_search.py
git commit -m "feat(server): busca híbrida com RRF"
```

---

### Task 6: Servidor MCP com `buscar_docs` e os prompts de ensino

**Files:**
- Create: `server/src/mentor_server/app.py`, `server/src/mentor_server/prompts/` (`dica.md`, `aula.md`, `exercicio.md`, `revisar.md`, `prova.md`, `entrevista.md`, `regras.md`)
- Test: `server/tests/test_app.py`

**Interfaces:**
- Consumes: `search`, `Hit` (Task 5); `make_embedder` (Task 4).
- Produces: `mcp = FastMCP("mentor-conhecimento")`; ferramenta `buscar_docs(pergunta: str, fonte: str | None = None, k: int = 5) -> dict` que devolve `{"trechos": [{"fonte","url","titulo","trecho","versao","coletado_em"}], "atribuicao": str}`; prompts `dica`, `aula`, `exercicio`, `revisar`, `prova`, `entrevista` (cada um inclui `regras.md`).
- Produces: `create_http_app() -> Starlette` (streamable HTTP em `/mcp`, `GET /health` → `{"ok": true}`).
- Produces (testes): fixtures `client_fake` (banco com fixtures indexadas pelo `FakeEmbedder`) e `client_sem_banco` (`DATABASE_URL` apontando para porta fechada). `call(client, nome, args) -> ToolResult` com `.data: dict`, `.is_error: bool`, `.text: str`; `get_prompt(client, nome) -> str`.
- Fora deste plano: o parâmetro `data?` da spec. Na V1 só existe uma versão indexada por fonte, então ele não tem efeito; volta quando houver histórico de versões.

Valores fixos:
- `k` entre 1 e 10; pergunta com 1 a 2000 caracteres após `strip()`.
- Fontes válidas: `mdn`, `typescript`, `node`.
- `atribuicao` quando houver trecho da MDN: `"Conteúdo da MDN Web Docs (Mozilla e colaboradores), licença CC-BY-SA 2.5."`
- Mensagens de erro (exatas):
  - pergunta inválida: `"A pergunta precisa ter entre 1 e 2000 caracteres."`
  - fonte inválida: `"Fonte desconhecida. Use uma destas: mdn, typescript, node."`
  - banco indisponível: `"A busca está indisponível agora. Tente de novo em alguns minutos."`
- `regras.md` leva, em pt-BR, as regras da skill `~/.claude/skills/mentor/SKILL.md`: a pessoa escreve e o mentor ensina; dicas em camadas 1→4 e a resposta só no nível 4 a pedido; consultar `buscar_docs` antes de ensinar recurso que pode ter mudado e citar a URL; uma ideia por mensagem e pergunta no fim. Sem dados pessoais do Lorenzo (metas, prazos, empresas).

- [ ] **Step 1: Write the failing tests**

```python
async def test_buscar_docs_devolve_citacao(client_fake):
    r = await call(client_fake, "buscar_docs", {"pergunta": "Map.prototype.get"})
    t = r.data["trechos"][0]
    assert t["url"].startswith("https://") and t["versao"] and t["coletado_em"]
    assert "CC-BY-SA" in r.data["atribuicao"]

@pytest.mark.parametrize("pergunta", ["", "   ", "x" * 2001])
async def test_pergunta_invalida(client_fake, pergunta):  # Review Focus 2
    r = await call(client_fake, "buscar_docs", {"pergunta": pergunta})
    assert r.is_error and "entre 1 e 2000" in r.text

async def test_fonte_invalida(client_fake):  # Review Focus 3
    r = await call(client_fake, "buscar_docs", {"pergunta": "x", "fonte": "python"})
    assert r.is_error and "mdn, typescript, node" in r.text

async def test_banco_fora_do_ar(client_sem_banco):  # Review Focus 4
    r = await asyncio.wait_for(call(client_sem_banco, "buscar_docs", {"pergunta": "x"}), 5)
    assert r.is_error and "indisponível" in r.text and "Traceback" not in r.text

async def test_prompts_incluem_regra_do_nivel_4(client_fake):
    for nome in ["dica", "aula", "exercicio", "revisar", "prova", "entrevista"]:
        assert "nível 4" in await get_prompt(client_fake, nome)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_app.py -v`
Expected: FAIL

- [ ] **Step 3: Implement o app e escrever os prompts** (timeout de conexão do psycopg de 3 s; exceções de banco viram a mensagem fixa e vão para o log sem o texto da pergunta)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_app.py -v`
Expected: all passed

- [ ] **Step 5: Teste manual com o Claude Code**

Run: `uv run mentor-serve` e `claude mcp add --transport http mentor http://localhost:8000/mcp`. No Claude Code, perguntar "como pego um valor de um Map em JS?".
Expected: o Claude chama `buscar_docs` e a resposta cita a URL da MDN.

- [ ] **Step 6: Commit**

```bash
git add server/
git commit -m "feat(server): servidor MCP com buscar_docs e prompts de ensino"
```

---

### Task 7: Limite de uso por instalação

**Files:**
- Create: `server/src/mentor_server/ratelimit.py`
- Modify: `server/src/mentor_server/app.py` (middleware na rota `/mcp`)
- Test: `server/tests/test_ratelimit.py`

**Interfaces:**
- Consumes: tabela `usage` (Task 1), `create_http_app` (Task 6).
- Produces: `consume(conn, install_id: str, limit: int, today: date) -> bool` (incrementa com `insert ... on conflict do update ... returning count`; devolve `False` se passou do limite).
- Só chamadas `tools/call` de `buscar_docs` contam; `initialize`, `tools/list` e `prompts/*` não contam.

Mensagens fixas:
- sem cabeçalho: HTTP 400, `"Instalação não identificada. Atualize a extensão Mentor."`
- limite estourado: erro da ferramenta `"Você chegou ao limite de 200 buscas de hoje. O limite volta à meia-noite (UTC)."`

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.db
def test_limite_por_dia(db):
    hoje = date(2026, 11, 13)
    assert all(consume(db, "a", 3, hoje) for _ in range(3))
    assert consume(db, "a", 3, hoje) is False
    assert consume(db, "b", 3, hoje) is True
    assert consume(db, "a", 3, hoje + timedelta(days=1)) is True

async def test_sem_cabecalho_e_recusado_e_nao_conta(http_client, db):  # Review Focus 5
    r = await http_client.post("/mcp", json=TOOLS_CALL_BUSCAR)
    assert r.status_code == 400 and "Atualize a extensão" in r.text
    assert db.execute("select count(*) from usage").fetchone()[0] == 0

async def test_listar_ferramentas_nao_conta(http_client, db):
    await http_client.post("/mcp", json=TOOLS_LIST, headers={"X-Mentor-Install": "a"})
    assert db.execute("select count(*) from usage").fetchone()[0] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_ratelimit.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `consume` e o middleware**

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_ratelimit.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add server/
git commit -m "feat(server): limite diário de buscas por instalação"
```

---

### Task 8: Conjunto de recuperação e métricas (recall@5, MRR)

**Files:**
- Create: `server/evals/retrieval.jsonl` (20 linhas), `server/src/mentor_server/evals/retrieval.py`
- Test: `server/tests/test_retrieval_metrics.py`

**Interfaces:**
- Consumes: `search` (Task 5).
- Produces: `recall_at_k(results: list[list[str]], expected: list[set[str]], k: int) -> float`; `mrr(results, expected) -> float`; comando `uv run mentor-eval-retrieval` que imprime `recall@5=0.XX mrr=0.XX` e grava `server/evals/out/retrieval.json`.

Formato de `retrieval.jsonl`: `{"pergunta": str, "urls_esperadas": [str], "tipo": "pt-sobre-en" | "identificador" | "conceito"}`. Pelo menos 10 linhas do tipo `pt-sobre-en`. As 20 perguntas ficam marcadas como rascunho até o Lorenzo revisar (MENTOR-27).

- [ ] **Step 1: Write the failing tests** (métricas puras, sem banco)

```python
def test_recall_e_mrr():
    res = [["u1", "u2"], ["u3", "u9"], ["u8", "u7"]]
    esp = [{"u2"}, {"u3"}, {"u5"}]
    assert recall_at_k(res, esp, k=2) == pytest.approx(2 / 3)
    assert mrr(res, esp) == pytest.approx((1/2 + 1 + 0) / 3)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_retrieval_metrics.py -v`
Expected: FAIL

- [ ] **Step 3: Implement as métricas, o comando e escrever as 20 perguntas** (URLs canônicas da Task 3)

- [ ] **Step 4: Run tests to verify they pass, then run the eval on the real index**

Run: `uv run pytest tests/test_retrieval_metrics.py -v && EMBED_PROVIDER=ollama uv run mentor-eval-retrieval`
Expected: testes passam; a linha `recall@5=... mrr=...` é impressa. Registrar o número no README como linha de base (sem meta mínima nesta etapa).

- [ ] **Step 5: Commit**

```bash
git add server/evals server/src/mentor_server/evals server/tests/test_retrieval_metrics.py
git commit -m "feat(server): conjunto de recuperação com recall@5 e MRR"
```

---

### Task 9: Imagem para deploy

**Files:**
- Create: `server/Dockerfile`, `server/.dockerignore`, `server/README.md`
- Test: verificação manual (sem teste automatizado)

**Interfaces:**
- Consumes: `create_http_app` (Task 6), variáveis `DATABASE_URL`, `EMBED_PROVIDER=workers_ai`, `CF_ACCOUNT_ID`, `CF_API_TOKEN`, `PORT`.

- [ ] **Step 1: Escrever o Dockerfile** (base `python:3.12-slim`, `uv sync --frozen --no-dev`, usuário não-root, `CMD` sobe `create_http_app` em `0.0.0.0:$PORT`)

- [ ] **Step 2: Build e rodar localmente contra o banco local**

Run: `docker build -t mentor-server server && docker run --rm -p 8000:8000 -e DATABASE_URL=... -e EMBED_PROVIDER=ollama mentor-server` e `curl localhost:8000/health`
Expected: `{"ok":true}`

- [ ] **Step 3: README** com: o que é, arquitetura em 5 linhas, como indexar, como rodar, fontes e licenças com atribuição da MDN, e a linha de base de recuperação da Task 8. Sem marca de autoria de IA.

- [ ] **Step 4: Commit**

```bash
git add server/Dockerfile server/.dockerignore server/README.md
git commit -m "chore(server): imagem de deploy e README"
```

O deploy de verdade (MENTOR-32) depende das contas do MENTOR-6, que são humano no loop.
