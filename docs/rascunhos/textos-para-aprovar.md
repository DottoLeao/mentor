# Textos para aprovar (MENTOR-36)

Status: rascunho. Nada aqui foi publicado. Cada item precisa da aprovação do Lorenzo antes do merge ou da publicação.

## 1. README da raiz do repositório

- Arquivo: `README.md` (branch `docs/readme-raiz`, PR contra `feat/servidor-conhecimento`).
- Conferir: o parágrafo de abertura, a tabela "Qualidade medida", a seção "Falhas conhecidas" e a lista de "Depende de contas".
- O link para `extension/README.md` só funciona depois do merge do PR #2.

## 2. Página do projeto no portfólio (pt e en)

- Repositório `DottoLeao/portifolio`, branch `feat/projeto-mentor`, rota `/pt/projects/mentor` e `/en/projects/mentor`.
- Textos em `content/mentor.ts` (abertura, 4 passos, tabela, "o que eu construí", falhas) e em `messages/pt.json` / `messages/en.json` (chave `mentor`).
- Card novo na home (`content/projects.ts`, projeto `mentor`).
- O merge publica em lorenzodotto.com.br. Não fazer merge antes de aprovar o texto.
- Pendente: gravar o vídeo de 20 s e trocar o espaço reservado.

## 3. Pedido ao roadmap.sh

- Arquivo: `docs/rascunhos/pedido-roadmap-sh.md`. Enviar só depois de aprovar.

## 4. Post do LinkedIn

- Arquivo: `docs/rascunhos/post-linkedin.md`. Publicar depois do merge dos PRs e, se possível, com o vídeo.

## 5. Termos de uso (rascunho curto)

> **Termos de uso do Mentor**
>
> 1. O Mentor é um projeto de código aberto, gratuito e oferecido "como está", sem garantia (licença MIT).
> 2. O uso é permitido só para maiores de 18 anos. Ao instalar a extensão ou usar o servidor de conhecimento, você declara ter 18 anos ou mais.
> 3. O Mentor é uma ferramenta de estudo. As respostas podem conter erros; confira sempre a documentação oficial citada.
> 4. Os exercícios rodam código JavaScript na sua máquina. Você é responsável pelo que executa e pelas permissões que concede ao seu agente (por exemplo, o Claude Code).
> 5. O servidor de conhecimento tem limite diário de buscas por instalação e pode ser suspenso ou alterado sem aviso. Abuso (automação em massa, tentativa de contornar o limite) leva ao bloqueio da instalação.
> 6. Os trechos de documentação mostrados continuam sob a licença de cada fonte (MDN: CC-BY-SA 2.5; TypeScript: CC BY 4.0; Node.js: MIT; VS Code: CC BY 3.0 US).
> 7. O uso do Claude Code e de outros serviços de terceiros segue os termos desses serviços.

## 6. Aviso de privacidade (rascunho curto)

> **Privacidade no Mentor**
>
> - **Seu progresso fica com você.** O que você domina, as dicas, os erros e as revisões ficam em `.mentor/progresso.json`, dentro da sua pasta de estudos. O Mentor não envia esse arquivo para nenhum servidor.
> - **O servidor de conhecimento recebe só a pergunta.** Junto vai um identificador aleatório da instalação, usado apenas para o limite diário de buscas. Não pedimos nome, e-mail nem conta, e o servidor não recebe o seu código.
> - **O que fica guardado no servidor:** a contagem de buscas por identificador de instalação, por dia, e registros técnicos de funcionamento (horário, tempo de resposta, erros). O texto da pergunta não é gravado no tracing.
> - **Servidor local.** A extensão abre um servidor só em `127.0.0.1`, protegido por um token salvo no `.mcp.json` da pasta. Não publique esse arquivo.
> - **Terceiros.** A conversa acontece no Claude Code; o que você escreve nele segue a política de privacidade do provedor do agente.
> - **Apagar seus dados:** apague a pasta `.mentor/`. No servidor, os contadores de uso antigos são descartados automaticamente.
> - **Contato:** pelas issues do repositório no GitHub.

Pontos a confirmar antes de publicar os dois textos:

- Por quanto tempo o servidor guarda o contador de uso (o PR #1 limpa o uso antigo; confirmar o prazo e citá-lo).
- Se os registros do servidor hospedado (quando existir) guardam IP. Se guardarem, dizer por quanto tempo.
- Se vale ter um e-mail de contato para privacidade em vez de só as issues.
