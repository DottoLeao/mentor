import { stat } from "node:fs/promises";
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { isAbsolute, relative, resolve } from "node:path";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod";
import { criarArquivoExercicio } from "../core/exercicio";
import { carregarMemoria, salvarMemoria, type Memoria } from "../core/memoria";
import { proximoPasso, registrarErro, registrarNivelamento, registrarResultado } from "../core/motor";
import { revisoesDoDia } from "../core/revisao";
import { TRILHAS, todosOsPassos } from "../core/trilha";
import type { AcoesEditor } from "./acoes";

export const SEM_PASTA = "Abra uma pasta de estudos no VS Code para o Mentor guardar seu progresso.";
const FORA_DA_PASTA = "O arquivo precisa ficar dentro da pasta de estudos aberta no VS Code.";

export interface Contexto {
  pastaWorkspace(): string | undefined;
  hoje(): string;
  acoes: AcoesEditor;
}

export class PortaOcupada extends Error {
  constructor(public porta: number) {
    super(`A porta ${porta} já está em uso. Troque a configuração mentor.portaLocal.`);
  }
}

type Resposta = { content: { type: "text"; text: string }[]; isError?: boolean };
const ok = (dados: unknown): Resposta => ({
  content: [{ type: "text", text: typeof dados === "string" ? dados : JSON.stringify(dados, null, 2) }],
});
const erro = (msg: string): Resposta => ({ content: [{ type: "text", text: msg }], isError: true });

const filas = new Map<string, Promise<unknown>>();
function naFila<T>(chave: string, fn: () => Promise<T>): Promise<T> {
  const anterior = filas.get(chave) ?? Promise.resolve();
  const atual = anterior.then(fn, fn);
  filas.set(chave, atual.catch(() => undefined));
  return atual;
}

/** Só letras, números, _ . / \ - e espaço, terminando em .ts ou .js: nada que um shell interprete. */
const ARQUIVO_EXECUTAVEL = /^[A-Za-z0-9_./\\ -]+\.(ts|js)$/;

function dentro(dir: string, arquivo: string): string {
  const alvo = resolve(dir, arquivo);
  const rel = relative(resolve(dir), alvo);
  if (rel.startsWith("..") || isAbsolute(rel)) throw new Error(FORA_DA_PASTA);
  return alvo;
}

const PROMPT_NIVELAMENTO = `Você vai fazer a entrevista de nivelamento do Mentor, em português.
Para cada unidade da trilha, em ordem, faça 2 ou 3 perguntas curtas ou peça um exercício de poucas linhas sobre os conceitos dela (use a ferramenta ver_progresso para ver as unidades).
Só considere a unidade dominada se a pessoa demonstrar, não se ela apenas disser que sabe. Pare na primeira unidade em que ela travar.
No fim, chame registrar_nivelamento com a lista dos números das unidades demonstradas e diga qual é o primeiro passo dela.`;

export function criarServidorLocal(ctx: Contexto): McpServer {
  const s = new McpServer({ name: "mentor-local", version: "0.1.0" });

  async function comMemoria(fn: (dir: string, m: Memoria, aviso?: string) => Promise<Resposta>): Promise<Resposta> {
    const dir = ctx.pastaWorkspace();
    if (!dir) return erro(SEM_PASTA);
    // Uma operação de memória por vez nesta pasta: chamadas paralelas não perdem atualizações.
    return naFila(dir, async () => {
      try {
        const { memoria, aviso } = await carregarMemoria(dir);
        const r = await fn(dir, memoria, aviso);
        return aviso ? { ...r, content: [{ type: "text" as const, text: aviso }, ...r.content] } : r;
      } catch (e) {
        return erro((e as Error).message);
      }
    });
  }
  const trilha = (m: Memoria) => TRILHAS[m.trilha] ?? TRILHAS["typescript-fundamentos"];

  s.registerTool("ver_progresso", { description: "Mostra o progresso da pessoa na trilha: unidades, o que domina, erros que se repetem e revisões do dia." }, () =>
    comMemoria(async (_dir, m, aviso) => {
      const t = trilha(m);
      const total = todosOsPassos(t).length;
      const feitos = Object.keys(m.concluidos).length;
      return ok({
        aviso,
        trilha: t.titulo,
        porcentagem: Math.round((feitos / total) * 100),
        unidades: t.unidades.map((u) => ({ numero: u.numero, titulo: u.titulo, conceitos: u.conceitos, roadmap: u.roadmapUrl })),
        domina: m.domina,
        emAndamento: m.emAndamento,
        errosQueSeRepetem: m.erros.filter((e) => e.vezes > 1),
        revisoesDeHoje: revisoesDoDia(m, ctx.hoje()),
        nivelamentoFeito: m.nivelamentoFeito,
      });
    }),
  );

  s.registerTool("proximo_passo", { description: "Diz o que a pessoa deve estudar agora: revisões vencidas primeiro, depois o próximo passo da trilha." }, () =>
    comMemoria(async (_dir, m, aviso) => {
      const p = proximoPasso(trilha(m), m, ctx.hoje());
      if (p.tipo === "passo") {
        return ok({ aviso, tipo: "passo", id: p.passo.id, passo: p.passo.titulo, tipoPasso: p.passo.tipo, hackerrank: p.passo.hackerrank, unidade: `${p.unidade.numero}. ${p.unidade.titulo}`, roadmap: p.unidade.roadmapUrl, nivelamentoFeito: m.nivelamentoFeito });
      }
      return ok({ aviso, ...p });
    }),
  );

  s.registerTool(
    "registrar_resultado",
    {
      description: "Registra o resultado de um passo da trilha ou de um item de revisão, e opcionalmente o erro típico da sessão.",
      inputSchema: { alvo: z.string().min(1), resultado: z.enum(["sem_dica", "com_dica", "refazer"]), erro: z.string().optional() },
    },
    ({ alvo, resultado, erro: descricao }) =>
      comMemoria(async (dir, m) => {
        const hoje = ctx.hoje();
        let nova = registrarResultado(trilha(m), m, alvo, resultado, hoje);
        if (descricao) nova = registrarErro(nova, descricao, hoje);
        await salvarMemoria(dir, nova);
        return ok({ registrado: alvo, resultado, proximaRevisao: nova.revisoes.find((r) => r.item === alvo)?.proxima });
      }),
  );

  s.registerTool(
    "registrar_nivelamento",
    { description: "Marca como dominadas as unidades que a pessoa demonstrou na entrevista de nivelamento.", inputSchema: { unidades: z.array(z.number().int().min(1)) } },
    ({ unidades }) =>
      comMemoria(async (dir, m) => {
        const nova = registrarNivelamento(trilha(m), m, unidades, ctx.hoje());
        await salvarMemoria(dir, nova);
        return ok({ unidadesNiveladas: unidades });
      }),
  );

  const espec = z.object({
    nome: z.string(),
    titulo: z.string(),
    enunciado: z.string(),
    exemplo: z.string(),
    perguntaGuia: z.string(),
    funcao: z.string(),
    parametros: z.string(),
    retorno: z.string(),
    casos: z.array(z.object({ entrada: z.string(), esperado: z.string(), borda: z.boolean().optional() })),
    hackerrank: z.string().optional(),
  });
  s.registerTool(
    "criar_exercicio",
    { description: "Cria o arquivo do exercício na pasta indicada (com testes no fim) e abre no editor. Nunca sobrescreve.", inputSchema: { pasta: z.string(), espec } },
    ({ pasta, espec: e }) =>
      comMemoria(async (dir) => {
        const caminho = await criarArquivoExercicio(dir, pasta, e);
        await ctx.acoes.abrirArquivo(caminho);
        return ok({ criado: caminho, comoRodar: `node ${e.nome}.ts` });
      }),
  );

  const naPasta = (fn: (dir: string) => Promise<Resposta>) => async () => {
    const dir = ctx.pastaWorkspace();
    if (!dir) return erro(SEM_PASTA);
    try {
      return await fn(dir);
    } catch (e) {
      return erro((e as Error).message);
    }
  };

  s.registerTool("abrir_arquivo", { description: "Abre um arquivo da pasta de estudos, opcionalmente numa linha.", inputSchema: { arquivo: z.string(), linha: z.number().int().min(1).optional() } }, ({ arquivo, linha }) =>
    naPasta(async (dir) => {
      await ctx.acoes.abrirArquivo(dentro(dir, arquivo), linha);
      return ok("Arquivo aberto.");
    })(),
  );
  s.registerTool("destacar_linha", { description: "Destaca uma linha de um arquivo com uma mensagem curta, para mostrar onde olhar.", inputSchema: { arquivo: z.string(), linha: z.number().int().min(1), mensagem: z.string().max(200) } }, ({ arquivo, linha, mensagem }) =>
    naPasta(async (dir) => {
      await ctx.acoes.destacarLinha(dentro(dir, arquivo), linha, mensagem);
      return ok("Linha destacada.");
    })(),
  );
  s.registerTool("abrir_configuracao", { description: "Abre as configurações do VS Code filtradas por uma chave, para ensinar onde mudar algo.", inputSchema: { chave: z.string().max(100) } }, ({ chave }) =>
    naPasta(async () => {
      await ctx.acoes.abrirConfiguracao(chave);
      return ok("Configuração aberta.");
    })(),
  );
  s.registerTool("rodar_teste", { description: "Roda um arquivo de exercício (.ts ou .js) com node, sem shell, e mostra a saída no VS Code.", inputSchema: { arquivo: z.string() } }, ({ arquivo }) =>
    naPasta(async (dir) => {
      if (!ARQUIVO_EXECUTAVEL.test(arquivo)) {
        return erro("Só dá para rodar arquivos .ts ou .js da pasta de estudos, com nome sem caracteres especiais.");
      }
      const caminho = dentro(dir, arquivo);
      const info = await stat(caminho).catch(() => undefined);
      if (!info?.isFile()) return erro(`O arquivo ${arquivo} não existe na pasta de estudos.`);
      await ctx.acoes.rodarNode(caminho);
      return ok("Rodando com node no VS Code.");
    })(),
  );
  s.registerTool("sugerir_extensao", { description: "Sugere instalar uma extensão do VS Code, dizendo o motivo. A pessoa decide se instala.", inputSchema: { id: z.string().regex(/^[\w-]+\.[\w-]+$/), motivo: z.string().max(200) } }, ({ id, motivo }) =>
    naPasta(async () => ok({ extensao: id, resposta: await ctx.acoes.sugerirExtensao(id, motivo) }))(),
  );

  s.registerPrompt("nivelamento", { description: "Entrevista de nivelamento: descobre de que unidade a pessoa deve começar." }, () => ({
    messages: [{ role: "user", content: { type: "text", text: PROMPT_NIVELAMENTO } }],
  }));

  return s;
}

async function lerCorpo(req: IncomingMessage): Promise<unknown> {
  const partes: Buffer[] = [];
  for await (const p of req) partes.push(p as Buffer);
  const t = Buffer.concat(partes).toString("utf8");
  return t ? JSON.parse(t) : undefined;
}

/** Sobe o MCP local só em 127.0.0.1, sem estado, exigindo o token em X-Mentor-Token. */
/** Tenta a porta pedida e as seguintes: outra janela do VS Code com o Mentor pode estar usando a padrão. */
export async function iniciarHttpComFallback(
  fabrica: () => McpServer,
  porta: number,
  token: string,
  tentativas = 10,
): Promise<{ porta: number; fechar(): Promise<void> }> {
  let ultimo: unknown;
  for (let i = 0; i < tentativas; i++) {
    try {
      return await iniciarHttp(fabrica, porta + i, token);
    } catch (e) {
      if (!(e instanceof PortaOcupada)) throw e;
      ultimo = e;
    }
  }
  throw ultimo;
}

export function iniciarHttp(fabrica: () => McpServer, porta: number, token: string): Promise<{ porta: number; fechar(): Promise<void> }> {
  const http = createServer(async (req: IncomingMessage, res: ServerResponse) => {
    try {
      if (!req.url?.startsWith("/mcp")) return void res.writeHead(404).end();
      if (req.headers["x-mentor-token"] !== token) return void res.writeHead(401).end("Token inválido.");
      if (req.method !== "POST") return void res.writeHead(405).end();
      const servidor = fabrica();
      const transporte = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
      res.on("close", () => {
        void transporte.close();
        void servidor.close();
      });
      await servidor.connect(transporte);
      await transporte.handleRequest(req, res, await lerCorpo(req));
    } catch {
      if (!res.headersSent) res.writeHead(500).end("Erro interno do Mentor.");
    }
  });
  return new Promise((aceitar, recusar) => {
    http.once("error", (e: NodeJS.ErrnoException) => recusar(e.code === "EADDRINUSE" ? new PortaOcupada(porta) : e));
    http.listen(porta, "127.0.0.1", () =>
      aceitar({ porta, fechar: () => new Promise<void>((ok) => { http.closeAllConnections(); http.close(() => ok()); }) }),
    );
  });
}
