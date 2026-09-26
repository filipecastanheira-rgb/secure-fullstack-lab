# Secure Fullstack Lab

Aplicação full-stack construída como laboratório prático de desenvolvimento, deployment e segurança (DevSecOps).

## Objetivo

Construir uma aplicação web completa — frontend, backend, base de dados — e endurecê-la ao longo do caminho com práticas reais de segurança, automação e observabilidade, **sem recorrer a cloud paga**.

## Stack

| Camada       | Tecnologia         | Estado        |
|--------------|--------------------|---------------|
| Frontend     | Vue 3 + Vite       | ✅ funcional  |
| Backend      | FastAPI (Python)   | ✅ funcional  |
| Base de dados| SQLite → PostgreSQL| ⏳ próximo    |
| Reverse proxy| Nginx              | ⏳ planeado   |
| HTTPS        | Let's Encrypt      | ⏳ planeado   |
| CI/CD        | GitHub Actions     | ⏳ planeado   |
| Segurança    | Bandit, SCA, ZAP   | ⏳ planeado   |

## Arquitetura (estado atual)

    Kali (cliente)          Ubuntu (servidor)
    ─────────────           ─────────────────
    Browser  ─── HTTP ──▶   Vue (Vite)  :5173
                              │
                              │ fetch /api/*
                              ▼
                            FastAPI     :8000

## Ambiente

- **Ubuntu (VMware)** — `192.168.1.173` — hospeda backend, frontend e, futuramente, BD e Nginx.
- **Kali (VMware)** — `192.168.1.125` — cliente, browser, testes de segurança.

## Como arrancar (desenvolvimento)

### Backend

    cd backend
    source .venv/bin/activate
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

### Frontend

    cd frontend
    npm run dev -- --host 0.0.0.0

Depois abrir em qualquer máquina da LAN:

    http://192.168.1.173:5173

## Documentação

- [`docs/JOURNAL.md`](docs/JOURNAL.md) — diário de desenvolvimento (decisões, problemas, soluções).

## Roadmap

- [x] Frontend Vue funcional
- [x] Backend FastAPI funcional
- [x] Vue ↔ FastAPI (HTTP + JSON)
- [ ] Dados persistentes (SQLite → PostgreSQL)
- [ ] Deployment no Ubuntu (systemd/supervisor)
- [ ] Nginx como reverse proxy
- [ ] HTTPS
- [ ] Hardening SSH / UFW / Fail2Ban
- [ ] CI/CD com GitHub Actions
- [ ] SAST (Bandit)
- [ ] SCA (dependências)
- [ ] DAST (OWASP ZAP)
- [ ] Logging e monitoring
- [ ] Backups
- [ ] Documentação final e security review

## Licença

Projeto pessoal de aprendizagem.
