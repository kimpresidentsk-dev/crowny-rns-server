#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  CrownyOS 웹 게이트웨이 — crownybus.com                      ║
║                                                              ║
║  crownybus.com/xxx  ↔  ctp://xxx.crowny                     ║
║  Railway 포트 8080 통합 서버                                  ║
╚══════════════════════════════════════════════════════════════╝
"""

import json, time, os, re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from rns import CTPRegistry, NAME_PATTERN, SERVICE_TYPES

VERSION = "1.0.0"
PORT = int(os.environ.get("PORT", 8080))
RNS = CTPRegistry()

# ═══════════════════════════════════════════════════════
# HTML 템플릿
# ═══════════════════════════════════════════════════════

STYLE = """
:root{--bg:#1a1208;--bg2:#2c1e10;--card:#342518;--bd:#4e3428;--fg:#fff8f0;--dim:#a89080;--mute:#6b5b50;--gold:#d4a574;--amber:#e8b86d;--copper:#b87333;--up:#4ade80;--dn:#f87171}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:'Pretendard','Apple SD Gothic Neo',sans-serif;font-size:13px;min-height:100vh}
.hd{background:var(--bg2);border-bottom:1px solid var(--bd);padding:14px 24px;display:flex;align-items:center;justify-content:space-between}
.logo{font-size:20px;font-weight:700;color:var(--gold)}.logo span{color:var(--dim);font-size:12px;font-weight:400;margin-left:8px}
.nav{display:flex;gap:6px}.nav a{padding:6px 14px;border-radius:6px;color:var(--dim);text-decoration:none;font-size:12px;border:1px solid transparent;transition:.2s}.nav a:hover,.nav a.on{color:var(--gold);border-color:var(--bd);background:var(--bg)}
.main{max-width:1000px;margin:0 auto;padding:24px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:16px;margin-bottom:12px}
.card h3{font-size:13px;color:var(--gold);margin-bottom:10px;font-weight:600}
.mono{font-family:'D2Coding','Menlo',monospace}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;margin-bottom:16px}
.svc-card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:16px;cursor:pointer;transition:.2s;text-decoration:none;color:var(--fg);display:block}
.svc-card:hover{border-color:var(--gold);transform:translateY(-2px)}
.svc-icon{font-size:28px;margin-bottom:6px}
.svc-name{font-size:14px;font-weight:700;color:var(--gold)}
.svc-desc{font-size:11px;color:var(--dim);margin-top:4px}
.svc-addr{font-family:'D2Coding',monospace;font-size:10px;color:var(--mute);margin-top:6px;background:var(--bg);padding:3px 6px;border-radius:4px;display:inline-block}
.btn{border:none;border-radius:6px;padding:8px 16px;cursor:pointer;font-size:12px;font-weight:600;transition:.2s;background:var(--gold);color:#1a1208}.btn:hover{background:var(--amber)}
.inp{background:var(--bg);border:1px solid var(--bd);border-radius:6px;padding:8px 10px;color:var(--fg);font-size:12px;width:100%}
.tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;background:var(--bg);border:1px solid var(--bd);color:var(--dim);margin:2px}
.hero{text-align:center;padding:40px 0 30px}
.hero h1{font-size:28px;color:var(--gold);margin-bottom:8px}
.hero p{color:var(--dim);font-size:14px}
.stat-row{display:flex;gap:20px;justify-content:center;margin:20px 0}
.stat-item{text-align:center}.stat-item .v{font-size:20px;font-weight:700;color:var(--amber);font-family:'D2Coding',monospace}.stat-item .l{font-size:10px;color:var(--mute);margin-top:2px}
.footer{text-align:center;padding:30px;color:var(--mute);font-size:11px}
.err{color:var(--dn)}.ok{color:var(--up)}
select.inp{appearance:auto}
"""

NAV = """
<div class="hd">
  <a href="/" style="text-decoration:none"><div class="logo">🏛 CrownyOS <span>균형삼진 네트워크</span></div></a>
  <div class="nav">
    <a href="/">서비스</a>
    <a href="/trading">트레이딩</a>
    <a href="/rns">RNS</a>
    <a href="/register">등록</a>
  </div>
</div>
"""

def page(title, body, active=""):
    nav = NAV
    if active:
        nav = nav.replace(f'href="/{active}"', f'href="/{active}" class="on"')
    return f"""<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title} — CrownyOS</title><style>{STYLE}</style></head>
<body>{nav}<div class="main">{body}</div>
<div class="footer">CrownyOS 균형삼진 컴퓨팅 — ctp:// 프로토콜<br>
crownybus.com/name ↔ ctp://name.crowny</div></body></html>"""


def portal_page():
    services = RNS.list_all()
    stats = RNS.stats()

    cards = ""
    for s in services:
        cards += f"""<a href="/{s['name']}" class="svc-card">
<div class="svc-icon">{s['icon']}</div>
<div class="svc-name">{s['title']}</div>
<div class="svc-desc">{s['desc']}</div>
<div style="margin-top:6px">
  <span class="svc-addr">ctp://{s['name']}.crowny</span>
  <span class="tag">{s['service']}</span>
  <span class="tag">{s['hits']}회</span>
</div></a>"""

    body = f"""
<div class="hero">
  <h1>🏛 CrownyOS 네트워크</h1>
  <p>균형삼진 컴퓨팅 — CTP 프로토콜 서비스 포탈</p>
  <div class="stat-row">
    <div class="stat-item"><div class="v">{stats['records']}</div><div class="l">서비스</div></div>
    <div class="stat-item"><div class="v">{stats['services']}</div><div class="l">타입</div></div>
    <div class="stat-item"><div class="v">{stats['total_hits']}</div><div class="l">조회</div></div>
  </div>
</div>
<div class="grid">{cards}</div>
"""
    return page("포탈", body)


def register_page(msg=""):
    opts = "".join(f'<option value="{t}">{t}</option>' for t in SERVICE_TYPES)
    alert = f'<div class="card" style="border-color:var(--gold)"><p>{msg}</p></div>' if msg else ""

    body = f"""
<div class="hero" style="padding:20px 0">
  <h1>📝 서비스 등록</h1>
  <p>CTP 네트워크에 새 서비스를 등록하세요</p>
</div>
{alert}
<div class="card">
  <h3>새 서비스 등록</h3>
  <form method="POST" action="/register" style="display:grid;gap:10px;max-width:500px">
    <div>
      <label style="font-size:11px;color:var(--dim);display:block;margin-bottom:4px">서비스 이름 (영어, 숫자, _, -)</label>
      <div style="display:flex;align-items:center;gap:4px">
        <span style="color:var(--mute);font-size:12px;font-family:monospace">ctp://</span>
        <input name="name" class="inp mono" placeholder="my-service" pattern="[a-zA-Z][a-zA-Z0-9_-]*" required style="flex:1">
        <span style="color:var(--mute);font-size:12px;font-family:monospace">.crowny</span>
      </div>
    </div>
    <div>
      <label style="font-size:11px;color:var(--dim);display:block;margin-bottom:4px">표시 이름</label>
      <input name="title" class="inp" placeholder="My Service">
    </div>
    <div>
      <label style="font-size:11px;color:var(--dim);display:block;margin-bottom:4px">설명</label>
      <input name="desc" class="inp" placeholder="서비스 설명...">
    </div>
    <div style="display:flex;gap:10px">
      <div style="flex:1">
        <label style="font-size:11px;color:var(--dim);display:block;margin-bottom:4px">서비스 타입</label>
        <select name="service" class="inp">{opts}</select>
      </div>
      <div style="flex:1">
        <label style="font-size:11px;color:var(--dim);display:block;margin-bottom:4px">아이콘 (이모지)</label>
        <input name="icon" class="inp" placeholder="📦" value="📦" maxlength="4">
      </div>
    </div>
    <button type="submit" class="btn" style="margin-top:6px">등록</button>
  </form>
</div>
<div class="card">
  <h3>이름 규칙</h3>
  <div style="font-size:11px;color:var(--dim);line-height:1.8">
    • 첫 글자: 영어 (a-z, A-Z)<br>
    • 나머지: 영어, 숫자, _, - (최대 63자)<br>
    • 예시: <code class="mono" style="background:var(--bg);padding:1px 4px;border-radius:3px">my-app</code>,
      <code class="mono" style="background:var(--bg);padding:1px 4px;border-radius:3px">crowny_wallet</code>,
      <code class="mono" style="background:var(--bg);padding:1px 4px;border-radius:3px">dex-v2</code><br>
    • 등록 후: <code class="mono" style="background:var(--bg);padding:1px 4px;border-radius:3px">ctp://이름.crowny</code> ↔
      <code class="mono" style="background:var(--bg);padding:1px 4px;border-radius:3px">crownybus.com/이름</code>
  </div>
</div>
"""
    return page("서비스 등록", body, "register")


def rns_page():
    services = RNS.list_all()
    stats = RNS.stats()

    rows = ""
    for s in services:
        rows += f"""<tr>
<td>{s['icon']} {s['title']}</td>
<td class="mono" style="color:var(--gold)">ctp://{s['name']}.crowny</td>
<td class="mono">crownybus.com/{s['name']}</td>
<td><span class="tag">{s['service']}</span></td>
<td class="mono">{s['hits']}</td></tr>"""

    body = f"""
<div class="hero" style="padding:20px 0">
  <h1>🌐 RNS — Resolve Name Service</h1>
  <p>CTP 프로토콜 이름 해석 서비스 ({stats['records']}레코드)</p>
</div>
<div class="card">
  <h3>등록된 서비스</h3>
  <table style="width:100%;border-collapse:collapse;font-size:11px">
    <thead><tr>
      <th style="text-align:left;padding:8px 6px;color:var(--mute);font-weight:500;border-bottom:1px solid var(--bd)">이름</th>
      <th style="text-align:left;padding:8px 6px;color:var(--mute);font-weight:500;border-bottom:1px solid var(--bd)">CTP 주소</th>
      <th style="text-align:left;padding:8px 6px;color:var(--mute);font-weight:500;border-bottom:1px solid var(--bd)">웹 주소</th>
      <th style="text-align:left;padding:8px 6px;color:var(--mute);font-weight:500;border-bottom:1px solid var(--bd)">타입</th>
      <th style="text-align:left;padding:8px 6px;color:var(--mute);font-weight:500;border-bottom:1px solid var(--bd)">조회</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
<div class="card">
  <h3>📡 CTP 프로토콜</h3>
  <div style="font-size:11px;color:var(--dim);line-height:1.8">
    <b style="color:var(--gold)">CTP (Crowny Transfer Protocol)</b> — 균형삼진 네트워크 전용 프로토콜<br><br>
    내부망: <code class="mono" style="background:var(--bg);padding:2px 6px;border-radius:3px">ctp://서비스이름.crowny</code><br>
    외부웹: <code class="mono" style="background:var(--bg);padding:2px 6px;border-radius:3px">https://crownybus.com/서비스이름</code><br><br>
    크라우니 브라우저에서는 ctp:// 주소로 직접 접속,<br>
    일반 브라우저에서는 crownybus.com을 통해 RNS가 자동 라우팅합니다.
  </div>
</div>
"""
    return page("RNS", body, "rns")


def service_page(name, record):
    """개별 서비스 페이지"""
    body = f"""
<div class="hero" style="padding:20px 0">
  <div style="font-size:48px;margin-bottom:8px">{record.get('icon','📦')}</div>
  <h1>{record.get('title', name)}</h1>
  <p>{record.get('desc', '')}</p>
</div>
<div class="card">
  <h3>서비스 정보</h3>
  <table style="font-size:12px;line-height:2.2">
    <tr><td style="color:var(--mute);padding-right:20px">CTP 주소</td>
        <td class="mono" style="color:var(--gold)">ctp://{name}.crowny</td></tr>
    <tr><td style="color:var(--mute)">웹 주소</td>
        <td class="mono">crownybus.com/{name}</td></tr>
    <tr><td style="color:var(--mute)">서비스 타입</td>
        <td><span class="tag">{record.get('service','web')}</span></td></tr>
    <tr><td style="color:var(--mute)">로컬 포트</td>
        <td class="mono">{record.get('local_port', '—')}</td></tr>
    <tr><td style="color:var(--mute)">조회 수</td>
        <td>{record.get('hits', 0)}회</td></tr>
  </table>
</div>
<div class="card">
  <h3>접속</h3>
  <div style="font-size:12px;line-height:2;color:var(--dim)">
    <b style="color:var(--fg)">크라우니 브라우저:</b>
    <code class="mono" style="background:var(--bg);padding:2px 8px;border-radius:4px;color:var(--gold)">ctp://{name}.crowny</code><br>
    <b style="color:var(--fg)">로컬 네트워크:</b>
    <code class="mono" style="background:var(--bg);padding:2px 8px;border-radius:4px">http://localhost:{record.get('local_port', '?')}</code><br>
    <b style="color:var(--fg)">공개 웹:</b>
    <code class="mono" style="background:var(--bg);padding:2px 8px;border-radius:4px">https://crownybus.com/{name}</code>
  </div>
</div>
<div style="text-align:center;margin-top:16px">
  <a href="/" class="btn" style="text-decoration:none">← 서비스 목록</a>
</div>
"""
    return page(record.get("title", name), body)


def not_found_page(name):
    body = f"""
<div class="hero">
  <div style="font-size:48px;margin-bottom:8px">❓</div>
  <h1>ctp://{name}.crowny</h1>
  <p style="color:var(--dn)">등록되지 않은 서비스입니다</p>
</div>
<div style="text-align:center;margin-top:20px">
  <a href="/register" class="btn" style="text-decoration:none;margin-right:10px">서비스 등록</a>
  <a href="/" class="btn" style="text-decoration:none;background:var(--bg);color:var(--gold);border:1px solid var(--bd)">서비스 목록</a>
</div>
"""
    return page("미등록", body)


# ═══════════════════════════════════════════════════════
# 핸들러
# ═══════════════════════════════════════════════════════

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _html(self, html, code=200):
        body = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        params = parse_qs(parsed.query)

        # 정적 페이지
        if path == "/":
            self._html(portal_page())
        elif path == "/register":
            self._html(register_page())
        elif path == "/rns":
            self._html(rns_page())
        elif path == "/health":
            self._json({"status": "ok", "version": VERSION, "records": len(RNS.records)})
        elif path == "/favicon.ico":
            self.send_response(204); self.end_headers()

        # API
        elif path == "/api/rns/list":
            self._json(RNS.list_all())
        elif path == "/api/rns/stats":
            self._json(RNS.stats())
        elif path.startswith("/api/rns/resolve/"):
            name = path.split("/")[-1]
            self._json(RNS.resolve(name))
        elif path.startswith("/api/rns/validate/"):
            name = path.split("/")[-1]
            ok, err = RNS.validate_name(name)
            self._json({"valid": ok, "error": err})

        # CTP 라우팅: /xxx → ctp://xxx.crowny
        else:
            name = path.lstrip("/").split("/")[0].lower()
            if name and NAME_PATTERN.match(name):
                rec = RNS.resolve(name)
                if "error" not in rec:
                    self._html(service_page(name, rec))
                else:
                    self._html(not_found_page(name), 404)
            else:
                self._json({"error": "Not Found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""

        if path == "/register":
            # HTML form POST
            from urllib.parse import parse_qs as pqs
            body = pqs(raw.decode("utf-8"))
            name = body.get("name", [""])[0].strip().lower()
            service = body.get("service", ["web"])[0]
            title = body.get("title", [""])[0]
            desc = body.get("desc", [""])[0]
            icon = body.get("icon", ["📦"])[0]

            result = RNS.register(name, service, title, desc, icon)
            if "error" in result:
                self._html(register_page(f'<span class="err">❌ {result["error"]}</span>'))
            else:
                self._html(register_page(
                    f'<span class="ok">✅ 등록 완료!</span> '
                    f'<code class="mono">ctp://{name}.crowny</code> ↔ '
                    f'<code class="mono">crownybus.com/{name}</code>'))

        elif path == "/api/rns/register":
            # JSON API
            try:
                body = json.loads(raw)
            except:
                self._json({"error": "JSON 파싱 오류"}, 400); return
            result = RNS.register(
                body.get("name", ""),
                body.get("service", "web"),
                body.get("title", ""),
                body.get("desc", ""),
                body.get("icon", "📦"),
                body.get("owner", "api"),
            )
            self._json(result, 200 if "ok" in result else 400)

        elif path == "/api/rns/delete":
            try:
                body = json.loads(raw)
            except:
                self._json({"error": "JSON 파싱 오류"}, 400); return
            self._json(RNS.delete(body.get("name", ""), body.get("owner", "")))

        else:
            self._json({"error": "Not Found"}, 404)


# ═══════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════

def main():
    httpd = HTTPServer(("0.0.0.0", PORT), Handler)
    stats = RNS.stats()
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  🏛 CrownyOS 웹 게이트웨이 v{VERSION}                          ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  웹:   http://0.0.0.0:{PORT}                                ║
║  도메인: crownybus.com                                       ║
║  프로토콜: CTP (Crowny Transfer Protocol)                    ║
║                                                              ║
║  RNS:  {stats['records']}개 서비스 등록                                  ║
║                                                              ║
║  라우팅:                                                     ║
║    crownybus.com/xxx  →  ctp://xxx.crowny                   ║
║    crownybus.com/trading → ctp://trading.crowny             ║
║    crownybus.com/mind    → ctp://mind.crowny                ║
║    crownybus.com/rns     → RNS 관리                         ║
║    crownybus.com/register → 서비스 등록                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
