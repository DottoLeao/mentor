export class McpJsonInvalido extends Error {
  constructor() {
    super("O arquivo .mcp.json desta pasta não é um JSON válido. Corrija ou apague o arquivo e tente de novo; não vou sobrescrever.");
  }
}

export interface OpcoesConexao {
  porta: number;
  token: string;
  urlConhecimento: string;
  idInstalacao: string;
}

/** Devolve o novo conteúdo do .mcp.json do workspace com as entradas do Mentor, preservando o resto. */
export function mesclarMcpJson(atual: string | undefined, o: OpcoesConexao): string {
  let base: Record<string, unknown> = {};
  if (atual !== undefined && atual.trim() !== "") {
    try {
      base = JSON.parse(atual);
    } catch {
      throw new McpJsonInvalido();
    }
    if (typeof base !== "object" || base === null || Array.isArray(base)) throw new McpJsonInvalido();
  }
  const servidores = (typeof base.mcpServers === "object" && base.mcpServers !== null ? base.mcpServers : {}) as Record<string, unknown>;
  const novo = {
    ...base,
    mcpServers: {
      ...servidores,
      "mentor-local": { type: "http", url: `http://127.0.0.1:${o.porta}/mcp`, headers: { "X-Mentor-Token": o.token } },
      "mentor-conhecimento": { type: "http", url: o.urlConhecimento, headers: { "X-Mentor-Install": o.idInstalacao } },
    },
  };
  return JSON.stringify(novo, null, 2) + "\n";
}
