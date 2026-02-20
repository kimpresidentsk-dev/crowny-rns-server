#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  한선어 (HanSeon Language) 인터프리터 v1.0                    ║
║                                                              ║
║  세계 최초 균형삼진 기반 한국어 프로그래밍 언어                  ║
║  .hsn 파일을 Python으로 트랜스파일 후 실행                     ║
║                                                              ║
║  사용법:                                                     ║
║    python3 hanseon.py 서버.hsn           실행                 ║
║    python3 hanseon.py 서버.hsn --변환     Python 변환 출력     ║
║    python3 hanseon.py --자가검사          셀프테스트            ║
║                                                              ║
║  CrownyOS 균형삼진 컴퓨팅 — CTP 프로토콜                      ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys, os, re, traceback

VERSION = "1.0.0"

# ═══════════════════════════════════════════════════════
# 한선어 → Python 키워드 매핑
# ═══════════════════════════════════════════════════════

# 핵심 키워드 (줄 시작 패턴)
KEYWORD_MAP = {
    # 제어 흐름
    "만약 ":     "if ",
    "아니면만약 ": "elif ",
    "아니면:":   "else:",
    "아니면 만약 ": "elif ",
    "동안 ":     "while ",
    "각각 ":     "for ",
    "안에 ":     "in ",
    "시도:":     "try:",
    "예외:":     "except:",
    "예외 ":     "except ",
    "마침내:":   "finally:",
    "멈춤":      "break",
    "계속":      "continue",
    "전달":      "pass",

    # 정의
    "함수 ":     "def ",
    "클래스 ":   "class ",
    "반환 ":     "return ",
    "반환":      "return",
    "올리기 ":   "raise ",
    "생성 ":     "yield ",
    "전역 ":     "global ",

    # 논리
    "참":        "True",
    "거짓":      "False",
    "없음":      "None",
    "그리고":    "and",
    "또는":      "or",
    "아닌 ":     "not ",
    "아닌":      "not",

    # 기타
    "삭제 ":     "del ",
    "단언 ":     "assert ",
    "~와 ":      "with ",
}

# 인라인 치환 (줄 내부)
INLINE_MAP = {
    " 안에 ":   " in ",
    " 각각 ":   " for ",
    " 만약 ":   " if ",
    " 아니면 ": " else ",
    " 그리고 ": " and ",
    " 또는 ":   " or ",
    " 아닌 ":   " not ",
    " ~로 ":    " as ",
    " ~로\n":   " as\n",
    "(참)":     "(True)",
    "(거짓)":   "(False)",
    "(없음)":   "(None)",
    ", 참)":    ", True)",
    ", 거짓)":  ", False)",
    ", 없음)":  ", None)",
    "=참":      "=True",
    "=거짓":    "=False",
    " 없음이 아니면": " is not None",
    " 없음이면":  " is None",
    "=없음":    "=None",
    "(없음)":   "(None)",
    ", 없음)":  ", None)",
    ", 없음,":  ", None,",
    " 참":      " True",
    " 거짓":    " False",
    " 없음":    " None",
    " 참:":     " True:",
    " 거짓:":   " False:",
    " 없음:":   " None:",
    " 참,":     " True,",
    " 거짓,":   " False,",
    " 없음,":   " None,",
    "이다 ":    "is ",
    " 이다":    " is",
}

# 내장함수 매핑
BUILTIN_MAP = {
    "출력":     "print",
    "입력":     "input",
    "길이":     "len",
    "범위":     "range",
    "정수":     "int",
    "실수":     "float",
    "문자열":   "str",
    "목록":     "list",
    "사전":     "dict",
    "집합":     "set",
    "튜플":     "tuple",
    "정렬":     "sorted",
    "뒤집기":   "reversed",
    "열거":     "enumerate",
    "묶기":     "zip",
    "모두":     "all",
    "하나라도": "any",
    "절대값":   "abs",
    "최대":     "max",
    "최소":     "min",
    "합계":     "sum",
    "열기":     "open",
    "종류":     "type",
    "인스턴스": "isinstance",
    "속성있음": "hasattr",
    "속성가져오기": "getattr",
    "속성설정": "setattr",
    "해시":     "hash",
    "아이디":   "id",
    "다음":     "next",
    "호출가능": "callable",
    "지도":     "map",
    "거르기":   "filter",
}

# 가져오기 (import) 패턴
IMPORT_RE = re.compile(r'^가져오기\s+(.+)$')
FROM_IMPORT_RE = re.compile(r'^(.+)에서\s+가져오기\s+(.+)$')


# ═══════════════════════════════════════════════════════
# 트랜스파일러
# ═══════════════════════════════════════════════════════

class HanSeonTranspiler:
    """한선어 → Python 트랜스파일러"""

    def __init__(self):
        self.source_map = {}  # py_line → hsn_line (디버깅용)

    def transpile(self, source: str, filename: str = "<한선>") -> str:
        """한선어 소스 → Python 소스"""
        lines = source.split("\n")
        py_lines = []

        # 첫 줄 인코딩 + 출처
        py_lines.append(f"# -*- coding: utf-8 -*-")
        py_lines.append(f"# 한선어 자동 변환: {filename}")
        py_lines.append(f"# HanSeon Language v{VERSION}")
        py_lines.append("")

        for i, line in enumerate(lines, 1):
            py_line = self._transpile_line(line, i)
            py_lines.append(py_line)
            self.source_map[len(py_lines)] = i

        return "\n".join(py_lines)

    def _transpile_line(self, line: str, lineno: int) -> str:
        """한 줄 변환"""
        # 빈 줄
        if not line.strip():
            return line

        # 주석 (# 또는 // 또는 ※)
        stripped = line.lstrip()
        if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("※"):
            # // → #, ※ → #
            if stripped.startswith("//"):
                indent = line[:len(line) - len(stripped)]
                return indent + "#" + stripped[2:]
            if stripped.startswith("※"):
                indent = line[:len(line) - len(stripped)]
                return indent + "#" + stripped[1:]
            return line

        # 문자열 내부 보호
        # 문자열 밖의 코드만 변환
        protected, strings = self._protect_strings(line)
        converted = self._convert_code(protected)
        result = self._restore_strings(converted, strings)

        return result

    def _protect_strings(self, line):
        """문자열 리터럴을 플레이스홀더로 대체"""
        strings = []
        result = []
        i = 0
        in_str = None

        while i < len(line):
            c = line[i]

            if in_str is None:
                if c in ('"', "'"):
                    # 삼중 따옴표 확인
                    if line[i:i+3] in ('"""', "'''"):
                        end = line.find(line[i:i+3], i+3)
                        if end == -1:
                            strings.append(line[i:])
                            result.append(f"__STR{len(strings)-1}__")
                            break
                        strings.append(line[i:end+3])
                        result.append(f"__STR{len(strings)-1}__")
                        i = end + 3
                        continue
                    # 일반 따옴표
                    in_str = c
                    start = i
                    i += 1
                    continue
                result.append(c)
                i += 1
            else:
                if c == '\\':
                    i += 2
                    continue
                if c == in_str:
                    strings.append(line[start:i+1])
                    result.append(f"__STR{len(strings)-1}__")
                    in_str = None
                i += 1

        if in_str is not None:
            strings.append(line[start:])
            result.append(f"__STR{len(strings)-1}__")

        return "".join(result), strings

    def _restore_strings(self, line, strings):
        """플레이스홀더 → 원래 문자열"""
        for i, s in enumerate(strings):
            line = line.replace(f"__STR{i}__", s)
        return line

    def _convert_code(self, line: str) -> str:
        """코드 부분 변환 (문자열 제외)"""
        # 인덴트 보존
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]

        if not stripped:
            return line

        # 가져오기 (import)
        m = FROM_IMPORT_RE.match(stripped)
        if m:
            module = m.group(1).strip()
            names = m.group(2).strip().replace(" ~로 ", " as ")
            return f"{indent}from {module} import {names}"

        m = IMPORT_RE.match(stripped)
        if m:
            modules = m.group(1).strip().replace(" ~로 ", " as ")
            return f"{indent}import {modules}"

        # 키워드 치환 (줄 시작)
        for kor, eng in KEYWORD_MAP.items():
            if stripped.startswith(kor):
                stripped = eng + stripped[len(kor):]
                break

        # 인라인 치환
        for kor, eng in INLINE_MAP.items():
            stripped = stripped.replace(kor, eng)

        # 내장함수 치환 (함수호출 패턴)
        for kor, eng in BUILTIN_MAP.items():
            # 함수호출: 한글( → 영어(
            stripped = stripped.replace(f"{kor}(", f"{eng}(")
            # 인자 참조: =한글) / =한글, / ,한글)
            stripped = stripped.replace(f"={kor})", f"={eng})")
            stripped = stripped.replace(f"={kor},", f"={eng},")
            stripped = stripped.replace(f"={kor}\n", f"={eng}\n")
            stripped = stripped.replace(f", {kor})", f", {eng})")
            stripped = stripped.replace(f"({kor})", f"({eng})")
            stripped = stripped.replace(f"({kor},", f"({eng},")

        # 특수 패턴
        # "자기" → "self"
        stripped = re.sub(r'\b자기\b', 'self', stripped)
        stripped = re.sub(r'\b자기\.', 'self.', stripped)

        # "없음이면" → "is None"
        stripped = stripped.replace("없음이면", "is None")
        stripped = stripped.replace(" 없음이 아니면", " is not None")

        return indent + stripped

    def transpile_file(self, filepath: str) -> str:
        """파일 변환"""
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        return self.transpile(source, os.path.basename(filepath))


# ═══════════════════════════════════════════════════════
# 실행 엔진
# ═══════════════════════════════════════════════════════

class HanSeonRuntime:
    """한선어 실행 엔진"""

    def __init__(self):
        self.transpiler = HanSeonTranspiler()
        self.modules = {}  # 캐시

    def run_file(self, filepath: str, argv=None):
        """한선어 파일 실행"""
        filepath = os.path.abspath(filepath)
        dirname = os.path.dirname(filepath)

        # 트랜스파일
        py_source = self.transpiler.transpile_file(filepath)

        # 한선어 모듈 임포트 지원
        sys.path.insert(0, dirname)
        self._install_import_hook(dirname)

        # 실행
        old_argv = sys.argv
        if argv is not None:
            sys.argv = argv
        try:
            code = compile(py_source, filepath, "exec")
            namespace = {
                "__file__": filepath,
                "__name__": "__main__",
                "__builtins__": __builtins__,
            }
            exec(code, namespace)
        except Exception as e:
            self._format_error(e, filepath, py_source)
            sys.exit(1)
        finally:
            sys.argv = old_argv

    def _install_import_hook(self, base_dir):
        """한선어 .hsn 파일 임포트 훅"""
        import importlib.abc, importlib.util

        class HanSeonFinder(importlib.abc.MetaPathFinder):
            def find_module(self, fullname, path=None):
                # .hsn 파일 검색
                hsn_path = os.path.join(base_dir, fullname + ".hsn")
                if os.path.exists(hsn_path):
                    return HanSeonLoader(hsn_path)
                # 한글 이름 → 영어 매핑 시도
                return None

        class HanSeonLoader(importlib.abc.Loader):
            def __init__(self, path):
                self.path = path
                self.transpiler = HanSeonTranspiler()

            def load_module(self, fullname):
                if fullname in sys.modules:
                    return sys.modules[fullname]
                py_source = self.transpiler.transpile_file(self.path)
                code = compile(py_source, self.path, "exec")
                import types
                mod = types.ModuleType(fullname)
                mod.__file__ = self.path
                mod.__loader__ = self
                sys.modules[fullname] = mod
                exec(code, mod.__dict__)
                return mod

        # 훅 등록 (중복 방지)
        if not any(isinstance(f, HanSeonFinder) for f in sys.meta_path):
            sys.meta_path.insert(0, HanSeonFinder())

    def _format_error(self, error, filepath, py_source):
        """에러 메시지 한선어 형식"""
        tb = traceback.extract_tb(error.__traceback__)
        print(f"\n한선어 오류 ━━━━━━━━━━━━━━━━━━━")
        print(f"  파일: {filepath}")
        for frame in tb:
            if frame.filename == filepath:
                # 원본 줄 번호 추정 (헤더 4줄 빼기)
                hsn_line = max(1, frame.lineno - 4)
                print(f"  줄 {hsn_line}: {frame.line}")
        print(f"  오류: {type(error).__name__}: {error}")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


# ═══════════════════════════════════════════════════════
# 셀프테스트
# ═══════════════════════════════════════════════════════

def self_test():
    """한선어 인터프리터 셀프테스트"""
    tp = HanSeonTranspiler()
    passed = 0
    total = 0

    def check(name, hsn, expected):
        nonlocal passed, total
        total += 1
        result = tp._transpile_line(hsn, 0).strip()
        if result == expected.strip():
            passed += 1
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name}")
            print(f"     입력: {hsn}")
            print(f"     기대: {expected.strip()}")
            print(f"     결과: {result}")

    print(f"한선어 인터프리터 v{VERSION} 셀프테스트")
    print("=" * 40)

    # 가져오기
    check("가져오기", "가져오기 json, time, os", "import json, time, os")
    check("~에서 가져오기", "http.server에서 가져오기 HTTPServer, BaseHTTPRequestHandler",
          "from http.server import HTTPServer, BaseHTTPRequestHandler")

    # 함수/클래스
    check("함수 정의", "함수 처리(자기, 요청):", "def 처리(self, 요청):")
    check("클래스 정의", "클래스 서버(기본서버):", "class 서버(기본서버):")
    check("반환", "    반환 결과", "    return 결과")

    # 제어 흐름
    check("만약", "만약 x > 0:", "if x > 0:")
    check("아니면만약", "아니면만약 x == 0:", "elif x == 0:")
    check("아니면", "아니면:", "else:")
    check("각각", "각각 항목 안에 목록:", "for 항목 in 목록:")
    check("동안", "동안 참:", "while True:")

    # 논리
    check("그리고/또는", "만약 a > 0 그리고 b < 10:", "if a > 0 and b < 10:")
    check("참/거짓/없음", "x = 참", "x = True")
    check("없음", "만약 x 없음이면:", "if x is None:")

    # 내장함수
    check("출력", "출력(\"안녕\")", "print(\"안녕\")")
    check("길이", "n = 길이(자료)", "n = len(자료)")
    check("범위", "각각 i 안에 범위(10):", "for i in range(10):")

    # 예외
    check("시도/예외", "시도:", "try:")
    check("예외", "예외 Exception:", "except Exception:")

    # 자기 → self
    check("자기", "자기.값 = 0", "self.값 = 0")

    # 주석
    check("주석 //", "// 이것은 주석", "# 이것은 주석")
    check("주석 ※", "※ 참고사항", "# 참고사항")

    # 문자열 보호
    check("문자열 보호", '출력("만약 참이면")', 'print("만약 참이면")')

    # 전달
    check("전달", "    전달", "    pass")

    print(f"\n결과: {passed}/{total} 통과")
    return passed == total


# ═══════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print(f"""
한선어 인터프리터 v{VERSION}
  사용법:
    python3 hanseon.py <파일.hsn>         실행
    python3 hanseon.py <파일.hsn> --변환   Python으로 변환
    python3 hanseon.py --자가검사          셀프테스트
""")
        return

    arg = sys.argv[1]

    if arg in ("--자가검사", "--test", "--셀프테스트"):
        ok = self_test()
        sys.exit(0 if ok else 1)

    filepath = arg

    if not os.path.exists(filepath):
        print(f"한선어 오류: 파일 없음 — {filepath}")
        sys.exit(1)

    if "--변환" in sys.argv or "--transpile" in sys.argv:
        # 변환만
        tp = HanSeonTranspiler()
        print(tp.transpile_file(filepath))
    else:
        # 실행
        rt = HanSeonRuntime()
        rt.run_file(filepath, [filepath] + sys.argv[2:])


if __name__ == "__main__":
    main()
