import { randomUUID } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import * as vscode from "vscode";
import { mesclarMcpJson } from "./conectar";
import { hojeLocal } from "./core/datas";
import { importarDiario } from "./core/importar-diario";
import { carregarMemoria, salvarMemoria } from "./core/memoria";
import { TRILHAS } from "./core/trilha";
import { SEM_PASTA, criarServidorLocal, iniciarHttpComFallback, type Contexto } from "./mcp/servidor-local";
import { AcoesVsCode } from "./vscode-acoes";
import { carregarConfig } from "./core/config";
import { renderCaminho } from "./telas/caminho";
import { renderPainel } from "./telas/painel";

let servidor: { porta: number; fechar(): Promise<void> } | undefined;

export function pastaWorkspace(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}

function segredo(memento: vscode.Memento, chave: string): string {
  let v = memento.get<string>(chave);
  if (!v) {
    v = randomUUID();
    void memento.update(chave, v);
  }
  return v;
}

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  // Token por pasta: duas janelas do VS Code nunca aceitam o Claude Code uma da outra.
  const token = segredo(context.workspaceState, "mentor.token");
  const idInstalacao = segredo(context.globalState, "mentor.idInstalacao");
  const config = () => vscode.workspace.getConfiguration("mentor");
  const contexto: Contexto = { pastaWorkspace, hoje: () => hojeLocal(), acoes: new AcoesVsCode() };

  try {
    servidor = await iniciarHttpComFallback(() => criarServidorLocal(contexto), config().get<number>("portaLocal", 39217), token);
  } catch (e) {
    void vscode.window.showWarningMessage((e as Error).message);
  }

  const abrirTela = (titulo: string, render: (dir: string, nonce: string) => Promise<string>) => async () => {
    const dir = pastaWorkspace();
    if (!dir) return void vscode.window.showWarningMessage(SEM_PASTA);
    const painel = vscode.window.createWebviewPanel("mentor", titulo, vscode.ViewColumn.Active, { enableScripts: true });
    const atualizar = async () => {
      painel.webview.html = await render(dir, randomUUID().replace(/-/g, ""));
    };
    await atualizar();
    painel.onDidChangeViewState((e) => e.webviewPanel.visible && void atualizar());
    painel.webview.onDidReceiveMessage(async (msg) => {
      if (msg?.tipo === "comecar") {
        await vscode.env.clipboard.writeText("Mentor, vamos para o próximo passo.");
        void vscode.window.showInformationMessage("Copiei \"Mentor, vamos para o próximo passo.\". Cole na conversa do Claude Code.");
      }
    });
  };
  const trilha = () => TRILHAS["typescript-fundamentos"];

  context.subscriptions.push(
    vscode.commands.registerCommand(
      "mentor.abrirCaminho",
      abrirTela("Mentor · Caminho", async (dir, nonce) => {
        const { memoria, aviso } = await carregarMemoria(dir);
        if (aviso) void vscode.window.showWarningMessage(aviso);
        return renderCaminho(TRILHAS[memoria.trilha] ?? trilha(), memoria, hojeLocal(), nonce);
      }),
    ),
    vscode.commands.registerCommand(
      "mentor.abrirPainel",
      abrirTela("Mentor · Progresso", async (dir, nonce) => {
        const { memoria, aviso } = await carregarMemoria(dir);
        if (aviso) void vscode.window.showWarningMessage(aviso);
        return renderPainel(TRILHAS[memoria.trilha] ?? trilha(), memoria, await carregarConfig(dir), hojeLocal(), nonce);
      }),
    ),
    vscode.commands.registerCommand("mentor.conectarClaudeCode", async () => {
      const dir = pastaWorkspace();
      if (!dir) return void vscode.window.showWarningMessage(SEM_PASTA);
      if (!servidor) return void vscode.window.showWarningMessage("O servidor local do Mentor não está rodando. Confira a configuração mentor.portaLocal e recarregue a janela.");
      const arquivo = join(dir, ".mcp.json");
      let atual: string | undefined;
      try {
        atual = await readFile(arquivo, "utf8");
      } catch {
        atual = undefined;
      }
      try {
        const conteudo = mesclarMcpJson(atual, { porta: servidor.porta, token, urlConhecimento: config().get<string>("urlConhecimento", "http://localhost:8000/mcp"), idInstalacao });
        await writeFile(arquivo, conteudo, "utf8");
      } catch (e) {
        return void vscode.window.showErrorMessage((e as Error).message);
      }
      void vscode.window.showInformationMessage("Pronto: o Claude Code desta pasta agora enxerga o Mentor. Reinicie a conversa do Claude Code e diga \"Mentor, qual o próximo passo?\". O .mcp.json tem um token local; não publique esse arquivo.");
    }),

    vscode.commands.registerCommand("mentor.importarDiario", async () => {
      const dir = pastaWorkspace();
      if (!dir) return void vscode.window.showWarningMessage(SEM_PASTA);
      const escolha = await vscode.window.showOpenDialog({ canSelectMany: false, filters: { Markdown: ["md"] }, openLabel: "Importar diário" });
      if (!escolha?.[0]) return;
      const { memoria: atual, aviso } = await carregarMemoria(dir);
      if (aviso) void vscode.window.showWarningMessage(aviso);
      if (Object.keys(atual.concluidos).length > 0) {
        const ok = await vscode.window.showWarningMessage("Já existe progresso nesta pasta. Importar o diário substitui esse progresso.", { modal: true }, "Substituir");
        if (ok !== "Substituir") return;
      }
      const md = await readFile(escolha[0].fsPath, "utf8");
      const memoria = importarDiario(md, TRILHAS["typescript-fundamentos"], hojeLocal());
      await salvarMemoria(dir, memoria);
      void vscode.window.showInformationMessage(`Diário importado: ${memoria.revisoes.length} revisões e ${Object.keys(memoria.concluidos).length} passos já feitos.`);
    }),
  );
}

export async function deactivate(): Promise<void> {
  await servidor?.fechar();
}
