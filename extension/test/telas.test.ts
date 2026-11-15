import { expect, test } from "vitest";
import { memoriaVazia } from "../src/core/memoria";
import { TRILHAS } from "../src/core/trilha";
import { renderCaminho } from "../src/telas/caminho";
import { renderPainel } from "../src/telas/painel";

const T = TRILHAS["typescript-fundamentos"];
const M = memoriaVazia(T.id);
const CFG = { metas: ["Certificado de exemplo"], prazos: [] };
const comUmConcluido = { ...M, concluidos: { [T.unidades[0].passos[0].id]: { resultado: "sem_dica" as const, data: "2026-11-13" } } };

test("caminho marca concluído, atual e bloqueado", () => {
  const html = renderCaminho(T, comUmConcluido, "2026-11-13", "n1");
  expect(html).toContain("concluído");
  expect(html).toContain("você está aqui");
  expect(html).toContain("bloqueado");
  expect(html).toContain("https://roadmap.sh/typescript");
  expect(html).toContain(T.unidades[0].passos[1].titulo);
});

test("caminho com revisões vencidas avisa antes do próximo passo", () => {
  const m = { ...M, revisoes: [{ item: "staircase", ultima: "2026-11-07", resultado: "sem_dica", proxima: "2026-11-13", intervalo: 7 }] };
  expect(renderCaminho(T, m, "2026-11-13", "n1")).toContain("1 revisão para hoje");
});

test("texto do usuário é escapado", () => {
  const m = { ...M, erros: [{ descricao: "<script>x</script>", vezes: 2, ultima: "2026-11-13" }] };
  const html = renderPainel(T, m, CFG, "2026-11-13", "n1");
  expect(html).not.toContain("<script>x");
  expect(html).toContain("&lt;script&gt;x");
});

test("painel mostra revisões do dia, porcentagem e metas", () => {
  const html = renderPainel(T, comUmConcluido, CFG, "2026-11-13", "n1");
  expect(html).toContain("Revisão de hoje");
  expect(html).toMatch(/\d+% da trilha/);
  expect(html).toContain("Certificado de exemplo");
});

test("CSP usa o nonce e não permite fontes externas", () => {
  const html = renderCaminho(T, M, "2026-11-13", "abc");
  expect(html).toContain("'nonce-abc'");
  expect(html).toContain("default-src 'none'");
  expect(html).not.toMatch(/https:\/\/fonts\./);
});

test("nenhum style= inline (a CSP da webview bloquearia)", () => {
  const m = { ...M, erros: [{ descricao: "x", vezes: 3, ultima: "2026-11-13" }] };
  expect(renderCaminho(T, comUmConcluido, "2026-11-13", "n")).not.toMatch(/\sstyle="/);
  expect(renderPainel(T, m, CFG, "2026-11-13", "n")).not.toMatch(/\sstyle="/);
});
