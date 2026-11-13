import { randomUUID } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import * as vscode from "vscode";
import { mesclarMcpJson } from "./conectar";
import { hojeLocal } from "./core/datas";
import { importarDiario } from "./core/importar-diario";
import { carregarMemoria, salvarMemoria } from "./core/memoria";
import { TRILHAS } from "./core/trilha";
import { SEM_PASTA, criarServidorLocal, iniciarHttp, type Contexto } from "./mcp/servidor-local";
import { AcoesVsCode } from "./vscode-acoes";

let servidor: { porta: number; fechar(): Promise<void> } | undefined;

export function pastaWorkspace(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}

function segredo(ctx: vscode.ExtensionContext, chave: string): string {
  let v = ctx.globalState.get<string>(chave);
  if (!v) {
    v = randomUUID();
    void ctx.globalState.update(chave, v);
  }
  return v;
}

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  const token = segredo(context, "mentor.token");
  const idInstalacao = segredo(context, "mentor.idInstalacao");
  const config = () => vscode.workspace.getConfiguration("mentor");
  const contexto: Contexto = { pastaWorkspace, hoje: () => hojeLocal(), acoes: new AcoesVsCode() };

  try {
    servidor = await iniciarHttp(() => criarServidorLocal(contexto), config().get<number>("portaLocal", 39217), token);
  } catch (e) {
    void vscode.window.showWarningMessage((e as Error).message);
  }

  context.subscriptions.push(
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
      const { memoria: atual } = await carregarMemoria(dir);
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
