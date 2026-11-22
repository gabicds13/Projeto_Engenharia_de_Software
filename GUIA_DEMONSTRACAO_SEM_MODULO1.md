# Capturas de tela do Módulo 6 sem depender do Módulo 1

Esta branch é **exclusivamente para demonstração visual**. Não contém login real nem chama o BFF, o banco Neon, o Módulo 1 ou o Gemini.

## Como abrir

1. Baixe ou clone a branch `demo/capturas-sem-modulo1`.
2. Abra o terminal na pasta `frontend`.
3. Execute:
   ```bash
   npm ci
   npm run dev:demo
   ```
4. Abra **http://localhost:5173**.
5. Clique em **Entrar no modo demonstração**.
6. Navegue entre **Dashboard**, **Notificações**, **Chat geral** e **Conversas privadas** e tire os prints.

Opcional: `npm run build:demo` gera a versão estática de demonstração em `frontend/dist`.

**Atenção:** esses prints mostram o funcionamento **visual** das telas com **dados fictícios**. Não comprovam integração com as APIs reais nem execução dos testes de ponta a ponta. Registre no relatório como **demonstração local com dados simulados**.

A branch `main` e os serviços reais não são modificados. Os números, projetos, notificações e mensagens são exemplos locais; alterações não são persistidas após recarregar a página. Um aviso "MODO DEMONSTRAÇÃO" aparece em todas as telas.

## Se você usa o VS Code

Abra um terminal integrado (Terminal > Novo Terminal), execute os comandos acima e depois abra o endereço indicado pelo Vite. Se o endereço estiver ocupado, use o que o terminal informar.

## Verificações

No GitHub Actions desta branch há um workflow separado que executa os testes do frontend e compila a versão de demonstração, **sem publicar no Azure**.
