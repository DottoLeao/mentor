# Mentor — Extensão do VS Code e MCP local Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extensão do VS Code que guarda o progresso da pessoa no próprio workspace, expõe isso ao Claude Code por um servidor MCP local (nivelamento, próximo passo, registrar resultado, criar exercício, ações no editor) e mostra o caminho linear e o painel de progresso.

**Architecture:** O núcleo (`src/core/`) é TypeScript puro e testável: trilha, memória, revisão espaçada, importador do diário, gerador de exercício. A extensão hospeda um servidor MCP HTTP em `127.0.0.1`, protegido por token, para que as ferramentas rodem dentro do processo do VS Code e possam usar a API do editor. Um comando escreve o `.mcp.json` do workspace apontando o Claude Code para o MCP local e para o servidor de conhecimento remoto (plano 1).

**Tech Stack:** TypeScript 5, VS Code Extension API (engine `^1.95.0`), esbuild, vitest, `@modelcontextprotocol/sdk` (TS), zod.

**Spec:** `docs/specs/2026-11-12-mentor-programacao-design.md` (seções 2, 4, 5 e 7). Plane: MENTOR-8, 10, 11, 13, 14, 15, 16, 17, 18, 21.

## Global Constraints

- Código em `extension/` no repositório `DottoLeao/mentor`.
- Todo texto que a pessoa lê: português do Brasil.
- Memória local-first: tudo fica em `<workspace>/.mentor/`. Nada pessoal vai para o servidor remoto.
- **O repositório é público: nenhum dado real do Lorenzo vai para fixtures, testes ou exemplos** (o diário real tem metas e decisões pessoais). Os fixtures usam o mesmo formato com conteúdo inventado.
- Agente suportado na V1: Claude Code.
- Nunca entregar a resposta antes do nível 4 (as regras de ensino vêm dos prompts do servidor remoto; o MCP local não ensina, só guarda e age).
- Trilha da V1: as 8 unidades da skill atual, na ordem dela, com link para o roadmap.sh em cada unidade e passo "certificado" = certificado oficial do HackerRank.
- Revisão espaçada (regra do diário atual): sem dica → +7 dias (+21 se o intervalo anterior já era 7 ou mais); com dica → +2 dias; refazer → +1 dia; errou numa revisão → volta para +2.
- Sem marca de autoria de IA em nada.

## Review Focus

1. **`progresso.json` corrompido ou editado à mão** com JSON inválido: a extensão não quebra nem sobrescreve; renomeia para `progresso.json.corrompido-<data>` e avisa em pt-BR. Teste na Task 2.
2. **Nenhuma pasta aberta no VS Code**: comandos e ferramentas respondem "Abra uma pasta de estudos no VS Code para o Mentor guardar seu progresso." em vez de erro. Teste na Task 6.
3. **`.mcp.json` já existe com outros servidores, ou é inválido**: preserva as outras entradas; se for inválido, não sobrescreve e avisa. Teste na Task 6.
4. **Arquivo de exercício que já existe**: nunca sobrescreve; devolve erro dizendo o caminho. Teste na Task 4.
5. **Porta do MCP local ocupada**: mensagem clara sugerindo trocar `mentor.portaLocal`, sem derrubar a extensão. Teste na Task 5.

---

### Task 1: Esqueleto da extensão e a trilha de TypeScript

**Files:**
- Create: `extension/package.json`, `extension/tsconfig.json`, `extension/esbuild.mjs`, `extension/vitest.config.ts`, `extension/src/core/tipos.ts`, `extension/src/core/trilhas/typescript-fundamentos.ts`, `extension/src/core/trilha.ts`
- Test: `extension/test/core/trilha.test.ts`

**Interfaces:**
- Produces (`tipos.ts`):
  - `type TipoPasso = "aula" | "exercicio" | "prova" | "certificado"`
  - `interface Passo { id: string; tipo: TipoPasso; titulo: string; hackerrank?: string }`
  - `interface Unidade { id: string; numero: number; titulo: string; conceitos: string[]; roadmapUrl: string; passos: Passo[] }`
  - `interface Trilha { id: string; titulo: string; unidades: Unidade[] }`
- Produces (`trilha.ts`): `TRILHAS: Record<string, Trilha>` com `"typescript-fundamentos"`; `todosOsPassos(t: Trilha): { unidade: Unidade; passo: Passo }[]` na ordem; `acharPasso(t: Trilha, passoId: string): { unidade: Unidade; passo: Passo } | undefined`.

Valores fixos: 8 unidades com os temas e os exercícios HackerRank da tabela da skill (`~/.claude/skills/mentor/SKILL.md`, seção "A trilha"). Cada unidade: 1 passo `aula` por conceito principal, 1 passo `exercicio` por exercício da tabela, 1 `prova` no fim; `certificado` depois da prova das unidades 4 (Problem Solving Basic), 6 (JavaScript Basic e SQL Basic) e 8 (React Basic). `id` de passo: `u<numero>-<slug>`. `roadmapUrl`: `https://roadmap.sh/typescript` nas unidades 1–4 e 6–7, `https://roadmap.sh/computer-science` nas 5 e 8.

- [ ] **Step 1: Write the failing test**

```ts
test("trilha de TS tem 8 unidades na ordem da skill", () => {
  const t = TRILHAS["typescript-fundamentos"];
  expect(t.unidades.map(u => u.numero)).toEqual([1,2,3,4,5,6,7,8]);
  expect(t.unidades[3].titulo).toBe("Map, Set e contagem");
});
test("ids de passo são únicos e cada unidade termina em prova ou certificado", () => {
  const passos = todosOsPassos(TRILHAS["typescript-fundamentos"]);
  expect(new Set(passos.map(p => p.passo.id)).size).toBe(passos.length);
  for (const u of TRILHAS["typescript-fundamentos"].unidades)
    expect(["prova","certificado"]).toContain(u.passos.at(-1)!.tipo);
});
test("certificados nas unidades 4, 6 e 8", () => {
  const certs = todosOsPassos(TRILHAS["typescript-fundamentos"]).filter(p => p.passo.tipo === "certificado");
  expect(certs.map(c => c.unidade.numero)).toEqual([4, 6, 6, 8]);
});
test("acharPasso devolve a unidade do passo", () => {
  expect(acharPasso(TRILHAS["typescript-fundamentos"], "u4-two-strings")?.unidade.numero).toBe(4);
});
```

- [ ] **Step 2:** `npm test` → FAIL (módulos não existem)
- [ ] **Step 3:** Implementar tipos, a trilha e as duas funções.
- [ ] **Step 4:** `npm test` → PASS
- [ ] **Step 5:** Commit `feat(extensao): esqueleto e trilha de fundamentos em TypeScript`

---

### Task 2: Memória local e revisão espaçada

**Files:**
- Create: `extension/src/core/memoria.ts`, `extension/src/core/revisao.ts`
- Test: `extension/test/core/memoria.test.ts`, `extension/test/core/revisao.test.ts`

**Interfaces:**
- Produces (`memoria.ts`):
  - `type Resultado = "sem_dica" | "com_dica" | "refazer"`
  - `interface Revisao { item: string; ultima: string; resultado: string; proxima: string; intervalo: number }` (datas `AAAA-MM-DD`)
  - `interface Memoria { versao: 1; trilha: string; concluidos: Record<string, { resultado: Resultado | "nivelamento"; data: string }>; domina: string[]; emAndamento: string[]; erros: { descricao: string; vezes: number; ultima: string }[]; revisoes: Revisao[]; sessoes: { data: string; resumo: string }[]; nivelamentoFeito: boolean }`
  - `memoriaVazia(trilha: string): Memoria`
  - `carregarMemoria(dir: string): Promise<{ memoria: Memoria; aviso?: string }>` — `dir` é a pasta do workspace; lê `.mentor/progresso.json`.
  - `salvarMemoria(dir: string, m: Memoria): Promise<void>` — grava em arquivo temporário e renomeia.
- Produces (`revisao.ts`): `agendar(resultado: Resultado, intervaloAnterior: number, hoje: string, foiRevisao: boolean): { proxima: string; intervalo: number }`; `revisoesDoDia(m: Memoria, hoje: string): Revisao[]` (as com `proxima <= hoje`, mais antigas primeiro).

- [ ] **Step 1: Write the failing tests**

```ts
test("agendar segue a regra do diário", () => {
  expect(agendar("sem_dica", 0, "2026-11-13", false)).toEqual({ proxima: "2026-11-20", intervalo: 7 });
  expect(agendar("sem_dica", 7, "2026-11-13", true)).toEqual({ proxima: "2026-12-04", intervalo: 21 });
  expect(agendar("com_dica", 7, "2026-11-13", false)).toEqual({ proxima: "2026-11-15", intervalo: 2 });
  expect(agendar("refazer", 0, "2026-11-13", false)).toEqual({ proxima: "2026-11-14", intervalo: 1 });
  expect(agendar("com_dica", 21, "2026-11-13", true)).toEqual({ proxima: "2026-11-15", intervalo: 2 }); // errou na revisão
});
test("carregar sem arquivo devolve memória vazia", async () => {
  const { memoria } = await carregarMemoria(tmp);
  expect(memoria).toEqual(memoriaVazia("typescript-fundamentos"));
});
test("salvar e carregar ida e volta", async () => { /* salva com 1 concluído, carrega igual */ });
test("JSON corrompido é preservado e gera aviso", async () => {  // Review Focus 1
  await writeFile(join(tmp, ".mentor/progresso.json"), "{ quebrado");
  const { memoria, aviso } = await carregarMemoria(tmp);
  expect(aviso).toMatch(/corrompido/);
  expect(memoria.concluidos).toEqual({});
  expect((await readdir(join(tmp, ".mentor"))).some(f => f.startsWith("progresso.json.corrompido-"))).toBe(true);
});
```

- [ ] **Step 2:** `npm test` → FAIL
- [ ] **Step 3:** Implementar (datas em UTC por string `AAAA-MM-DD`, sem fuso).
- [ ] **Step 4:** `npm test` → PASS
- [ ] **Step 5:** Commit `feat(extensao): memória local com revisão espaçada`

---

### Task 3: Motor do progresso e importador do diário

**Files:**
- Create: `extension/src/core/motor.ts`, `extension/src/core/importar-diario.ts`
- Test: `extension/test/core/motor.test.ts`, `extension/test/core/importar-diario.test.ts`, `extension/test/fixtures/diario-exemplo.md` (inventado, mesmo formato do diário da skill: seções Config, Domina, Em andamento, Revisões com tabela, Marcos, Sessões)

**Interfaces:**
- Consumes: `Trilha`, `todosOsPassos`, `acharPasso` (Task 1); `Memoria`, `Resultado`, `agendar`, `revisoesDoDia` (Task 2).
- Produces (`motor.ts`):
  - `type Proximo = { tipo: "revisao"; revisoes: Revisao[] } | { tipo: "passo"; unidade: Unidade; passo: Passo } | { tipo: "fim" }`
  - `proximoPasso(t: Trilha, m: Memoria, hoje: string): Proximo` — revisões vencidas vêm antes do próximo passo não concluído.
  - `registrarResultado(t: Trilha, m: Memoria, alvo: string, resultado: Resultado, hoje: string): Memoria` — `alvo` é um id de passo ou o nome de um item de revisão; atualiza `concluidos` (só para passo e só se não for `refazer`) e cria/atualiza a revisão com `agendar`. Função pura (devolve cópia).
  - `registrarNivelamento(t: Trilha, m: Memoria, unidadesDominadas: number[], hoje: string): Memoria` — marca todos os passos `aula`/`exercicio`/`prova` dessas unidades como `"nivelamento"` (certificados nunca) e `nivelamentoFeito = true`.
  - `registrarErro(m: Memoria, descricao: string, hoje: string): Memoria` — soma em `vezes` se a descrição já existe (comparação sem diferença de maiúsculas).
- Produces (`importar-diario.ts`): `importarDiario(md: string, t: Trilha, hoje: string): Memoria` — lê Domina, Em andamento, a tabela de Revisões (item, última, resultado, próxima), as sessões (`### AAAA-MM-DD`) e "Semana atual: N" (as unidades anteriores a N viram `"nivelamento"`); `nivelamentoFeito = true`.

- [ ] **Step 1: Write the failing tests**

```ts
test("revisão vencida vem antes do próximo passo", () => {
  let m = memoriaVazia("typescript-fundamentos");
  m = { ...m, revisoes: [{ item: "staircase", ultima: "2026-11-07", resultado: "sem_dica", proxima: "2026-11-14", intervalo: 7 }] };
  expect(proximoPasso(T, m, "2026-11-14").tipo).toBe("revisao");
  expect(proximoPasso(T, m, "2026-11-13")).toMatchObject({ tipo: "passo", passo: { id: T.unidades[0].passos[0].id } });
});
test("registrar 'refazer' não conclui o passo mas agenda para amanhã", () => { /* concluidos sem o id; revisão proxima = hoje+1 */ });
test("nivelamento pula unidades dominadas e nunca marca certificado", () => {
  const m = registrarNivelamento(T, memoriaVazia(T.id), [1, 2, 3, 4], "2026-11-13");
  expect(proximoPasso(T, m, "2026-11-13")).toMatchObject({ tipo: "passo", passo: { tipo: "certificado" } });
});
test("erro repetido soma vezes", () => { /* registrarErro 2x com caixa diferente → vezes 2 */ });
test("importa o diário de exemplo", () => {
  const m = importarDiario(readFileSync(FIXTURE, "utf8"), T, "2026-11-13");
  expect(m.domina.length).toBe(2);
  expect(m.revisoes.find(r => r.item === "exercicio-a")?.proxima).toBe("2026-11-20");
  expect(m.concluidos[T.unidades[0].passos[0].id]?.resultado).toBe("nivelamento"); // semana atual 2 → unidade 1 nivelada
  expect(m.nivelamentoFeito).toBe(true);
});
test("diário sem a seção de revisões não quebra", () => { /* revisoes = [] */ });
```

- [ ] **Step 2:** `npm test` → FAIL
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `npm test` → PASS
- [ ] **Step 5:** Commit `feat(extensao): motor de progresso e importador do diário`

---

### Task 4: Configuração pessoal e gerador de exercício

**Files:**
- Create: `extension/src/core/config.ts`, `extension/src/core/exercicio.ts`
- Test: `extension/test/core/config.test.ts`, `extension/test/core/exercicio.test.ts`

**Interfaces:**
- Produces (`config.ts`): `interface ConfigPessoal { nome?: string; minutosPorDia?: number; metas: string[]; prazos: { descricao: string; data: string }[] }`; `carregarConfig(dir: string): Promise<ConfigPessoal>` (lê `.mentor/config.json`; ausente ou inválido → `{ metas: [], prazos: [] }`).
- Produces (`exercicio.ts`): `interface EspecExercicio { nome: string; titulo: string; enunciado: string; exemplo: string; perguntaGuia: string; funcao: string; parametros: string; retorno: string; casos: { entrada: string; esperado: string; borda?: boolean }[]; hackerrank?: string }`; `gerarExercicio(e: EspecExercicio): string` (formato da skill: cabeçalho JSDoc, assinatura com `// seu código aqui`, bloco de testes com ✅/❌ no fim); `criarArquivoExercicio(dir: string, pasta: string, e: EspecExercicio): Promise<string>` → devolve o caminho; recusa sobrescrever.

Regras: `nome` só `[a-z0-9-]`; pelo menos um caso com `borda: true` (senão erro "Inclua pelo menos um caso de borda"); o arquivo termina com o comando `node <nome>.ts` comentado.

- [ ] **Step 1: Write the failing tests**

```ts
test("gera no formato da skill", () => {
  const src = gerarExercicio(ESPEC);
  expect(src).toContain("export function contarPares(ar: number[]): number {");
  expect(src).toContain("// seu código aqui");
  expect(src).toContain("rode: node contar-pares.ts");
  expect(src).toMatch(/caso de borda/);
});
test("sem caso de borda é recusado", () => { expect(() => gerarExercicio({ ...ESPEC, casos: [{ entrada: "[1]", esperado: "0" }] })).toThrow(/caso de borda/); });
test("nome inválido é recusado", () => { expect(() => gerarExercicio({ ...ESPEC, nome: "../x" })).toThrow(); });
test("não sobrescreve arquivo existente", async () => {  // Review Focus 4
  await criarArquivoExercicio(tmp, "semana-4", ESPEC);
  await expect(criarArquivoExercicio(tmp, "semana-4", ESPEC)).rejects.toThrow(/já existe/);
});
test("config ausente ou inválida vira padrão", async () => { /* {metas:[],prazos:[]} */ });
```

- [ ] **Step 2–4:** RED → implementar → GREEN
- [ ] **Step 5:** Commit `feat(extensao): configuração pessoal e gerador de exercício`

---

### Task 5: Servidor MCP local (HTTP em 127.0.0.1 com token)

**Files:**
- Create: `extension/src/mcp/servidor-local.ts`, `extension/src/mcp/acoes.ts`
- Test: `extension/test/mcp/servidor-local.test.ts`

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces (`acoes.ts`): `interface AcoesEditor { abrirArquivo(caminho: string, linha?: number): Promise<void>; destacarLinha(caminho: string, linha: number, mensagem: string): Promise<void>; abrirConfiguracao(chave: string): Promise<void>; rodarNoTerminal(comando: string): Promise<void>; sugerirExtensao(id: string, motivo: string): Promise<"instalada" | "recusada"> }`.
- Produces (`servidor-local.ts`):
  - `interface Contexto { pastaWorkspace(): string | undefined; hoje(): string; acoes: AcoesEditor }`
  - `criarServidorLocal(ctx: Contexto): McpServer` com ferramentas `ver_progresso`, `proximo_passo`, `registrar_resultado(alvo, resultado, erro?)`, `registrar_nivelamento(unidades: number[])`, `criar_exercicio(pasta, espec)`, `abrir_arquivo`, `destacar_linha`, `abrir_configuracao`, `rodar_teste(arquivo)` (roda `node <arquivo>` no terminal), `sugerir_extensao(id, motivo)`; e o prompt `nivelamento` (explica ao agente como aplicar 2–3 perguntas por unidade e chamar `registrar_nivelamento` só com as unidades demonstradas).
  - `iniciarHttp(servidor: McpServer, porta: number, token: string): Promise<{ porta: number; fechar(): Promise<void> }>` — escuta só em `127.0.0.1`; sem `X-Mentor-Token` correto → 401; porta ocupada → erro `PortaOcupada` com a mensagem "A porta <n> já está em uso. Troque a configuração mentor.portaLocal."

Mensagem fixa sem pasta aberta: `"Abra uma pasta de estudos no VS Code para o Mentor guardar seu progresso."`

- [ ] **Step 1: Write the failing tests** (cliente MCP do SDK por HTTP contra `iniciarHttp` numa porta livre, `AcoesEditor` falso que registra chamadas)

```ts
test("proximo_passo e registrar_resultado gravam no workspace", async () => { /* registra sem_dica no 1º passo → progresso.json tem o id; proximo_passo devolve o 2º */ });
test("sem token → 401", async () => { /* fetch POST /mcp sem cabeçalho → 401 */ });
test("sem pasta aberta → mensagem clara", async () => {  // Review Focus 2
  /* pastaWorkspace() = undefined → isError e texto 'Abra uma pasta de estudos' */
});
test("rodar_teste e destacar_linha chamam as ações do editor", async () => { /* fake registra 'node x.ts' e (arquivo, 3, msg) */ });
test("porta ocupada gera PortaOcupada", async () => {  // Review Focus 5
  /* ocupa a porta com net.createServer e chama iniciarHttp nela */
});
test("criar_exercicio fora da pasta do workspace é recusado", async () => { /* pasta '../fora' → isError */ });
```

- [ ] **Step 2–4:** RED → implementar → GREEN
- [ ] **Step 5:** Commit `feat(extensao): servidor MCP local com ferramentas de progresso e do editor`

---

### Task 6: Conectar ao Claude Code (`.mcp.json`) e ativação da extensão

**Files:**
- Create: `extension/src/conectar.ts`, `extension/src/extension.ts`, `extension/src/vscode-acoes.ts`
- Test: `extension/test/conectar.test.ts`

**Interfaces:**
- Consumes: `criarServidorLocal`, `iniciarHttp`, `AcoesEditor` (Task 5).
- Produces (`conectar.ts`): `mesclarMcpJson(atual: string | undefined, o: { porta: number; token: string; urlConhecimento: string; idInstalacao: string }): string` — devolve o novo conteúdo; mantém as outras entradas de `mcpServers`; entradas `mentor-local` (`type: "http"`, `url: http://127.0.0.1:<porta>/mcp`, `headers: { "X-Mentor-Token": token }`) e `mentor-conhecimento` (`type: "http"`, `url`, `headers: { "X-Mentor-Install": idInstalacao }`); JSON inválido → lança `McpJsonInvalido`.
- `extension.ts`: `activate` gera e guarda (em `globalState`) o token e o `idInstalacao` (UUID aleatório, sem dado pessoal); sobe o servidor local na porta `mentor.portaLocal` (padrão `39217`); comandos `mentor.conectarClaudeCode`, `mentor.abrirCaminho`, `mentor.abrirPainel`, `mentor.importarDiario`. Configurações: `mentor.portaLocal`, `mentor.urlConhecimento` (padrão `http://localhost:8000/mcp` até haver deploy).
- `vscode-acoes.ts`: `AcoesEditor` real com a API do VS Code (`showTextDocument`, decoração na linha, `workbench.action.openSettings`, terminal "Mentor", `showInformationMessage` com botão "Instalar" que chama `workbench.extensions.installExtension`).

- [ ] **Step 1: Write the failing tests**

```ts
test("cria .mcp.json do zero", () => { /* JSON com as 2 entradas */ });
test("preserva servidores existentes", () => {  // Review Focus 3
  const novo = JSON.parse(mesclarMcpJson(JSON.stringify({ mcpServers: { outro: { command: "x" } } }), OPC));
  expect(Object.keys(novo.mcpServers).sort()).toEqual(["mentor-conhecimento", "mentor-local", "outro"]);
});
test("JSON inválido não é sobrescrito", () => { expect(() => mesclarMcpJson("{ ruim", OPC)).toThrow(McpJsonInvalido); });
```

- [ ] **Step 2–4:** RED → implementar → GREEN; depois `npm run build` → `dist/extension.js` gerado sem erro.
- [ ] **Step 5:** Commit `feat(extensao): conexão com o Claude Code e ativação`

---

### Task 7: Telas — caminho linear e painel de progresso

**Files:**
- Create: `extension/src/telas/caminho.ts`, `extension/src/telas/painel.ts`, `extension/src/telas/estilo.ts`
- Modify: `extension/src/extension.ts` (webviews dos comandos `mentor.abrirCaminho` e `mentor.abrirPainel`)
- Test: `extension/test/telas.test.ts`

**Interfaces:**
- Consumes: `Trilha`, `Memoria`, `proximoPasso`, `revisoesDoDia`, `ConfigPessoal`.
- Produces: `renderCaminho(t: Trilha, m: Memoria, hoje: string, nonce: string): string` e `renderPainel(t: Trilha, m: Memoria, c: ConfigPessoal, hoje: string, nonce: string): string` — HTML completo com CSP (`default-src 'none'; style-src 'nonce-…'; script-src 'nonce-…'`), cores do tema do VS Code (`var(--vscode-…)`), seguindo as telas 6 e 2 do canvas. Estados por passo com texto, não só cor: "concluído", "você está aqui", "bloqueado". O botão "Começar" envia `{ tipo: "comecar" }`; a extensão copia para a área de transferência "Mentor, vamos para o próximo passo" e avisa "Cole no Claude Code".

- [ ] **Step 1: Write the failing tests**

```ts
test("caminho marca concluído, atual e bloqueado", () => {
  const html = renderCaminho(T, comUmConcluido, "2026-11-13", "n1");
  expect(html).toContain("concluído"); expect(html).toContain("você está aqui"); expect(html).toContain("bloqueado");
  expect(html).toContain("https://roadmap.sh/typescript");
});
test("texto do usuário é escapado", () => {
  const m = { ...M, erros: [{ descricao: "<script>x</script>", vezes: 1, ultima: "2026-11-13" }] };
  expect(renderPainel(T, m, CFG, "2026-11-13", "n1")).not.toContain("<script>x");
});
test("painel mostra revisões do dia e porcentagem da trilha", () => { /* "Revisão de hoje", "% da trilha" */ });
test("CSP usa o nonce", () => { expect(renderCaminho(T, M, "2026-11-13", "abc")).toContain("'nonce-abc'"); });
```

- [ ] **Step 2–4:** RED → implementar → GREEN; `npm run build` sem erro.
- [ ] **Step 5:** Commit `feat(extensao): telas do caminho linear e do painel`

---

### Task 8: Empacotar e README

**Files:**
- Create: `extension/README.md`, `extension/.vscodeignore`, `extension/LICENSE` (MIT)
- Test: verificação manual

- [ ] **Step 1:** `npx @vscode/vsce package --no-dependencies` → gera `mentor-0.1.0.vsix` sem erro (dependências já embutidas pelo esbuild).
- [ ] **Step 2:** README: o que é, como instalar o `.vsix`, o comando "Mentor: conectar ao Claude Code", onde ficam os dados (`.mentor/`), privacidade (nada pessoal sai do computador), e as telas. Sem marca de autoria de IA.
- [ ] **Step 3:** Commit `chore(extensao): empacotamento e README`

A publicação no Marketplace é o MENTOR-37 (humano no loop).
