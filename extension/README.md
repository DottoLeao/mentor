# Mentor de Programação (extensão do VS Code)

Um mentor de programação em português que vive dentro do VS Code. Ele ensina você a programar de verdade, em vez de programar por você: dá dicas em camadas, guarda o seu progresso e mostra o caminho da trilha.

A conversa acontece no Claude Code, que você já usa. A extensão dá a ele três coisas:

1. **Memória do seu progresso.** O que você domina, o que ainda precisa de dica, os erros que se repetem e as revisões do dia (revisão espaçada).
2. **A trilha.** Oito unidades de fundamentos em TypeScript, com exercícios no formato do HackerRank e link para o roadmap.sh em cada unidade.
3. **Ações no editor.** Abrir o exercício, destacar a linha onde olhar, rodar os testes no terminal e sugerir extensões, sempre com a sua confirmação.

## Instalar

1. Instale o arquivo `.vsix`: Extensões → `...` → "Instalar do VSIX".
2. Abra a sua pasta de estudos no VS Code.
3. Rode o comando **Mentor: conectar ao Claude Code**. Ele cria ou atualiza o `.mcp.json` da pasta.
4. Abra o Claude Code e diga: "Mentor, qual o próximo passo?".

Já estudava com um diário em Markdown? Rode **Mentor: importar diário de estudos** para trazer o histórico e as revisões.

## Comandos

| Comando | O que faz |
|---|---|
| Mentor: abrir o caminho | Mostra a trilha numa linha: o que você já fez, onde está e o que vem depois |
| Mentor: abrir o painel de progresso | Revisões de hoje, o que você domina, erros que se repetem e metas |
| Mentor: conectar ao Claude Code | Aponta o Claude Code desta pasta para o Mentor |
| Mentor: importar diário de estudos | Converte um diário em Markdown para o progresso do Mentor |

## Privacidade

- O progresso fica em `.mentor/progresso.json`, dentro da sua pasta. Metas pessoais opcionais ficam em `.mentor/config.json`.
- O servidor local escuta só em `127.0.0.1` e exige um token, que fica no `.mcp.json`. Não publique esse arquivo.
- O servidor de conhecimento (busca na documentação oficial) recebe só a pergunta. Nunca recebe o seu código nem o seu progresso.

## Configurações

- `mentor.portaLocal` (padrão `39217`): porta do servidor local.
- `mentor.urlConhecimento`: endereço do servidor de conhecimento.

## Desenvolvimento

```bash
npm install
npm test
npm run build
npx @vscode/vsce package --no-dependencies
```
