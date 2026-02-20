"""
CrownyOS RNS (Resolve Name Service) — Railway Edition
ctp://xxx.crowny ↔ crownybus.com/xxx 매핑

이름 규칙: 영어, 숫자, _, - (첫 글자는 영어)
"""

import json, time, re, os
from pathlib import Path

NAME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]{0,62}$')

# 서비스 타입
SERVICE_TYPES = [
    "mind", "db", "web", "chain", "dex", "p2p", "rns",
    "trade", "ai", "motor", "lidar", "robot", "med", "gene",
]

DATA_DIR = Path(os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "/tmp/crowny-rns"))


class CTPRegistry:
    """CTP 프로토콜 레지스트리 — ctp://name.crowny ↔ crownybus.com/name"""

    def __init__(self):
        self.records = {}  # name → record
        self.data_file = DATA_DIR / "rns_registry.json"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._load()
        self._seed_defaults()

    def _load(self):
        try:
            if self.data_file.exists():
                self.records = json.loads(self.data_file.read_text("utf-8"))
        except:
            self.records = {}

    def save(self):
        try:
            self.data_file.write_text(
                json.dumps(self.records, ensure_ascii=False, indent=2), "utf-8")
        except:
            pass

    def _seed_defaults(self):
        """기본 서비스 등록"""
        defaults = {
            "trading": {"service": "trade", "title": "크라우니트레이딩",
                        "desc": "PVE v4.0 AI 에이전트 트레이딩", "icon": "🏛",
                        "local_port": 7430},
            "mind": {"service": "mind", "title": "CrownyMind",
                     "desc": "균형삼진 인지 엔진 v3.1", "icon": "🧠",
                     "local_port": 7420},
            "db": {"service": "db", "title": "CrownyDB",
                   "desc": "균형삼진 데이터베이스", "icon": "🗄",
                   "local_port": 7420},
            "dex": {"service": "dex", "title": "CROWNY DEX",
                    "desc": "벡터형 균형3진 AMM", "icon": "💎",
                    "local_port": 7422},
            "rns": {"service": "rns", "title": "RNS",
                    "desc": "Resolve Name Service", "icon": "🌐",
                    "local_port": 7424},
            "chain": {"service": "chain", "title": "CrownyChain",
                      "desc": "균형삼진 블록체인", "icon": "⛓",
                      "local_port": 7421},
            "os": {"service": "web", "title": "CrownyOS",
                   "desc": "균형삼진 컴퓨팅 플랫폼", "icon": "🖥",
                   "local_port": 7420},
        }
        changed = False
        for name, info in defaults.items():
            if name not in self.records:
                self.records[name] = {
                    **info,
                    "ctp": f"ctp://{name}.crowny",
                    "web": f"crownybus.com/{name}",
                    "owner": "system",
                    "created": time.time(),
                    "hits": 0,
                }
                changed = True
        if changed:
            self.save()

    def validate_name(self, name: str) -> tuple:
        """이름 유효성 검사 → (ok, error)"""
        if not name:
            return False, "이름을 입력하세요"
        if not NAME_PATTERN.match(name):
            return False, "이름은 영어로 시작, 영어/숫자/_/- 만 가능 (최대 63자)"
        if name in self.records:
            return False, f"'{name}' 이미 등록됨"
        reserved = {"api", "admin", "static", "health", "register", "login", "favicon"}
        if name.lower() in reserved:
            return False, f"'{name}' 은 예약어입니다"
        return True, ""

    def register(self, name: str, service: str = "web",
                 title: str = "", desc: str = "", icon: str = "📦",
                 owner: str = "user") -> dict:
        """새 이름 등록"""
        ok, err = self.validate_name(name)
        if not ok:
            return {"error": err}
        if service not in SERVICE_TYPES:
            service = "web"

        record = {
            "service": service,
            "title": title or name,
            "desc": desc or f"{name}.crowny 서비스",
            "icon": icon,
            "ctp": f"ctp://{name}.crowny",
            "web": f"crownybus.com/{name}",
            "local_port": 0,
            "owner": owner,
            "created": time.time(),
            "hits": 0,
        }
        self.records[name] = record
        self.save()
        return {"ok": True, "name": name, "ctp": record["ctp"], "web": record["web"]}

    def resolve(self, name: str) -> dict:
        """이름 해석 — ctp://name.crowny 또는 crownybus.com/name"""
        name = name.lower().strip()
        # ctp://xxx.crowny → xxx
        if name.startswith("ctp://"):
            name = name[6:]
        if name.endswith(".crowny"):
            name = name[:-7]
        # crownybus.com/xxx → xxx
        if "/" in name:
            name = name.split("/")[-1]

        rec = self.records.get(name)
        if not rec:
            return {"error": f"'{name}' 미등록", "name": name}
        rec["hits"] = rec.get("hits", 0) + 1
        self.save()
        return {**rec, "name": name}

    def list_all(self) -> list:
        """전체 목록"""
        result = []
        for name, rec in sorted(self.records.items()):
            result.append({
                "name": name,
                "ctp": rec.get("ctp", f"ctp://{name}.crowny"),
                "web": rec.get("web", f"crownybus.com/{name}"),
                "title": rec.get("title", name),
                "desc": rec.get("desc", ""),
                "icon": rec.get("icon", "📦"),
                "service": rec.get("service", "web"),
                "hits": rec.get("hits", 0),
            })
        return result

    def delete(self, name: str, owner: str = "") -> dict:
        if name not in self.records:
            return {"error": f"'{name}' 미등록"}
        rec = self.records[name]
        if rec.get("owner") == "system":
            return {"error": "시스템 서비스는 삭제 불가"}
        if owner and rec.get("owner") != owner:
            return {"error": "권한 없음"}
        del self.records[name]
        self.save()
        return {"ok": True, "deleted": name}

    def stats(self) -> dict:
        return {
            "records": len(self.records),
            "services": len(set(r.get("service", "web") for r in self.records.values())),
            "total_hits": sum(r.get("hits", 0) for r in self.records.values()),
            "service_types": SERVICE_TYPES,
        }
