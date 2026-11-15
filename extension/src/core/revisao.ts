import { somarDias } from "./datas";
import type { Memoria, Resultado, Revisao } from "./memoria";

/**
 * Regra do diário: sem dica → +7 (+21 se já era revisão com intervalo de 7 ou mais);
 * com dica → +2 (vale também para quem errou numa revisão); refazer → +1.
 */
export function agendar(
  resultado: Resultado,
  intervaloAnterior: number,
  hoje: string,
  foiRevisao: boolean,
): { proxima: string; intervalo: number } {
  let intervalo: number;
  if (resultado === "sem_dica") intervalo = foiRevisao && intervaloAnterior >= 7 ? 21 : 7;
  else if (resultado === "com_dica") intervalo = 2;
  else intervalo = 1;
  return { proxima: somarDias(hoje, intervalo), intervalo };
}

export function revisoesDoDia(m: Memoria, hoje: string): Revisao[] {
  return m.revisoes.filter((r) => r.proxima <= hoje).sort((a, b) => a.proxima.localeCompare(b.proxima));
}
