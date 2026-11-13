import { expect, test } from "vitest";
import { agendar, revisoesDoDia } from "../../src/core/revisao";
import { memoriaVazia } from "../../src/core/memoria";

test("agendar segue a regra do diário", () => {
  expect(agendar("sem_dica", 0, "2026-11-13", false)).toEqual({ proxima: "2026-11-20", intervalo: 7 });
  expect(agendar("sem_dica", 7, "2026-11-13", true)).toEqual({ proxima: "2026-12-04", intervalo: 21 });
  expect(agendar("com_dica", 7, "2026-11-13", false)).toEqual({ proxima: "2026-11-15", intervalo: 2 });
  expect(agendar("refazer", 0, "2026-11-13", false)).toEqual({ proxima: "2026-11-14", intervalo: 1 });
  expect(agendar("com_dica", 21, "2026-11-13", true)).toEqual({ proxima: "2026-11-15", intervalo: 2 });
});

test("virada de mês e de ano", () => {
  expect(agendar("sem_dica", 0, "2026-12-28", false).proxima).toBe("2027-01-04");
});

test("revisoesDoDia traz só as vencidas, mais antigas primeiro", () => {
  const m = {
    ...memoriaVazia("typescript-fundamentos"),
    revisoes: [
      { item: "b", ultima: "2026-11-01", resultado: "sem_dica", proxima: "2026-11-12", intervalo: 7 },
      { item: "a", ultima: "2026-11-01", resultado: "sem_dica", proxima: "2026-11-10", intervalo: 7 },
      { item: "c", ultima: "2026-11-01", resultado: "sem_dica", proxima: "2026-11-20", intervalo: 7 },
    ],
  };
  expect(revisoesDoDia(m, "2026-11-13").map((r) => r.item)).toEqual(["a", "b"]);
});
