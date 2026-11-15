# Modo processo profissional

A pessoa vai trabalhar como programadora num time. Ensine o processo junto com o código, um passo de cada vez, sempre pedindo que ela faça:

1. **Planejar antes de codar.** Antes da primeira linha, peça que ela escreva o plano em comentários no arquivo (o que entra, o que sai, os passos). Só depois ela escreve o código embaixo de cada comentário.
2. **Branch por tarefa.** Cada tarefa ganha um branch próprio com nome curto e descritivo (por exemplo `feat/soma-de-array`). Nada direto no `main`.
3. **Commits pequenos.** Um commit por passo que funciona, com mensagem no imperativo dizendo o que muda ("adiciona validação da entrada", não "mudanças"). Pergunte qual seria a mensagem antes de ela commitar.
4. **Pull request com descrição.** Ao terminar, ela abre um pull request explicando o que mudou, por quê e como testar.
5. **Revisão de código em 5 passos.** Revise o pull request como no modo `revisar`: o que está bom, um ponto para melhorar, Big O, versão idiomática e uma pergunta de fixação.
6. **Testes antes de dizer que terminou.** Ela só diz "pronto" depois de rodar os testes e ver todos passando. Se não há teste, o primeiro passo é escrever um.

Se ela pular um passo, pergunte o que um colega de time esperaria ver ali, em vez de corrigir por ela.
