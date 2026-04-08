# CLAUDE.md

Este arquivo fornece orientações ao Claude Code (claude.ai/code) para trabalhar com o código neste repositório.

## Visão geral

ScoreLattes é uma API REST em Flask que calcula pontuações de produtividade acadêmica a partir de currículos Lattes do CNPq. A aplicação busca os currículos via serviço SOAP do CNPq, faz o parse do XML e retorna pontuações ponderadas com base em publicações, projetos, orientações e outras atividades acadêmicas.

## Executando a aplicação

A aplicação roda dentro do Docker:

```bash
docker-compose up -d          # Inicia todos os serviços
docker-compose logs -f lattes # Acompanha os logs
docker-compose down           # Para os serviços
```

Para desenvolvimento local sem Docker (requer Redis rodando separadamente):
```bash
cd app
python3 lattes.py
```

## Arquitetura

Todo o código da aplicação fica em `app/`:

- **`lattes.py`** — Ponto de entrada Flask. Expõe `GET /score/<cpf>/<area_capes>/<periodo>/<tipo>`. Realiza chamadas SOAP ao CNPq via `zeep`, baixa e extrai o ZIP do currículo e delega o cálculo ao `scorerun.py`. Limitação de requisições com Flask-Limiter usando Redis como backend.
- **`scorerun.py`** — Motor de pontuação. A classe `Score` faz o parse do XML Lattes (via `xml.etree.ElementTree`), consulta os estratos Qualis dos periódicos no SQLite e computa as pontuações ponderadas. Contém dois dicts globais principais: `weights` (pontos por item) e `bounds` (tetos por categoria).
- **`cnpq`** — Arquivo WSDL para o serviço SOAP do CNPq (`getCurriculoCompactado`, `getIdentificadorCNPq`).
- **`qualis.sqlite3`** / **`qualis2017.sqlite3`** — Bancos SQLite que mapeiam ISSN/título de periódico para estrato Qualis nos períodos 2021–2024 e 2017, respectivamente.

## Endpoint da API

```
GET /score/<cpf_ou_id>/<area_capes>/<periodo>/<tipo>
```

- `cpf_ou_id`: CPF com 11 dígitos (resolvido para ID Lattes via SOAP) ou ID Lattes de 16 dígitos diretamente
- `area_capes`: string da área de conhecimento CAPES (usada para consultar os estratos Qualis)
- `periodo`: `5` ou `7` (anos retroativos a partir da data atual)
- `tipo`: `0` retorna `{"score": "<float>"}`, `1` retorna um resumo HTML completo

## Infraestrutura

O `docker-compose.yml` define:
- **lattes** — Container Python 3 executando `lattes.py` via waitress na porta 8888→80, atrás do Traefik com TLS
- **redis** — Redis 8, usado exclusivamente para armazenamento do rate limiting do Flask-Limiter
- **autoheal** — Reinicia automaticamente containers com falha no healthcheck

Limites de requisições: 600/dia, 150/hora globalmente; 30/dia, 10/hora, 3/minuto no endpoint de pontuação.

## Sistema de pontuação

`scorerun.py:weights` e `scorerun.py:bounds` são as duas estruturas de dados que controlam a rubrica de pontuação. Cada categoria de produção acadêmica tem um valor em pontos no `weights` e um teto de acumulação em `bounds` (`'inf'` significa sem limite). O `Score.__init__` também recebe `ano_qualis_periodicos` (atualmente fixado em `2017` em `lattes.py`) para selecionar qual banco Qualis utilizar.
