# 🏛 CrownyOS 웹 게이트웨이 — 한선어(HanSeon Language)

> 세계 최초 한국어 프로그래밍 언어로 구동되는 웹서버

## CTP 프로토콜

```
크라우니 브라우저:  ctp://trading.crowny
일반 브라우저:     https://crownybus.com/trading
```

## 한선어 코드 예시

```python
※ CTP 이름 해석
함수 해석(자기, 이름):
    만약 아닌 이름:
        반환 {"error": "이름을 입력하세요"}
    레코드 = 자기.레코드.get(이름)
    만약 아닌 레코드:
        반환 {"error": f"'{이름}' 미등록"}
    반환 {**레코드, "name": 이름}
```

## 파일 구조

| 파일 | 설명 |
|---|---|
| `hanseon.py` | 한선어 인터프리터 v1.0 (트랜스파일러 + 런타임) |
| `서버.hsn` | 웹 게이트웨이 서버 (한선어) |
| `등록소.hsn` | CTP 이름등록소 (한선어) |
| `Dockerfile` | Railway 배포 설정 |

## 실행

```bash
# 한선어 서버 실행
python3 hanseon.py 서버.hsn

# 인터프리터 셀프테스트
python3 hanseon.py --자가검사

# Python 변환 출력
python3 hanseon.py 서버.hsn --변환
```

## 한선어 키워드

| 한선어 | Python | 설명 |
|---|---|---|
| `함수` | `def` | 함수 정의 |
| `클래스` | `class` | 클래스 정의 |
| `만약` | `if` | 조건문 |
| `아니면` | `else` | 아니면 |
| `각각` | `for` | 반복문 |
| `동안` | `while` | 반복문 |
| `반환` | `return` | 반환 |
| `참/거짓` | `True/False` | 불리언 |
| `출력` | `print` | 출력 |
| `가져오기` | `import` | 모듈 |
| `자기` | `self` | 인스턴스 |
| `※` | `#` | 주석 |

## CrownyOS 균형삼진 컴퓨팅

한선어는 CrownyOS 균형삼진 컴퓨팅 플랫폼의 기본 프로그래밍 언어입니다.
