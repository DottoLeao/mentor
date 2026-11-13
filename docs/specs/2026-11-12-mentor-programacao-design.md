# Mentor de Programação — documento de design

Data: 12/11/2026 · Autor: Lorenzo Dotto · Status: rascunho para aprovação

Nome provisório: **mentor.dev** (escolha do builder, pode mudar).

## 1. Intenção e o porquê

Um mentor de programação em português que vive dentro do VS Code. Ele ensina a pessoa a programar de verdade, em vez de programar por ela. O objetivo é que dev iniciante saia confiante de que é programador, sem buracos de conteúdo por ter pulado etapas.

Por que este projeto:

- **Uso próprio diário.** O Lorenzo já estuda todo dia com uma skill de mentor no Claude Code (`~/.claude/skills/mentor/SKILL.md`) e quer transformar esse método em produto. Ele é o primeiro usuário e testa tudo nele mesmo.
- **Portfólio para vagas de IA.** É o projeto de RAG público do portfólio dele (lorenzodotto.com.br). Precisa mostrar, em 30 segundos, o que recrutador brasileiro de vaga júnior/pleno de Python/IA valoriza: RAG com citação, avaliação automática, MCP, dados que se atualizam sozinhos e métricas de custo e latência.
- **Espaço vazio no mercado.** A pesquisa (`Vagas/reports/RAG em educação ideias.md`) não encontrou mentor em português que fique dentro do editor e guarde o progresso. A Luri, da Alura, só responde sobre o catálogo da Alura e não roda no editor. NotebookLM, ChatGPT Modo Estudo e Gemini Aprendizado Guiado não têm memória de trilha nem integração com o editor. Ressalva: Copilot e o modo de aprendizado do Claude não foram verificados.

## 2. Como funciona (visão do usuário)

1. **Entrevista de nivelamento.** Na primeira vez, o mentor pergunta o que a pessoa já sabe e aplica mini-testes por tópico (2 ou 3 perguntas ou um exercício curto). Só marca como sabido o que a pessoa demonstra.
2. **Trilha guiada pelo roadmap.sh.** A trilha segue a ordem dos roadmaps do roadmap.sh, e cada tópico tem um link "ver no roadmap.sh". O conteúdo do roadmap.sh não é copiado, por causa da licença (ver Restrições).
3. **Caminho linear.** A pessoa vê o progresso numa linha só, no estilo de app de idiomas: unidades concluídas, a atual com "você está aqui" e as futuras visíveis com cadeado. Cada passo é uma aula, um exercício, uma prova de unidade ou um certificado.
4. **Ensino em camadas, nunca a resposta.** Dicas do nível 1 (reformular) ao nível 4 (resposta, só se a pessoa pedir), igual à skill atual.
5. **O ofício inteiro, não só a sintaxe:**
   - **Linguagem e lógica:** exercícios com testes, revisão de código (o que está bom, um ponto a melhorar, Big O, versão idiomática, pergunta de fixação).
   - **VS Code bem usado:** depurador, terminal, Git pelo editor, atalhos, configurações. O mentor pode abrir a configuração certa e destacar a linha.
   - **Extensões recomendadas no momento certo**, com o motivo, por exemplo ESLint no primeiro erro de estilo ou o depurador quando a pessoa começa a encher o código de `console.log`.
   - **Processo profissional:** planejar antes de codar, commits, branches, pull requests, revisão de código, testes.
   - **Entrevista técnica e provas:** cronômetro, raciocínio em voz alta, feedback em 4 pontos.
6. **Sempre atualizado.** Antes de ensinar, o mentor consulta a fonte oficial (MDN, TypeScript, Node.js, notas de versão do VS Code), cita o trecho e mostra de quando é a informação.
7. **Memória.** O mentor lembra o que a pessoa domina, o que ainda precisa de dica e os erros que se repetem, e usa isso para escolher o próximo exercício e para dar dicas.

## 3. Objetivos, não-objetivos e anti-objetivos

**Objetivos da V1**
- O Lorenzo usa o mentor todo dia para a trilha de fundamentos em TypeScript que ele já faz.
- Uma página pública no portfólio com vídeo de 20 s, arquitetura, a parte que ele fez e resultados de avaliação reais.
- Código aberto no GitHub e instalação reproduzível.

**Não-objetivos da V1**
- Várias linguagens e conteúdo fora de código (fica para V2/V3).
- Cobrança, planos pagos, times e escolas.
- Login com conta para várias pessoas no painel web (V1 é single-user, local-first).
- Escrever código pela pessoa.

**Anti-objetivos (falha mesmo que funcione)**
- Entregar a resposta antes do nível 4. É o pior erro possível.
- Ensinar API desatualizada ou inventada sem citar fonte.
- Recomendar extensão maliciosa ou abandonada.
- Virar só mais um chat genérico, sem trilha, memória ou fonte.
- Copiar conteúdo do roadmap.sh sem permissão.

## 4. Decisões já tomadas

| Decisão | Valor | Quem decidiu |
|---|---|---|
| Idioma do produto | Português do Brasil | Lorenzo |
| Onde roda | Dentro do VS Code | Lorenzo |
| Trilhas | Guiadas pelo roadmap.sh, com links | Lorenzo |
| Nivelamento | Entrevista inicial com mini-testes | Lorenzo, a partir de sugestão |
| Progresso | Caminho linear com passos futuros visíveis | Lorenzo |
| Escopo de ensino | Código, VS Code, extensões, processo profissional | Lorenzo |
| Primeira trilha da V1 | Fundamentos em TypeScript (a trilha atual da skill) | Proposta minha, aceita pelo Lorenzo |
| Gerenciamento | Plane, workspace "Projetos", milestones e etiquetas "humano no loop" / "execução direta" | Lorenzo |
| Agente suportado na V1 | Claude Code (Copilot fica para a V2) | Lorenzo |
| Orçamento dos evals | Até US$ 20/mês, permitindo um modelo melhor como juiz | Lorenzo |
| Servidor de conhecimento | Aberto para qualquer pessoa que instalar, com limite de uso por usuário | Lorenzo |
| Telas de referência | Canvas https://claude.ai/artifact/LGdQfehBwiW9hVnUPU2P8g (telas 1, 2, 3, 4, 6 = produto; 5 = página do portfólio) | Lorenzo revisou |

## 5. Arquitetura proposta (escolhas minhas, marcadas para revisão)

Duas peças com dois servidores MCP, separados por onde cada dado mora:

1. **Servidor MCP remoto em Python** (SDK oficial de MCP, transporte HTTP), hospedado. É o "cérebro de conhecimento", sem nenhum dado pessoal. Ferramentas:
   - `buscar_docs(pergunta, fonte?, data?)`: RAG sobre documentação oficial, com citação (URL, trecho, data de coleta).
   - `recomendar_extensao(contexto)`: só de publicador verificado, com instalações e atualização recente.
   - Prompts MCP com o "jeito de ensinar": dicas em camadas, revisão, entrevista, prova.

   *Por quê Python:* é o que as vagas pedem, e o Lorenzo quer aprender. Aqui ficam o RAG, os evals e a reindexação, que são a parte de IA/MLOps do portfólio.
2. **Extensão do VS Code em TypeScript**, que também registra um **servidor MCP local**. Cuida de tudo que é pessoal ou de interface:
   - Progresso: `nivelamento()`, `proximo_passo()`, `registrar_resultado(passo, status)`, lendo e escrevendo o arquivo de memória no workspace.
   - Ações de interface: abrir configuração, destacar linha, rodar teste, sugerir instalar extensão.
   - Telas: caminho linear e painel de progresso (webview).

   *Por quê assim:* um servidor remoto não lê arquivo local nem controla o editor. A memória fica local (privacidade), e o conhecimento fica no servidor compartilhado. Esta divisão é escolha minha, a partir da revisão do builder.
3. **Índice e dados:** Postgres com pgvector (Neon free) e busca híbrida (vetorial + full-text). A coleta e a reindexação das fontes rodam por agendamento no GitHub Actions (semanal; notas do VS Code, mensal). Cada trecho guarda fonte, URL, versão e data.

**Trilha e exercícios da V1 (escolha minha, a partir da conversa):**
- **Ordem:** a da trilha de 8 semanas da skill atual (base, arrays e strings, funções e objetos, Map/Set, ordenação, recursão, pilhas e filas, Big O). A ordem do roadmap.sh só passa a valer nas trilhas novas da V2, e na V1 o roadmap.sh entra como link em cada tópico.
- **Exercícios:** arquivos locais no formato da skill (enunciado, assinatura tipada e testes no próprio arquivo), com a referência ao problema do HackerRank quando existir.
- **Passo "certificado":** o certificado oficial do HackerRank daquela faixa. O mentor só diz quando a pessoa está pronta para ele.

**Migração da skill (escolha minha):** na V1 o mentor substitui a skill do Lorenzo. Um comando importa o `Estudos/diario.md` atual para o novo formato, e quem já tem histórico pula o nivelamento. O contexto pessoal (metas, prazo da Amazon, perfil de vagas) sai do código e vai para um arquivo de configuração do usuário.

**De onde vem o LLM (minha escolha):** na V1, a conversa acontece no Claude Code dentro do VS Code, que chama os dois servidores MCP. Assim o custo de LLM do projeto fica quase zero, e o "jeito de ensinar" vai nas instruções expostas pelo servidor (prompts MCP). O servidor só usa LLM próprio para embeddings e para os evals. O painel de chat da tela 1 do canvas fica para depois, se o modelo "use sua própria IA" não for suficiente.

**Memória (minha escolha):** local-first. O diário fica num arquivo dentro do workspace da pessoa (como o `diario.md` de hoje, em formato estruturado), e o servidor recebe só o necessário em cada chamada. Isso evita guardar dados de terceiros na V1.

## 6. Avaliação e métricas (o que mostra no portfólio)

- Conjunto de **50 conversas escritas à mão**, segmentadas por tipo:
  - pedido de resposta direta;
  - dúvida de API recente;
  - erro de teste;
  - pergunta de VS Code;
  - pedido de extensão;
  - fora de escopo.
- **Métricas:**
  - não entregou a resposta antes do nível 4 (%);
  - citação correta (a página citada contém a informação);
  - uso da memória (a dica usa um erro registrado);
  - recall@k e MRR da busca, separados da qualidade da resposta;
  - custo e latência por chamada.
- **Como os evals simulam o agente:** no CI, um modelo via API faz o papel do Claude Code, com os mesmos prompts e ferramentas MCP, e um segundo modelo, melhor, atua como juiz. Orçamento de até US$ 20/mês, com um limite de gasto configurado no provedor. Os números públicos dizem qual modelo foi usado na simulação.
- Os evals rodam no CI a cada mudança e a cada reindexação. Os resultados vão para a página pública, com "falhas conhecidas" listadas.
- Tracing com Langfuse (free tier).

## 7. Restrições

- **Custo:** deploy grátis ou quase. Hospedagem sugerida pela pesquisa anterior: Cloud Run ou similar para o servidor, Neon, Langfuse Hobby, Vercel para a página. O builder confere os limites atuais.
- **roadmap.sh:** sem API para progresso. A licença do conteúdo é restritiva (permite links, proíbe republicar sem autorização). Por isso: só links e nomes de tópicos próprios até haver permissão por escrito.
- **Licenças das fontes:**
  - MDN: CC-BY-SA, exige atribuição.
  - Docs do TypeScript, do Node e do VS Code: o builder confere.
- **Segurança de extensões:** filtro por publicador verificado, número de instalações e data de atualização.
- **Público adulto (18+) nos termos**, para ficar fora do ECA Digital na V1.
- **Servidor aberto com limite de uso:** identificação anônima por instalação (sem login na V1), limite diário de consultas por instalação e proteção contra abuso. O custo por consulta é só o embedding da pergunta, mais o banco. O servidor não recebe nem guarda dados pessoais nem código do usuário, só a pergunta.
- **Sem marca de autoria de IA** em commits, PRs, docs e na página (regra do Lorenzo).

## 8. Milestones

- **M0, Fundação:** repositório, servidor MCP mínimo, índice com MDN, TypeScript e Node, extensão "hello", Plane organizado.
- **M1, Mentor usável pelo Lorenzo:** nivelamento, trilha TS (8 unidades da skill atual), dicas em camadas, revisão, memória local, caminho linear na extensão.
- **M2, Ofício:** ações de VS Code, recomendação de extensões, processo profissional (Git, PR, revisão), modo entrevista e provas.
- **M3, Qualidade e portfólio:** 50 evals no CI, Langfuse, reindexação agendada, página no portfólio com vídeo e resultados, README.
- **V2 (depois):** trilha de Python, mais roadmaps, painel web com login, permissão do roadmap.sh.
- **V3 (depois):** modo pago e outras áreas além de código.

## 9. Humano no loop (só o Lorenzo pode fazer)

- Pedir ao autor do roadmap.sh permissão para usar a estrutura de tópicos.
- Criar contas e chaves: Neon, Langfuse, Google Cloud ou outro host, VS Code Marketplace (publicador), domínio.
- Escrever ou aprovar as 50 conversas de avaliação, pelo menos revisar as geradas.
- Usar o mentor de verdade por duas semanas e registrar o que falhou.
- Gravar o vídeo de 20 s e aprovar o texto da página do portfólio.
- Publicar a extensão no Marketplace e o post no LinkedIn.

## 10. Deixado para o builder

- Estrutura de pastas e testes.
- Formato do arquivo de memória.
- Estratégia de chunking.
- Escolha do modelo de embeddings (bge-m3 ou qwen3-embedding foram sugeridos).
- Nome final do produto.
- Detalhes visuais da extensão, seguindo o canvas.
