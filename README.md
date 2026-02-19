# 🚌 CrownyBus RNS Server

**CrownyOS Route Name System - Central Routing Hub**

## Routes

| Path | Service | CTP Address |
|------|---------|-------------|
| `/exchange` | Crowny Exchange Platform | `ctp://exchange.crowny` |
| `/rns` | RNS Management API | - |
| `/` | CrownyBus Landing | - |

## API

- `GET /health` - Health check
- `GET /rns/status` - RNS status
- `GET /rns/routes` - Route table
- `GET /rns/resolve/:address` - CTP → HTTP resolve

## Deploy

Railway auto-deploys from this repo.

## Environment

- `PORT` - Server port (default: 8080)
- `EXCHANGE_URL` - Exchange Platform URL (default: Railway URL)
