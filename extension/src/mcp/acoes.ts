/** O que as ferramentas podem pedir ao editor. A extensão implementa com a API do VS Code. */
export interface AcoesEditor {
  abrirArquivo(caminho: string, linha?: number): Promise<void>;
  destacarLinha(caminho: string, linha: number, mensagem: string): Promise<void>;
  abrirConfiguracao(chave: string): Promise<void>;
  rodarNoTerminal(comando: string): Promise<void>;
  sugerirExtensao(id: string, motivo: string): Promise<"instalada" | "recusada">;
}
