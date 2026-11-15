export function esc(s: unknown): string {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

const CSS = `
body{font-family:var(--vscode-font-family);color:var(--vscode-foreground);background:var(--vscode-editor-background);margin:0;padding:24px;line-height:1.5}
main{max-width:860px;margin:0 auto;display:flex;flex-direction:column;gap:20px}
h1{font-size:22px;margin:0}h2{font-size:15px;margin:0 0 8px}
.cartao{background:var(--vscode-sideBar-background);border:1px solid var(--vscode-panel-border);border-radius:12px;padding:16px}
.faixa{border-radius:12px;padding:12px 16px;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
.faixa.concluida{background:var(--vscode-button-secondaryBackground);color:var(--vscode-button-secondaryForeground)}
.faixa.agora{background:var(--vscode-button-background);color:var(--vscode-button-foreground)}
.faixa.depois{border:1px dashed var(--vscode-panel-border)}
.faixa a{color:inherit}
.passos{display:flex;flex-direction:column;align-items:center;gap:10px;margin:12px 0 20px}
.passo{display:flex;flex-direction:column;align-items:center;gap:4px;text-align:center;max-width:220px}
.bola{width:52px;height:52px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700}
.concluido .bola{background:var(--vscode-button-secondaryBackground)}
.atual .bola{width:66px;height:66px;background:var(--vscode-button-background);color:var(--vscode-button-foreground);outline:6px solid var(--vscode-focusBorder)}
.bloqueado .bola{border:2px dashed var(--vscode-panel-border)}
.estado{font-size:12px;opacity:.85}
.aviso{background:var(--vscode-inputValidation-warningBackground);border:1px solid var(--vscode-inputValidation-warningBorder);border-radius:10px;padding:10px 14px}
button{background:var(--vscode-button-background);color:var(--vscode-button-foreground);border:0;border-radius:8px;padding:10px 16px;font:inherit;cursor:pointer;min-height:40px}
.barra{height:10px;border-radius:999px;background:var(--vscode-panel-border);overflow:hidden}.barra>div{height:100%;background:var(--vscode-button-background)}
.chips{display:flex;flex-wrap:wrap;gap:6px}.chip{border:1px solid var(--vscode-panel-border);border-radius:999px;padding:3px 10px;font-size:13px}
ul{margin:0;padding-left:18px}
${[0, 50, 90, 50, 0, -50, -90, -50].map((d, i) => `.d${i}{transform:translateX(${d}px)}`).join("")}
`;

export function pagina(titulo: string, nonce: string, corpo: string, script = ""): string {
  return `<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'nonce-${nonce}'; script-src 'nonce-${nonce}';">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(titulo)}</title>
<style nonce="${nonce}">${CSS}</style>
</head>
<body><main>${corpo}</main>${script ? `<script nonce="${nonce}">${script}</script>` : ""}</body>
</html>`;
}
