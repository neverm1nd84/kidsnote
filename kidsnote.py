#!/usr/bin/env python3
"""키즈노트 로그인 후 공지(알림장 제외) 가져오기.

환경변수 KIDSNOTE_ID / KIDSNOTE_PW 사용. 표준 라이브러리만 사용.
사용법: python3 kidsnote.py [--limit N] [--json]
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

BASE = "https://www.kidsnote.com"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def login():
    user, pw = os.environ.get("KIDSNOTE_ID"), os.environ.get("KIDSNOTE_PW")
    if not user or not pw:
        sys.exit("KIDSNOTE_ID / KIDSNOTE_PW 환경변수가 필요합니다.")
    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.open(f"{BASE}/kr/login").read()  # 초기 쿠키
    data = urllib.parse.urlencode({"username": user, "password": pw}).encode()
    no_redirect = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar), NoRedirect
    )
    try:
        no_redirect.open(urllib.request.Request(f"{BASE}/kr/login", data=data))
    except urllib.error.HTTPError as e:
        if e.code not in (301, 302, 303, 307, 308):
            sys.exit(f"로그인 실패: HTTP {e.code}")
    if not any(c.name == "sessionid" for c in jar):
        sys.exit("로그인 실패: 세션 쿠키 없음 (아이디/비밀번호 확인, 2단계 인증 여부)")
    return opener


def get(opener, path):
    with opener.open(f"{BASE}/api/v1/{path}") as r:
        return json.load(r)


def fetch_notices(opener, limit=20):
    """원 공지 + 반 공지를 합친 notices/ 엔드포인트를 최신순으로 가져온다."""
    size = min(limit, 50)
    notices, page_no = [], 1
    while len(notices) < limit and page_no:
        page = get(opener, f"notices/?page_size={size}&page={page_no}")
        notices.extend(page["results"])
        page_no = page.get("next")  # 다음 페이지 번호, 없으면 None
    return notices[:limit]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    notices = fetch_notices(login(), args.limit)
    if args.json:
        json.dump(notices, sys.stdout, ensure_ascii=False, indent=2)
        return
    for n in notices:
        scope = n.get("class_name") or "전체"
        print(f"[{n['created'][:10]}] {n['title']} ({scope}, {n['author_name']})")
        print(f"  {n['content'].strip()[:200]}")
        for f in n.get("attached_files", []):
            print(f"  첨부: {f.get('original_file_name')}")


if __name__ == "__main__":
    main()
