# PRD — Sistema Completo de Emissão de NF-e

## Problem Statement
"sistema completo de emissao de nota fiscal" — Complete Brazilian electronic invoice (NF-e, modelo 55) emission system.

## User Choices
- Tipo: NF-e (produtos)
- Integração fiscal: Real (SEFAZ) — requires ICP-Brasil A1 certificate (.pfx). Signing implemented; live SEFAZ transmission needs a real certificate.
- Auth: Email/senha (JWT)
- Recursos: cadastro de clientes e produtos, emissão + listagem com PDF, dashboard com totais/relatórios, cálculo de impostos.

## Architecture
- Backend: FastAPI + MongoDB (motor). Files: server.py (routes), models.py (Pydantic + BaseDocument), auth.py (JWT/bcrypt), nfe_utils.py (chave de acesso mod11, cálculo de impostos, XML NF-e 4.00 via lxml, assinatura digital via signxml/cryptography, DANFE PDF via reportlab).
- Frontend: React + Tailwind + shadcn/ui + Phosphor icons + Recharts. JWT Bearer token in localStorage ('nfe_token').

## User Personas
- Contador / dono de empresa que emite notas fiscais de produtos.

## Core Requirements (static)
- Auth email/senha; cadastro de emitente + certificado A1; CRUD de clientes e produtos; emissão de NF-e com cálculo automático de ICMS/IPI/PIS/COFINS; geração de XML 4.00 assinado e DANFE PDF; dashboard.

## Implemented (2026-06)
- JWT auth (register/login/logout/me), admin seed (mateus.ferreira@camainbox.com.br).
- Configurações: dados do emitente, SEFAZ (UF/ambiente/série/número/CSC), upload e validação de certificado A1.
- Clientes CRUD, Produtos CRUD (com tributação).
- Emissão NF-e: wizard 3 passos, cálculo de impostos, geração de chave de acesso (44 díg. + DV mod11), XML NF-e 4.00, assinatura digital (quando certificado instalado), DANFE PDF, cancelamento, download XML/PDF.
- Dashboard: totais, receita, impostos, gráficos (faturamento mensal, notas por status), notas recentes.
- 100% pass em testes backend (14) e E2E frontend.

## Known Limitations
- Transmissão real ao SEFAZ requer certificado A1 ICP-Brasil válido; sem ele, a emissão gera XML e marca a nota como "pendente".
- cert_password armazenada em texto (endurecer para produção).

## Backlog (P1/P2)
- P1: Transmissão SOAP real ao webservice NFeAutorizacao4 por UF; consulta de protocolo/autorização.
- P1: Geração de QR Code e protocolo na DANFE após autorização.
- P2: Paginação nas listagens; relatórios exportáveis; carta de correção (CC-e).
