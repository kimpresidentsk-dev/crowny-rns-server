/**
 * CrownyOS Route Name System (RNS) Server v1.0
 * 
 * 중앙 라우팅 허브 - crownybus.com의 모든 요청을 적절한 서비스로 프록시
 * 
 * Routes:
 *   /exchange/*  → Crowny Exchange Platform (Railway)
 *   /rns/*       → RNS Management API
 *   /            → CrownyBus Landing Page
 */

const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('path');
const http = require('http');

const app = express();
const PORT = process.env.PORT || 8080;

// ═══════════════════════════════════════════════════
// Route Registry - CrownyOS 서비스 라우팅 테이블
// ═══════════════════════════════════════════════════
const ROUTE_TABLE = {
  exchange: {
    name: 'Crowny Exchange Platform',
    target: process.env.EXCHANGE_URL || 'https://crowny-exchange-production.up.railway.app',
    path: '/exchange',
    status: 'active',
    version: '2.0.0',
    protocol: 'ctp://exchange.crowny',
    description: 'DEX, AI Trading, Upbit/Binance API'
  }
  // 향후 추가 서비스:
  // wallet: { target: '...', path: '/wallet' },
  // browser: { target: '...', path: '/browser' },
  // kernel: { target: '...', path: '/kernel' },
};

// ═══════════════════════════════════════════════════
// Middleware
// ═══════════════════════════════════════════════════
app.use((req, res, next) => {
  // CORS
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-CTP-Protocol, X-Crowny-Service');
  
  // CrownyOS RNS 헤더
  res.header('X-Powered-By', 'CrownyOS-RNS/1.0');
  res.header('X-RNS-Node', 'crownybus.com');
  
  if (req.method === 'OPTIONS') return res.sendStatus(200);
  next();
});

// Request logging
app.use((req, res, next) => {
  const timestamp = new Date().toISOString();
  console.log(`[RNS ${timestamp}] ${req.method} ${req.url} → routing...`);
  next();
});

// ═══════════════════════════════════════════════════
// Exchange Platform Proxy
// /exchange/* → Railway Exchange Platform
// ═══════════════════════════════════════════════════
const exchangeProxy = createProxyMiddleware({
  target: ROUTE_TABLE.exchange.target,
  changeOrigin: true,
  ws: true,
  pathRewrite: {
    '^/exchange': ''  // /exchange/api/market → /api/market
  },
  on: {
    proxyReq: (proxyReq, req, res) => {
      proxyReq.setHeader('X-Forwarded-By', 'CrownyOS-RNS');
      proxyReq.setHeader('X-RNS-Route', 'exchange');
      proxyReq.setHeader('X-Original-URL', req.originalUrl);
    },
    proxyRes: (proxyRes, req, res) => {
      proxyRes.headers['x-rns-routed'] = 'true';
      proxyRes.headers['x-rns-service'] = 'exchange';
    },
    error: (err, req, res) => {
      console.error(`[RNS ERROR] Exchange proxy failed: ${err.message}`);
      if (res.writeHead) {
        res.writeHead(502, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          error: 'RNS_PROXY_ERROR',
          message: 'Exchange Platform 연결 실패',
          service: 'exchange',
          target: ROUTE_TABLE.exchange.target,
          timestamp: new Date().toISOString()
        }));
      }
    }
  }
});

app.use('/exchange', exchangeProxy);

// ═══════════════════════════════════════════════════
// RNS Management API
// ═══════════════════════════════════════════════════

// RNS 상태
app.get('/rns/status', (req, res) => {
  res.json({
    system: 'CrownyOS Route Name System',
    version: '1.0.0',
    node: 'crownybus.com',
    uptime: process.uptime(),
    routes: Object.keys(ROUTE_TABLE).length,
    timestamp: new Date().toISOString()
  });
});

// 라우팅 테이블 조회
app.get('/rns/routes', (req, res) => {
  const routes = Object.entries(ROUTE_TABLE).map(([key, route]) => ({
    id: key,
    name: route.name,
    path: route.path,
    url: `https://crownybus.com${route.path}`,
    ctp: route.protocol,
    status: route.status,
    version: route.version,
    description: route.description
  }));
  res.json({ routes, total: routes.length });
});

// 특정 서비스 조회
app.get('/rns/routes/:service', (req, res) => {
  const route = ROUTE_TABLE[req.params.service];
  if (!route) {
    return res.status(404).json({ error: 'SERVICE_NOT_FOUND', service: req.params.service });
  }
  res.json({
    id: req.params.service,
    ...route,
    url: `https://crownybus.com${route.path}`,
    health: `https://crownybus.com${route.path}/api/health`
  });
});

// RNS Resolve - CTP 프로토콜 주소 → HTTP URL 변환
app.get('/rns/resolve/:address', (req, res) => {
  const address = req.params.address; // e.g., "exchange.crowny"
  const parts = address.split('.');
  const serviceName = parts[0];
  
  const route = ROUTE_TABLE[serviceName];
  if (!route) {
    return res.status(404).json({
      error: 'RNS_RESOLVE_FAILED',
      address: `ctp://${address}`,
      message: `서비스 "${serviceName}" 를 찾을 수 없습니다`
    });
  }
  
  res.json({
    ctp: `ctp://${address}`,
    http: `https://crownybus.com${route.path}`,
    direct: route.target,
    service: route.name,
    status: route.status
  });
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'rns', timestamp: new Date().toISOString() });
});

// ═══════════════════════════════════════════════════
// Landing Page - crownybus.com 메인
// ═══════════════════════════════════════════════════
app.get('/', (req, res) => {
  res.send(getLandingPage());
});

// 404 - Unknown routes
app.use((req, res) => {
  // CTP 프로토콜 요청 감지
  const ctpHeader = req.headers['x-ctp-protocol'];
  if (ctpHeader) {
    return res.status(404).json({
      error: 'CTP_ROUTE_NOT_FOUND',
      message: `CTP 경로를 찾을 수 없습니다: ${req.url}`,
      available: Object.keys(ROUTE_TABLE).map(k => ROUTE_TABLE[k].protocol)
    });
  }
  
  res.status(404).send(get404Page(req.url));
});

// ═══════════════════════════════════════════════════
// Server Start
// ═══════════════════════════════════════════════════
const server = http.createServer(app);

// WebSocket 프록시 지원
server.on('upgrade', (req, socket, head) => {
  if (req.url.startsWith('/exchange')) {
    exchangeProxy.upgrade(req, socket, head);
  }
});

server.listen(PORT, () => {
  console.log(`
╔══════════════════════════════════════════════════╗
║     🚌 CrownyBus RNS Server v1.0                ║
║     Route Name System - Central Hub              ║
╠══════════════════════════════════════════════════╣
║  Port: ${String(PORT).padEnd(41)}║
║  Node: crownybus.com                             ║
╠══════════════════════════════════════════════════╣
║  Routes:                                         ║
║    /exchange → Exchange Platform (Railway)       ║
║    /rns      → RNS Management API                ║
║    /         → CrownyBus Landing                 ║
╠══════════════════════════════════════════════════╣
║  CTP Addresses:                                  ║
║    ctp://exchange.crowny → /exchange              ║
╚══════════════════════════════════════════════════╝
  `);
});

// ═══════════════════════════════════════════════════
// Landing Page HTML
// ═══════════════════════════════════════════════════
function getLandingPage() {
  const services = Object.entries(ROUTE_TABLE).map(([key, r]) => `
    <div class="service-card">
      <div class="service-header">
        <span class="service-status ${r.status}"></span>
        <h3>${r.name}</h3>
        <span class="version">v${r.version}</span>
      </div>
      <p class="desc">${r.description}</p>
      <div class="endpoints">
        <div class="endpoint">
          <span class="label">HTTP</span>
          <a href="${r.path}">${r.path}</a>
        </div>
        <div class="endpoint">
          <span class="label">CTP</span>
          <code>${r.protocol}</code>
        </div>
      </div>
      <a href="${r.path}" class="enter-btn">접속 →</a>
    </div>
  `).join('');

  return `<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CrownyBus - CrownyOS Service Hub</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    
    body {
      font-family: 'SF Mono', 'Fira Code', monospace;
      background: #0a0a0f;
      color: #e0e0e0;
      min-height: 100vh;
    }
    
    .header {
      text-align: center;
      padding: 60px 20px 40px;
      background: linear-gradient(180deg, #0d1117 0%, #0a0a0f 100%);
      border-bottom: 1px solid #1a1a2e;
    }
    
    .logo {
      font-size: 48px;
      margin-bottom: 8px;
    }
    
    .title {
      font-size: 28px;
      font-weight: 700;
      color: #ffd700;
      letter-spacing: 2px;
    }
    
    .subtitle {
      font-size: 14px;
      color: #666;
      margin-top: 8px;
    }
    
    .rns-bar {
      background: #111;
      border: 1px solid #222;
      border-radius: 8px;
      max-width: 600px;
      margin: 24px auto 0;
      padding: 12px 20px;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    
    .rns-bar .protocol { color: #ffd700; font-weight: bold; }
    .rns-bar .domain { color: #4ecdc4; }
    .rns-bar .cursor {
      width: 2px; height: 18px;
      background: #ffd700;
      animation: blink 1s infinite;
    }
    
    @keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }
    
    .main {
      max-width: 900px;
      margin: 0 auto;
      padding: 40px 20px;
    }
    
    .section-title {
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 3px;
      color: #555;
      margin-bottom: 20px;
      padding-bottom: 8px;
      border-bottom: 1px solid #1a1a2e;
    }
    
    .services {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
      gap: 16px;
    }
    
    .service-card {
      background: #111118;
      border: 1px solid #1e1e2e;
      border-radius: 12px;
      padding: 24px;
      transition: all 0.2s;
    }
    
    .service-card:hover {
      border-color: #ffd700;
      transform: translateY(-2px);
      box-shadow: 0 4px 20px rgba(255, 215, 0, 0.1);
    }
    
    .service-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 12px;
    }
    
    .service-status {
      width: 8px; height: 8px;
      border-radius: 50%;
    }
    .service-status.active { background: #4ecdc4; box-shadow: 0 0 8px #4ecdc4; }
    .service-status.inactive { background: #666; }
    
    .service-header h3 { font-size: 16px; color: #fff; flex: 1; }
    .version { font-size: 11px; color: #555; background: #1a1a2e; padding: 2px 8px; border-radius: 4px; }
    
    .desc { font-size: 13px; color: #777; margin-bottom: 16px; }
    
    .endpoints { margin-bottom: 16px; }
    .endpoint {
      display: flex; align-items: center; gap: 8px;
      font-size: 12px; margin-bottom: 6px;
    }
    .endpoint .label {
      background: #1a1a2e; color: #ffd700;
      padding: 1px 6px; border-radius: 3px;
      font-size: 10px; font-weight: bold;
      min-width: 36px; text-align: center;
    }
    .endpoint a { color: #4ecdc4; text-decoration: none; }
    .endpoint a:hover { text-decoration: underline; }
    .endpoint code { color: #888; font-size: 12px; }
    
    .enter-btn {
      display: inline-block;
      background: linear-gradient(135deg, #ffd700, #f0c000);
      color: #000;
      padding: 8px 20px;
      border-radius: 6px;
      text-decoration: none;
      font-weight: bold;
      font-size: 13px;
      transition: all 0.2s;
    }
    .enter-btn:hover { transform: scale(1.05); box-shadow: 0 2px 12px rgba(255, 215, 0, 0.3); }
    
    .stats {
      margin-top: 40px;
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }
    
    .stat-card {
      background: #111118;
      border: 1px solid #1e1e2e;
      border-radius: 8px;
      padding: 20px;
      text-align: center;
    }
    
    .stat-value { font-size: 24px; color: #ffd700; font-weight: bold; }
    .stat-label { font-size: 11px; color: #555; margin-top: 4px; text-transform: uppercase; letter-spacing: 1px; }
    
    .footer {
      text-align: center;
      padding: 40px 20px;
      color: #333;
      font-size: 12px;
    }
    .footer a { color: #555; text-decoration: none; }
    
    @media (max-width: 480px) {
      .services { grid-template-columns: 1fr; }
      .stats { grid-template-columns: 1fr; }
      .title { font-size: 22px; }
    }
  </style>
</head>
<body>
  <div class="header">
    <div class="logo">🚌</div>
    <div class="title">CROWNYBUS</div>
    <div class="subtitle">CrownyOS Route Name System · Service Hub</div>
    <div class="rns-bar">
      <span class="protocol">rns://</span>
      <span class="domain">crownybus.com</span>
      <div class="cursor"></div>
    </div>
  </div>
  
  <div class="main">
    <div class="section-title">Active Services</div>
    <div class="services">${services}</div>
    
    <div class="stats">
      <div class="stat-card">
        <div class="stat-value">${Object.keys(ROUTE_TABLE).length}</div>
        <div class="stat-label">Active Routes</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="uptime">0s</div>
        <div class="stat-label">Uptime</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">v1.0</div>
        <div class="stat-label">RNS Version</div>
      </div>
    </div>
  </div>
  
  <div class="footer">
    <p>CrownyOS RNS v1.0 · Node: crownybus.com</p>
    <p style="margin-top:4px;">
      <a href="/rns/status">Status</a> · 
      <a href="/rns/routes">Routes</a> · 
      <a href="/exchange">Exchange</a>
    </p>
  </div>
  
  <script>
    // Uptime counter
    const start = Date.now();
    setInterval(() => {
      const s = Math.floor((Date.now() - start) / 1000);
      const h = Math.floor(s / 3600);
      const m = Math.floor((s % 3600) / 60);
      document.getElementById('uptime').textContent = 
        h > 0 ? h + 'h ' + m + 'm' : m > 0 ? m + 'm ' + (s%60) + 's' : s + 's';
    }, 1000);
  </script>
</body>
</html>`;
}

function get404Page(url) {
  return `<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>404 - CrownyBus RNS</title>
  <style>
    body { font-family: 'SF Mono', monospace; background: #0a0a0f; color: #e0e0e0; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
    .container { text-align: center; }
    .code { font-size: 72px; color: #ffd700; font-weight: bold; }
    .msg { color: #666; margin: 16px 0; }
    .url { color: #ff4444; font-size: 14px; background: #1a1a2e; padding: 8px 16px; border-radius: 4px; display: inline-block; margin: 12px 0; }
    a { color: #4ecdc4; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .routes { margin-top: 24px; font-size: 13px; color: #555; }
  </style>
</head>
<body>
  <div class="container">
    <div class="code">404</div>
    <div class="msg">RNS 경로를 찾을 수 없습니다</div>
    <div class="url">${url}</div>
    <div class="routes">
      <p>사용 가능한 경로:</p>
      <p><a href="/exchange">/exchange</a> → Crowny Exchange Platform</p>
      <p><a href="/rns/routes">/rns/routes</a> → 라우팅 테이블</p>
      <p><a href="/">/ → 메인</a></p>
    </div>
  </div>
</body>
</html>`;
}
