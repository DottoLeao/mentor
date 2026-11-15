# Mentor — Servidor: ofício (M2) e qualidade (M3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completar o servidor de conhecimento com a documentação do VS Code, recomendação segura de extensões, o prompt de processo profissional, CI de testes, avaliação de conversas com agente simulado e juiz, reindexação agendada e tracing opcional com Langfuse.

**Architecture:** Tudo em `server/` (Python, MCP 2.x `MCPServer`), mais workflows em `.github/workflows/`. Peças que dependem de contas (Neon, OpenRouter, Langfuse, Cloudflare) ficam atrás de variáveis de ambiente: sem a variável, o código degrada para no-op ou pula com mensagem clara, e os testes usam falsos.

**Tech Stack:** Python 3.12, uv, mcp 2.x, psycopg 3, httpx, pytest; GitHub Actions; API compatível com OpenAI (OpenRouter) para evals; SDK `langfuse` opcional.

**Spec:** `docs/specs/2026-11-12-mentor-programacao-design.md` (seções 2, 6, 7). Plane: MENTOR-22, 23, 24, 25, 26, 28, 29, 30. Branch: `feat/servidor-m2-m3`, criado a partir de `feat/servidor-conhecimento`.

## Global Constraints

- Português do Brasil em tudo que a pessoa lê. Sem marca de autoria de IA em nada (commits incluídos).
- O servidor só recebe a pergunta; nada de dado pessoal; não logar pergunta junto com id de instalação.
- Licença VS Code docs: CC BY 3.0 US (conteúdo). MDN CC-BY-SA 2.5, TS CC BY 4.0, Node MIT (já no código).
- Orçamento de evals: até US$ 20/mês; os resultados públicos dizem qual modelo simulou o agente e qual julgou.
- Recomendação de extensão: só de publicador verificado, muitas instalações, atualizada recentemente, sempre com o motivo.
- Rodar a suíte existente inteira (`uv run pytest -q` em `server/`, Postgres em Docker na porta 5433) a cada tarefa.

## Review Focus

1. **Recomendação pedida para um contexto que não casa com nada** ("quero uma extensão de música"): lista vazia com mensagem clara, nunca uma extensão aleatória. Teste na Task 2.
2. **Workflow de evals/reindexação sem os segredos configurados** (fork, PR de terceiro): o job termina verde com aviso "segredo X ausente, pulando", sem falhar a CI nem vazar nada. Teste na Task 5 e 6 (script de verificação).
3. **Juiz devolve texto fora do formato JSON pedido**: o caso conta como "inconclusivo", não derruba a execução nem vira aprovação. Teste na Task 5.
4. **Langfuse indisponível ou chave errada**: a busca continua funcionando, sem atraso perceptível (tracing nunca bloqueia). Teste na Task 7.
5. **Página do VS Code sem `TOCTitle`/título e release notes antigas**: indexadas com a URL certa ou puladas, nunca com URL quebrada. Teste na Task 1.

---

### Task 1: Fonte "vscode" (docs e notas de versão)

**Files:** Modify `server/src/mentor_server/ingest/sources.py`, `server/src/mentor_server/app.py` (lista de fontes e atribuição); Create fixtures `server/tests/fixtures/vscode/docs/editor/debugging.md`, `server/tests/fixtures/vscode/release-notes/v1_95.md`; Test `server/tests/ingest/test_sources.py`, `server/tests/test_app.py`.

**Interfaces:** `SOURCES["vscode"] = Source("vscode", "https://github.com/microsoft/vscode-docs", subdir, "CC-BY-3.0-US", _vscode_url)` — o repositório tem `docs/` e `release-notes/`; `Source.subdir` vira `subdirs: tuple[str, ...]` (todas as fontes atualizadas; `fetch_source` faz sparse-checkout de todas). URLs: `docs/<a>/<b>.md` → `https://code.visualstudio.com/docs/<a>/<b>`; `release-notes/v1_95.md` → `https://code.visualstudio.com/updates/v1_95`; outros arquivos → `None`. `ERRO_FONTE` passa a ser gerado de `SOURCES` (ordem: mdn, typescript, node, vscode). Atribuição: quando houver trecho do VS Code, acrescentar `"Trechos da documentação do Visual Studio Code (Microsoft), licença CC BY 3.0 US (https://creativecommons.org/licenses/by/3.0/us/)."`; com MDN e VS Code, as duas frases separadas por espaço.

- [ ] Testes que falham: URL de docs e de release notes; arquivo fora das duas pastas → `None`; `buscar_docs(fonte="vscode")` aceito; `fonte="python"` → mensagem com as 4 fontes; atribuição do VS Code presente quando há trecho dele.
- [ ] RED → implementar → GREEN (suíte inteira) → commit `feat(server): documentação e notas de versão do VS Code como fonte`.

### Task 2: Ferramenta `recomendar_extensao` com catálogo curado

**Files:** Create `server/src/mentor_server/extensoes.py`, `server/src/mentor_server/data/extensoes.json`; Modify `app.py`; Test `server/tests/test_extensoes.py`.

**Interfaces:** `Extensao(id: str, nome: str, publicador: str, motivo: str, gatilhos: list[str], url: str)`; `carregar_catalogo() -> list[Extensao]`; `recomendar(contexto: str, ja_instaladas: list[str] = []) -> list[Extensao]` (até 3, por número de gatilhos casados, sem diferenciar maiúsculas e acentos; nunca devolve uma já instalada). Ferramenta MCP `recomendar_extensao(contexto: str, ja_instaladas: list[str] = []) -> {"extensoes": [...], "aviso": str}`; lista vazia → aviso `"Nenhuma extensão do catálogo combina com isso. Melhor seguir sem extensão nova."`.

Catálogo inicial (só publicadores verificados): `dbaeumer.vscode-eslint` (gatilhos: estilo, eslint, lint, erro de estilo, ponto e vírgula), `esbenp.prettier-vscode` (formatar, formatação, indentação), `eamodio.gitlens` (git, commit, histórico, blame), `usernamehw.errorlens` (erro, sublinhado vermelho, mensagem de erro), `streetsidesoftware.code-spell-checker` (ortografia, typo, nome de variável), `ms-vscode.vscode-typescript-next` (typescript nightly, versão nova do typescript). Cada `motivo` em pt-BR, uma frase, dizendo quando ajuda. `url` = `https://marketplace.visualstudio.com/items?itemName=<id>`.

- [ ] Testes: "meu código tem erro de estilo" → ESLint primeiro; "git commit" → GitLens; já instalada não volta; "quero uma extensão de música" → vazio + aviso (Review Focus 1); todo item do catálogo tem `id` no formato `publisher.nome` e motivo não vazio.
- [ ] RED → GREEN → commit `feat(server): recomendação de extensões a partir de catálogo curado`.

### Task 3: Prompts `processo` e `vscode`

**Files:** Create `server/src/mentor_server/prompts/processo.md`, `prompts/vscode.md`; Modify `app.py` (`PROMPTS`); Test `server/tests/test_app.py`.

Conteúdo: `processo` — planejar antes de codar (escrever o plano em comentários), commits pequenos com mensagem no imperativo, branch por tarefa, pull request com descrição, revisão de código em 5 passos (link para o modo `revisar`), testes antes de dizer que terminou. `vscode` — ensinar o editor fazendo junto: usar as ferramentas do MCP local (`abrir_configuracao`, `destacar_linha`, `rodar_teste`, `sugerir_extensao`) e `recomendar_extensao`; depurador antes de `console.log`; consultar `buscar_docs(fonte="vscode")` antes de ensinar recurso do editor. Ambos incluem `regras.md`.

- [ ] Teste: os 8 prompts (`dica, aula, exercicio, revisar, prova, entrevista, processo, vscode`) existem e contêm "nível 4"; `processo` contém "commit" e "pull request"; `vscode` contém "destacar_linha" e "buscar_docs".
- [ ] RED → GREEN → commit `feat(server): prompts de processo profissional e de uso do VS Code`.

### Task 4: CI de testes

**Files:** Create `.github/workflows/ci.yml`.

Dois jobs em `pull_request` e `push` para `main`: `server` (ubuntu, serviço `pgvector/pgvector:pg17` com `POSTGRES_DB=mentor_test`, porta 5433→5432, `uv sync`, `uv run pytest -q -m "not slow"` com `TEST_DATABASE_URL`) e `extension` (Node 22, `npm ci`, `npm test`, `npx tsc --noEmit`, `npm run build`).

- [ ] Verificação: `actionlint` se disponível (senão `python -c "import yaml; yaml.safe_load(open(...))"`); push do branch e conferir o resultado com `gh run list --branch feat/servidor-m2-m3 --limit 1` → `completed success`. Se falhar, corrigir até verde.
- [ ] Commit `ci: testes do servidor e da extensão`.

### Task 5: Evals de conversa (agente simulado + juiz)

**Files:** Create `server/src/mentor_server/evals/conversas.py`, `server/evals/conversas.jsonl` (50 casos, marcados `"rascunho": true`), `.github/workflows/evals.yml`; Test `server/tests/test_eval_conversas.py`.

**Interfaces:**
- `class LLM(Protocol): def completar(self, mensagens: list[dict], *, modelo: str) -> str`; `OpenRouterLLM(api_key, base_url="https://openrouter.ai/api/v1")` (chat completions); `LLMFalso(respostas: list[str])` para testes.
- Caso: `{"id", "tipo": "pede_resposta"|"api_recente"|"erro_de_teste"|"vscode"|"extensao"|"fora_de_escopo", "mensagens": [{"role","content"}], "criterios": [str]}`.
- `rodar_caso(caso, agente: LLM, juiz: LLM, buscar: Callable[[str], dict], modelo_agente: str, modelo_juiz: str) -> Resultado` com `Resultado(id, tipo, nao_entregou_resposta: bool|None, citou_fonte: bool|None, aprovado: bool|None, custo_usd: float, latencia_s: float)`; `None` = inconclusivo.
- O agente recebe como sistema o texto do prompt `dica` + `regras.md` e o trecho de `buscar_docs` da última mensagem do usuário (o simulador faz 1 busca por caso); o juiz recebe caso + resposta + critérios e deve devolver JSON `{"nao_entregou_resposta": bool, "citou_fonte": bool, "aprovado": bool}`; JSON inválido → inconclusivo (Review Focus 3).
- `resumir(resultados) -> dict` com taxas sobre os conclusivos e contagem de inconclusivos; CLI `mentor-eval-conversas` grava `server/evals/out/conversas.json` com os nomes dos modelos; sem `OPENROUTER_API_KEY` imprime `"OPENROUTER_API_KEY ausente: evals de conversa pulados."` e sai com código 0.
- Modelos padrão (variáveis `EVAL_MODELO_AGENTE`, `EVAL_MODELO_JUIZ`): barato para o agente, melhor para o juiz; valores escolhidos pelo executor e registrados no ledger.
- `evals.yml`: `workflow_dispatch` e `pull_request` com paths `server/src/mentor_server/prompts/**`; passo que pula com aviso quando o segredo não existe (Review Focus 2).

- [ ] Testes com `LLMFalso`: caso aprovado; juiz devolve "não sei" → inconclusivo e não aprovado; `resumir` ignora inconclusivos nas taxas; CLI sem chave sai 0 com a mensagem; o conjunto tem 50 casos, todos os 6 tipos, ids únicos.
- [ ] RED → GREEN → commit `feat(server): evals de conversa com agente simulado e juiz`.

### Task 6: Reindexação agendada

**Files:** Create `.github/workflows/reindexar.yml`, `server/scripts/checar_segredos.py`; Test `server/tests/test_checar_segredos.py`.

`checar_segredos(nomes: list[str], env: Mapping[str,str]) -> list[str]` (devolve os ausentes); script imprime `"Segredo <X> ausente, pulando."` para cada um e escreve `pular=true` em `$GITHUB_OUTPUT`. Workflow: `schedule` semanal (segunda 06:00 UTC) e `workflow_dispatch`; passos: checar `DATABASE_URL`, `CF_ACCOUNT_ID`, `CF_API_TOKEN`; se não pular, `EMBED_PROVIDER=workers_ai uv run mentor-index all` e depois `uv run mentor-eval-retrieval`, publicando `evals/out/retrieval.json` como artefato.

- [ ] Testes de `checar_segredos` (todos presentes → `[]`; vazio conta como ausente). Commit `ci: reindexação semanal com checagem de segredos`.

### Task 7: Tracing opcional com Langfuse

**Files:** Create `server/src/mentor_server/tracing.py`; Modify `app.py`, `pyproject.toml` (dependência opcional `langfuse`); Test `server/tests/test_tracing.py`.

**Interfaces:** `class Tracer(Protocol): def registrar_busca(self, *, fonte: str|None, k: int, n_trechos: int, latencia_s: float, erro: str|None) -> None`; `NoopTracer`; `LangfuseTracer(cliente)`; `criar_tracer(env) -> Tracer` (Noop sem `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`). `build_server(..., tracer=NoopTracer())` chama `registrar_busca` depois de cada busca. **Nunca** envia o texto da pergunta nem o id da instalação. Exceção do tracer é engolida e logada.

- [ ] Testes: sem variáveis → Noop; tracer falso recebe 1 registro por busca sem campo de pergunta; tracer que lança exceção não muda o resultado da busca (Review Focus 4).
- [ ] RED → GREEN → commit `feat(server): tracing opcional com Langfuse, sem dados da pergunta`.
