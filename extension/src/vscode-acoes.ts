import * as vscode from "vscode";
import { dirname } from "node:path";
import type { AcoesEditor } from "./mcp/acoes";

const destaque = vscode.window.createTextEditorDecorationType({
  backgroundColor: new vscode.ThemeColor("editor.findMatchHighlightBackground"),
  isWholeLine: true,
});



export class AcoesVsCode implements AcoesEditor {
  async abrirArquivo(caminho: string, linha?: number): Promise<void> {
    const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(caminho));
    const editor = await vscode.window.showTextDocument(doc, { preview: false });
    if (linha) {
      const pos = new vscode.Position(linha - 1, 0);
      editor.selection = new vscode.Selection(pos, pos);
      editor.revealRange(new vscode.Range(pos, pos), vscode.TextEditorRevealType.InCenter);
    }
  }

  async destacarLinha(caminho: string, linha: number, mensagem: string): Promise<void> {
    await this.abrirArquivo(caminho, linha);
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;
    const faixa = editor.document.lineAt(Math.min(linha - 1, editor.document.lineCount - 1)).range;
    editor.setDecorations(destaque, [{ range: faixa, hoverMessage: mensagem, renderOptions: { after: { contentText: `  ← ${mensagem}`, color: new vscode.ThemeColor("editorCodeLens.foreground") } } }]);
  }

  async abrirConfiguracao(chave: string): Promise<void> {
    await vscode.commands.executeCommand("workbench.action.openSettings", chave);
  }

  async rodarNode(arquivo: string): Promise<void> {
    // ProcessExecution não passa por shell: o caminho vai como argumento, sem ser interpretado.
    const tarefa = new vscode.Task(
      { type: "mentor", arquivo },
      vscode.TaskScope.Workspace,
      `Mentor: rodar ${vscode.workspace.asRelativePath(arquivo)}`,
      "mentor",
      new vscode.ProcessExecution("node", [arquivo], { cwd: dirname(arquivo) }),
    );
    tarefa.presentationOptions = { reveal: vscode.TaskRevealKind.Always, panel: vscode.TaskPanelKind.Dedicated, clear: true };
    await vscode.tasks.executeTask(tarefa);
  }

  async sugerirExtensao(id: string, motivo: string): Promise<"instalada" | "recusada"> {
    const escolha = await vscode.window.showInformationMessage(`O Mentor sugere a extensão ${id}: ${motivo}`, "Instalar", "Agora não");
    if (escolha !== "Instalar") return "recusada";
    await vscode.commands.executeCommand("workbench.extensions.installExtension", id);
    return "instalada";
  }
}
