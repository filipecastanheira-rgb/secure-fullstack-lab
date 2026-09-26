# Secure Fullstack Lab — Diário de Desenvolvimento

Registo cronológico das decisões, comandos e problemas encontrados ao longo do projeto.
Serve para: (1) documentar para o portefólio, (2) recuperar contexto, (3) aprender com os erros.

---

## Arquitetura atual

    Frontend (Vue + Vite)   →   Backend (FastAPI)   →   [em breve: SQLite]
    http://192.168.1.173:5173     http://192.168.1.173:8000

Máquinas:
- Ubuntu (VMware) — 192.168.1.173 — hospeda o projeto
- Kali (VMware) — 192.168.1.125 — cliente / browser / testes

---

## Sessão 1 — Arranque do frontend e backend

**Objetivo:** ter Vue e FastAPI a correr, acessíveis a partir do Kali.

- Backend FastAPI a responder em `/` com `{"message": "Secure Fullstack Lab API is running"}`.
- Frontend Vue a correr com `npm run dev -- --host 0.0.0.0`.
- `App.vue` inicial mostrava apenas "You did it!" (template do Vite).

**Problema 1:** Firefox no Kali não conseguia abrir `http://192.168.1.173:5173`.
**Diagnóstico (por camadas):**
1. `ss -ltnp | grep 5173` no Ubuntu → Vite a escutar em `0.0.0.0:5173` (OK).
2. `curl` no Ubuntu → `HTTP/1.1 200 OK` (OK).
3. `ping` do Kali → responde (rede OK).
4. `curl` do Kali → `HTTP/1.1 200 OK` (rede + firewall + Vite OK).
**Conclusão:** o problema era do lado do browser (cache/refresh). Resolvido com `Ctrl+Shift+R`.

**Lição:** diagnosticar sempre camada a camada — rede → firewall → serviço → browser.

---

## Sessão 2 — Ligar Vue ao FastAPI

**Objetivo:** o Vue faz `fetch` ao FastAPI e mostra a resposta no ecrã.

**Backend (`backend/main.py`):**
- Adicionado `CORSMiddleware` com as origens permitidas:
  - `http://localhost:5173`
  - `http://192.168.1.173:5173`
- Novo endpoint: `GET /api/hello` → `{"message": "Olá do FastAPI 👋"}`.

**Frontend (`frontend/src/App.vue`):**
- `ref` para o estado reativo (`message`).
- `onMounted` para disparar o `fetch` quando o componente monta.
- `await fetch('http://192.168.1.173:8000/api/hello')` + `await res.json()`.
- `{{ message }}` no template para mostrar a resposta.

**Problema 2:** erro `NetworkError when attempting to fetch resource` no browser.
**Causa:** o FastAPI tinha parado entretanto (morreu com o terminal).
**Diagnóstico:** `curl -H "Origin: http://192.168.1.173:5173" -i ...` mostrava `access-control-allow-origin` quando o servidor estava vivo → CORS estava bem.
**Solução:** arrancar FastAPI e Vite com `nohup ... &` para sobreviverem ao fecho do terminal.

**Resultado:** Firefox no Kali mostra `Olá do FastAPI 👋` — Vue ↔ FastAPI a funcionar. ✅

---

## Comandos úteis usados

Arrancar FastAPI em background:

    cd ~/secure-fullstack-lab/backend
    source .venv/bin/activate
    nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ~/fastapi.log 2>&1 &

Arrancar Vite em background:

    cd ~/secure-fullstack-lab/frontend
    nohup npm run dev -- --host 0.0.0.0 > ~/vite.log 2>&1 &

Ver logs:

    tail -f ~/fastapi.log
    tail -f ~/vite.log

Ver quem ocupa uma porta:

    sudo ss -ltnp | grep <porta>

Matar processo:

    kill <PID>

---

## Decisões de arquitetura

- **CORS explícito** (sem `"*"`), porque vamos usar credenciais mais tarde.
- **Prefixos `/api`** nos endpoints, para separar API de páginas.
- **SQLite primeiro, PostgreSQL depois** — o código será escrito com SQLAlchemy para que a migração seja só trocar a connection string.
- **`nohup` em desenvolvimento** — solução provisória; em produção usaremos systemd/supervisor.

---

## Próximo passo

- Persistência de dados com SQLite + SQLAlchemy.
