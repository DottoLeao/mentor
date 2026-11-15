import type { ConfigPessoal } from "../core/config";
import type { Memoria } from "../core/memoria";
import { proximoPasso } from "../core/motor";
import { revisoesDoDia } from "../core/revisao";
import type { Trilha } from "../core/tipos";
import { todosOsPassos } from "../core/trilha";
import { esc, pagina } from "./estilo";

const chips = (xs: string[]) => (xs.length ? `<div class="chips">${xs.map((x) => `<span class="chip">${esc(x)}</span>`).join("")}</div>` : "<p>Nada ainda.</p>");

/** Painel de progresso: onde está, revisões do dia, o que domina, erros que se repetem e metas. */
export function renderPainel(t: Trilha, m: Memoria, c: ConfigPessoal, hoje: string, nonce: string): string {
  const total = todosOsPassos(t).length;
  const feitos = Object.keys(m.concluidos).length;
  const pct = Math.round((feitos / total) * 100);
  const prox = proximoPasso(t, { ...m, revisoes: [] }, hoje);
  const unidade = prox.tipo === "passo" ? `Unidade ${prox.unidade.numero} de ${t.unidades.length}: ${esc(prox.unidade.titulo)}` : "Trilha concluída";
  const revisoes = revisoesDoDia(m, hoje);
  const erros = m.erros.filter((e) => e.vezes > 1).sort((a, b) => b.vezes - a.vezes);

  const corpo = `
<h1>${c.nome ? `Progresso de ${esc(c.nome)}` : "Seu progresso"}</h1>
<section class="cartao"><h2>Onde você está</h2><p>${unidade}</p>
<div class="barra" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"><div class="p${pct}"></div></div>
<p class="estado">${pct}% da trilha · ${feitos} de ${total} passos</p></section>
<section class="cartao"><h2>Revisão de hoje</h2>${
    revisoes.length ? `<ul>${revisoes.map((r) => `<li>${esc(r.item)} <span class="estado">(última vez ${esc(r.ultima)})</span></li>`).join("")}</ul>` : "<p>Nenhuma revisão vencida hoje.</p>"
  }</section>
<section class="cartao"><h2>Você domina</h2>${chips(m.domina)}<h2>Ainda precisa de dica</h2>${chips(m.emAndamento)}</section>
<section class="cartao"><h2>Erros que se repetem</h2>${
    erros.length ? `<ul>${erros.map((e) => `<li>${esc(e.descricao)} <span class="estado">(${e.vezes} vezes)</span></li>`).join("")}</ul>` : "<p>Nenhum erro repetido.</p>"
  }</section>
${c.metas.length || c.prazos.length ? `<section class="cartao"><h2>Metas</h2>${chips(c.metas)}${c.prazos.length ? `<ul>${c.prazos.map((p) => `<li>${esc(p.descricao)}: ${esc(p.data)}</li>`).join("")}</ul>` : ""}</section>` : ""}`;
  return pagina("Mentor · Progresso", nonce, corpo).replace(
    "</style>",
    `.p${pct}{width:${pct}%}</style>`,
  );
}
