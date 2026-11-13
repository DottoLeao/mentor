import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "vitest";
import { importarDiario } from "../../src/core/importar-diario";
import { memoriaVazia } from "../../src/core/memoria";
import { proximoPasso, registrarErro, registrarNivelamento, registrarResultado } from "../../src/core/motor";
import { TRILHAS } from "../../src/core/trilha";

const T = TRILHAS["typescript-fundamentos"];
const FIXTURE = join(__dirname, "../fixtures/diario-exemplo.md");

test("revisão vencida vem antes do próximo passo", () => {
  const m = {
    ...memoriaVazia(T.id),
    revisoes: [{ item: "staircase", ultima: "2026-11-07", resultado: "sem_dica", proxima: "2026-11-14", intervalo: 7 }],
  };
  expect(proximoPasso(T, m, "2026-11-14").tipo).toBe("revisao");
  expect(proximoPasso(T, m, "2026-11-13")).toMatchObject({ tipo: "passo", passo: { id: T.unidades[0].passos[0].id } });
});

test("registrar 'refazer' não conclui o passo mas agenda para amanhã", () => {
  const id = T.unidades[0].passos[0].id;
  const m = registrarResultado(T, memoriaVazia(T.id), id, "refazer", "2026-11-13");
  expect(m.concluidos[id]).toBeUndefined();
  expect(m.revisoes.find((r) => r.item === id)?.proxima).toBe("2026-11-14");
});

test("registrar sem dica conclui e agenda revisão em 7 dias, sem mutar a entrada", () => {
  const id = T.unidades[0].passos[0].id;
  const antes = memoriaVazia(T.id);
  const m = registrarResultado(T, antes, id, "sem_dica", "2026-11-13");
  expect(m.concluidos[id]).toEqual({ resultado: "sem_dica", data: "2026-11-13" });
  expect(m.revisoes[0]).toMatchObject({ item: id, proxima: "2026-11-20", intervalo: 7 });
  expect(antes.concluidos).toEqual({});
  expect(proximoPasso(T, m, "2026-11-13")).toMatchObject({ passo: { id: T.unidades[0].passos[1].id } });
});

test("revisar um item existente atualiza a mesma linha", () => {
  let m = registrarResultado(T, memoriaVazia(T.id), "staircase", "sem_dica", "2026-11-01");
  m = registrarResultado(T, m, "staircase", "sem_dica", "2026-11-08");
  expect(m.revisoes.filter((r) => r.item === "staircase")).toHaveLength(1);
  expect(m.revisoes[0]).toMatchObject({ proxima: "2026-11-29", intervalo: 21 });
});

test("nivelamento pula unidades dominadas e nunca marca certificado", () => {
  const m = registrarNivelamento(T, memoriaVazia(T.id), [1, 2, 3, 4], "2026-11-13");
  expect(m.nivelamentoFeito).toBe(true);
  expect(proximoPasso(T, m, "2026-11-13")).toMatchObject({ tipo: "passo", passo: { tipo: "certificado" } });
});

test("trilha toda concluída devolve fim", () => {
  let m = memoriaVazia(T.id);
  for (const u of T.unidades) for (const p of u.passos) m.concluidos[p.id] = { resultado: "sem_dica", data: "2026-11-13" };
  expect(proximoPasso(T, m, "2026-11-13").tipo).toBe("fim");
});

test("erro repetido soma vezes", () => {
  let m = registrarErro(memoriaVazia(T.id), "Esquecer o caso vazio", "2026-11-12");
  m = registrarErro(m, "esquecer o caso vazio", "2026-11-13");
  expect(m.erros).toEqual([{ descricao: "Esquecer o caso vazio", vezes: 2, ultima: "2026-11-13" }]);
});

test("importa o diário de exemplo", () => {
  const m = importarDiario(readFileSync(FIXTURE, "utf8"), T, "2026-11-13");
  expect(m.domina).toHaveLength(2);
  expect(m.emAndamento).toEqual(["`let` vs `const`"]);
  expect(m.revisoes.find((r) => r.item === "exercicio-a")?.proxima).toBe("2026-11-20");
  expect(m.revisoes).toHaveLength(2);
  expect(m.concluidos[T.unidades[0].passos[0].id]?.resultado).toBe("nivelamento");
  expect(m.concluidos[T.unidades[1].passos[0].id]).toBeUndefined();
  expect(m.sessoes.map((s) => s.data)).toEqual(["2026-10-01", "2026-10-02"]);
  expect(m.nivelamentoFeito).toBe(true);
});

test("diário sem a seção de revisões não quebra", () => {
  const m = importarDiario("# Diário\n\n## Domina\n- x\n", T, "2026-11-13");
  expect(m.revisoes).toEqual([]);
  expect(m.domina).toEqual(["x"]);
});
