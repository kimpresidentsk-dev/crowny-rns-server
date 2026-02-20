#!/usr/bin/env python3
"""진입점 — 한글 파일명 호환"""
import os, glob, sys

os.environ.setdefault("LANG", "C.UTF-8")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# .hsn 서버 파일 찾기
hsn_files = glob.glob("*.hsn")
server_file = None
for f in hsn_files:
    if "서버" in f or "server" in f:
        server_file = f
        break

if not server_file and hsn_files:
    # 가장 큰 .hsn 파일이 서버
    server_file = max(hsn_files, key=os.path.getsize)

if server_file:
    print(f"한선어 서버 시작: {server_file}")
    from hanseon import HanSeonRuntime
    rt = HanSeonRuntime()
    rt.run_file(server_file)
else:
    print("오류: .hsn 파일을 찾을 수 없습니다")
    print(f"현재 디렉토리: {os.getcwd()}")
    print(f"파일 목록: {os.listdir('.')}")
    sys.exit(1)
