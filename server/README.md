# Mentor — servidor de conhecimento

Servidor MCP que responde perguntas de programação com trechos citados da documentação oficial. É a parte compartilhada do Mentor: não recebe código nem dados pessoais, só a pergunta.

## Arquitetura

1. O coletor lê o Markdown dos repositórios oficiais (clone raso e esparso) e divide cada página em trechos por título.
2. Cada trecho é gravado no Postgres com pgvector, com fonte, URL, versão (SHA do commit) e data de coleta.
3. A busca é híbrida: vetor multilíngue (bge-m3), para perguntas em português sobre docs em inglês, mais full-text, para nomes como `Map.prototype.get`. As duas listas são combinadas por Reciprocal Rank Fusion.
4. O servidor MCP (transporte HTTP) expõe a ferramenta `buscar_docs` e os prompts com o jeito de ensinar: `dica`, `aula`, `exercicio`, `revisar`, `prova`, `entrevista`.
5. Cada instalação tem limite de 200 buscas por dia, identificada pelo cabeçalho `X-Mentor-Install`.

## Rodar localmente

```bash
docker compose up -d                       # Postgres com pgvector na porta 5433
uv sync
ollama pull bge-m3                         # embeddings locais
EMBED_PROVIDER=ollama uv run mentor-index all
EMBED_PROVIDER=ollama uv run mentor-serve  # http://localhost:8000/mcp
```

Conectar ao Claude Code:

```bash
claude mcp add --transport http mentor http://localhost:8000/mcp --header "X-Mentor-Install: local"
```

## Testes

```bash
uv run pytest            # sobe tudo que não precisa do Ollama
uv run pytest -m slow    # testes com o modelo bge-m3 real
uv run mentor-eval-retrieval
```

## Fontes e licenças

| Fonte | Repositório | Licença |
|---|---|---|
| MDN (JavaScript) | mdn/content | CC-BY-SA 2.5. Toda resposta com trecho da MDN inclui a atribuição. |
| TypeScript Handbook | microsoft/TypeScript-Website | a confirmar |
| Node.js API | nodejs/node | MIT |

## Qualidade da busca

Conjunto de 20 perguntas em `evals/retrieval.jsonl` (rascunho, em revisão), metade em português sobre documentação em inglês.

Linha de base: ainda não medida com o índice completo.
