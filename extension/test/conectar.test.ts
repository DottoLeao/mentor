import { expect, test } from "vitest";
import { McpJsonInvalido, mesclarMcpJson } from "../src/conectar";

const OPC = { porta: 39217, token: "tk", urlConhecimento: "https://exemplo.dev/mcp", idInstalacao: "inst-1" };

test("cria .mcp.json do zero", () => {
  const j = JSON.parse(mesclarMcpJson(undefined, OPC));
  expect(j.mcpServers["mentor-local"]).toEqual({ type: "http", url: "http://127.0.0.1:39217/mcp", headers: { "X-Mentor-Token": "tk" } });
  expect(j.mcpServers["mentor-conhecimento"]).toEqual({ type: "http", url: "https://exemplo.dev/mcp", headers: { "X-Mentor-Install": "inst-1" } });
});

test("preserva servidores existentes e outras chaves", () => {
  const atual = JSON.stringify({ mcpServers: { outro: { command: "x" } }, extra: 1 });
  const novo = JSON.parse(mesclarMcpJson(atual, OPC));
  expect(Object.keys(novo.mcpServers).sort()).toEqual(["mentor-conhecimento", "mentor-local", "outro"]);
  expect(novo.extra).toBe(1);
});

test("atualiza a porta numa segunda conexão", () => {
  const primeira = mesclarMcpJson(undefined, OPC);
  const j = JSON.parse(mesclarMcpJson(primeira, { ...OPC, porta: 40000 }));
  expect(j.mcpServers["mentor-local"].url).toBe("http://127.0.0.1:40000/mcp");
});

test("JSON inválido não é sobrescrito", () => {
  expect(() => mesclarMcpJson("{ ruim", OPC)).toThrow(McpJsonInvalido);
  expect(() => mesclarMcpJson("[]", OPC)).toThrow(McpJsonInvalido);
});
