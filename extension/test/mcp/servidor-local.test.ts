import { mkdtemp, readFile } from "node:fs/promises";
import { createServer, type Server } from "node:net";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { afterEach, beforeEach, expect, test } from "vitest";
import type { AcoesEditor } from "../../src/mcp/acoes";
import { PortaOcupada, criarServidorLocal, iniciarHttp, iniciarHttpComFallback, type Contexto } from "../../src/mcp/servidor-local";
import { mkdir, writeFile } from "node:fs/promises";
import { TRILHAS } from "../../src/core/trilha";

const T = TRILHAS["typescript-fundamentos"];
const TOKEN = "token-de-teste";

class AcoesFalsas implements AcoesEditor {
  chamadas: string[] = [];
  async abrirArquivo(c: string, l?: number) { this.chamadas.push(`abrir ${c} ${l ?? ""}`.trim()); }
  async destacarLinha(c: string, l: number, m: string) { this.chamadas.push(`destacar ${c} ${l} ${m}`); }
  async abrirConfiguracao(k: string) { this.chamadas.push(`config ${k}`); }
  async rodarNode(arquivo: string) { this.chamadas.push(`node ${arquivo}`); }
  async sugerirExtensao(id: string, motivo: string) { this.chamadas.push(`ext ${id} ${motivo}`); return "recusada" as const; }
}

let tmp: string | undefined;
let acoes: AcoesFalsas;
let http: { porta: number; fechar(): Promise<void> } | undefined;

function ctx(): Contexto {
  return { pastaWorkspace: () => tmp, hoje: () => "2026-11-14", acoes };
}

async function portaLivre(): Promise<number> {
  return new Promise((ok) => {
    const s = createServer().listen(0, "127.0.0.1", () => {
      const p = (s.address() as { port: number }).port;
      s.close(() => ok(p));
    });
  });
}

async function cliente() {
  const c = new Client({ name: "teste", version: "0" });
  await c.connect(
    new StreamableHTTPClientTransport(new URL(`http://127.0.0.1:${http!.porta}/mcp`), {
      requestInit: { headers: { "X-Mentor-Token": TOKEN } },
    }),
  );
  return c;
}

function texto(r: any): string {
  return r.content.map((c: any) => c.text).join("\n");
}

beforeEach(async () => {
  tmp = await mkdtemp(join(tmpdir(), "mentor-"));
  acoes = new AcoesFalsas();
  http = await iniciarHttp(() => criarServidorLocal(ctx()), await portaLivre(), TOKEN);
});
afterEach(async () => {
  await http?.fechar();
});

test("proximo_passo e registrar_resultado gravam no workspace", async () => {
  const c = await cliente();
  const primeiro = T.unidades[0].passos[0].id;
  expect(texto(await c.callTool({ name: "proximo_passo", arguments: {} }))).toContain(primeiro);
  await c.callTool({ name: "registrar_resultado", arguments: { alvo: primeiro, resultado: "sem_dica" } });
  const salvo = JSON.parse(await readFile(join(tmp!, ".mentor/progresso.json"), "utf8"));
  expect(salvo.concluidos[primeiro].resultado).toBe("sem_dica");
  expect(texto(await c.callTool({ name: "proximo_passo", arguments: {} }))).toContain(T.unidades[0].passos[1].id);
  await c.close();
});

test("registrar_resultado com erro soma no histórico de erros", async () => {
  const c = await cliente();
  await c.callTool({ name: "registrar_resultado", arguments: { alvo: "x", resultado: "com_dica", erro: "Esquecer o caso vazio" } });
  const salvo = JSON.parse(await readFile(join(tmp!, ".mentor/progresso.json"), "utf8"));
  expect(salvo.erros[0]).toMatchObject({ descricao: "Esquecer o caso vazio", vezes: 1 });
  await c.close();
});

test("sem token → 401", async () => {
  const r = await fetch(`http://127.0.0.1:${http!.porta}/mcp`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json, text/event-stream" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/list" }),
  });
  expect(r.status).toBe(401);
});

test("sem pasta aberta → mensagem clara", async () => {
  tmp = undefined;
  const c = await cliente();
  const r: any = await c.callTool({ name: "proximo_passo", arguments: {} });
  expect(r.isError).toBe(true);
  expect(texto(r)).toContain("Abra uma pasta de estudos no VS Code");
  await c.close();
});

test("rodar_teste e destacar_linha chamam as ações do editor", async () => {
  const c = await cliente();
  await mkdir(join(tmp!, "semana-4"), { recursive: true });
  await writeFile(join(tmp!, "semana-4/x.ts"), "");
  await c.callTool({ name: "rodar_teste", arguments: { arquivo: "semana-4/x.ts" } });
  await c.callTool({ name: "destacar_linha", arguments: { arquivo: "semana-4/x.ts", linha: 3, mensagem: "olhe aqui" } });
  expect(acoes.chamadas).toContain(`node ${join(tmp!, "semana-4", "x.ts")}`);
  expect(acoes.chamadas.some((x) => x.startsWith("destacar") && x.includes(" 3 olhe aqui"))).toBe(true);
  await c.close();
});

test("criar_exercicio fora da pasta do workspace é recusado", async () => {
  const c = await cliente();
  const r: any = await c.callTool({
    name: "criar_exercicio",
    arguments: {
      pasta: "../fora",
      espec: { nome: "x", titulo: "x", enunciado: "x", exemplo: "x", perguntaGuia: "x", funcao: "f", parametros: "a: number", retorno: "number", casos: [{ entrada: "1", esperado: "1", borda: true }] },
    },
  });
  expect(r.isError).toBe(true);
  expect(texto(r)).toMatch(/dentro da pasta/);
  await c.close();
});

test("porta ocupada gera PortaOcupada", async () => {
  const ocupada = await portaLivre();
  const s: Server = createServer().listen(ocupada, "127.0.0.1");
  await new Promise((ok) => s.once("listening", ok));
  await expect(iniciarHttp(() => criarServidorLocal(ctx()), ocupada, TOKEN)).rejects.toBeInstanceOf(PortaOcupada);
  await new Promise((ok) => s.close(ok));
});

test("prompt de nivelamento orienta a chamar registrar_nivelamento", async () => {
  const c = await cliente();
  const p = await c.getPrompt({ name: "nivelamento" });
  expect(JSON.stringify(p.messages)).toContain("registrar_nivelamento");
  await c.close();
});


test("rodar_teste recusa nomes que poderiam injetar comando e arquivos que não existem", async () => {
  const c = await cliente();
  for (const arquivo of ["a” ; calc ; “b.ts", "x.ts\nwhoami", "%PATH%.ts", "nao-existe.ts", "x.py"]) {
    const r: any = await c.callTool({ name: "rodar_teste", arguments: { arquivo } });
    expect(r.isError, arquivo).toBe(true);
  }
  expect(acoes.chamadas.filter((x) => x.startsWith("node"))).toEqual([]);
  await c.close();
});

test("aviso de arquivo corrompido chega também em registrar_resultado", async () => {
  await mkdir(join(tmp!, ".mentor"), { recursive: true });
  await writeFile(join(tmp!, ".mentor/progresso.json"), "{ quebrado");
  const c = await cliente();
  const r: any = await c.callTool({ name: "registrar_resultado", arguments: { alvo: "x", resultado: "sem_dica" } });
  expect(texto(r)).toMatch(/corrompido/);
  await c.close();
});

test("chamadas simultâneas não perdem atualizações", async () => {
  const c = await cliente();
  await Promise.all(
    Array.from({ length: 8 }, (_, i) => c.callTool({ name: "registrar_resultado", arguments: { alvo: `item-${i}`, resultado: "sem_dica" } })),
  );
  const salvo = JSON.parse(await readFile(join(tmp!, ".mentor/progresso.json"), "utf8"));
  expect(salvo.revisoes).toHaveLength(8);
  await c.close();
});

test("com a porta ocupada, usa a próxima livre", async () => {
  const ocupada = await portaLivre();
  const s: Server = createServer().listen(ocupada, "127.0.0.1");
  await new Promise((ok) => s.once("listening", ok));
  const h = await iniciarHttpComFallback(() => criarServidorLocal(ctx()), ocupada, TOKEN, 5);
  expect(h.porta).not.toBe(ocupada);
  await h.fechar();
  await new Promise((ok) => s.close(ok));
});
