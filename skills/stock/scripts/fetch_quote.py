#!/usr/bin/env python3
"""Fetch Tencent/Sina market quotes (GBK) and Sina finance roll news."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

SINA_REFERER = "https://finance.sina.com.cn"

def _browser_ua() -> str:
    # Use the exact embedded-browser UA when the app injects it into the env.
    injected = os.environ.get("DIPPER_BROWSER_UA")
    if injected:
        return injected
    # Mirror the embedded browser's Chrome desktop UA format (frozen major).
    major = "150.0.7871.46"
    if sys.platform == "darwin":
        return f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{major} Safari/537.36"
    if sys.platform == "linux":
        return f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{major} Safari/537.36"
    return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{major} Safari/537.36"


UA = _browser_ua()

# Tencent full quote (~-separated). Index 0 is a market/type flag; names start at 1.
TX_FIELDS = {
    1: "name",
    2: "code",
    3: "price",
    4: "prev_close",
    5: "open",
    6: "volume",
    30: "time",
    31: "change",
    32: "change_pct",
    33: "high",
    34: "low",
    36: "amount",
}


def http_get(url: str, *, headers: dict[str, str] | None = None, encoding: str | None = "utf-8") -> str | bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, **(headers or {})},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            raw = res.read()
    except urllib.error.HTTPError as e:
        body = e.read()[:500]
        raise SystemExit(f"HTTP {e.code} for {url}: {body!r}") from e
    except urllib.error.URLError as e:
        raise SystemExit(f"Request failed for {url}: {e}") from e
    if encoding is None:
        return raw
    return raw.decode(encoding, errors="replace")


def parse_tencent(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        # v_sh000001="a~b~..." or v_s_sh000001="..."
        m = re.match(r'^v_([^=]+)="(.*)";?\s*$', line)
        if not m:
            continue
        key, payload = m.group(1), m.group(2)
        parts = payload.split("~")
        row: dict[str, Any] = {"symbol_key": key, "raw_fields": len(parts)}
        if key.startswith("s_"):
            # s_ layout: flag~name~code~price~change~change_pct~volume~amount~
            if len(parts) >= 6:
                row.update(
                    {
                        "name": parts[1],
                        "code": parts[2],
                        "price": parts[3],
                        "change": parts[4],
                        "change_pct": parts[5],
                    }
                )
            if len(parts) > 6 and parts[6] != "":
                row["volume"] = parts[6]
            if len(parts) > 7 and parts[7] != "":
                row["amount"] = parts[7]
        else:
            for idx, name in TX_FIELDS.items():
                if idx < len(parts) and parts[idx] != "":
                    row[name] = parts[idx]
        out.append(row)
    return out


def parse_sina(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r'^var hq_str_([^=]+)="(.*)";?\s*$', line)
        if not m:
            continue
        code, payload = m.group(1), m.group(2)
        if not payload:
            out.append({"code": code, "error": "empty"})
            continue
        p = payload.split(",")
        # 名称,今开,昨收,现价,最高,最低,... date, time (typical A-share)
        row: dict[str, Any] = {
            "code": code,
            "name": p[0] if len(p) > 0 else "",
            "open": p[1] if len(p) > 1 else "",
            "prev_close": p[2] if len(p) > 2 else "",
            "price": p[3] if len(p) > 3 else "",
            "high": p[4] if len(p) > 4 else "",
            "low": p[5] if len(p) > 5 else "",
        }
        if len(p) >= 32:
            row["date"] = p[30]
            row["time"] = p[31]
        elif len(p) >= 2:
            row["tail"] = p[-2:]
        out.append(row)
    return out


def fetch_tencent(codes: str, *, simple: bool = False) -> list[dict[str, Any]]:
    parts = [c.strip() for c in codes.split(",") if c.strip()]
    if not parts:
        raise SystemExit("No codes given")
    if simple:
        parts = [p if p.startswith("s_") else f"s_{p}" for p in parts]
    url = "https://qt.gtimg.cn/q=" + ",".join(parts)
    text = http_get(url, encoding="gbk")
    assert isinstance(text, str)
    return parse_tencent(text)


def fetch_sina(codes: str) -> list[dict[str, Any]]:
    parts = [c.strip() for c in codes.split(",") if c.strip()]
    if not parts:
        raise SystemExit("No codes given")
    url = "https://hq.sinajs.cn/list=" + ",".join(parts)
    text = http_get(url, headers={"Referer": SINA_REFERER}, encoding="gbk")
    assert isinstance(text, str)
    return parse_sina(text)


def fetch_news(num: int, page: int) -> list[dict[str, Any]]:
    qs = urllib.parse.urlencode(
        {"pageid": 153, "lid": 2516, "num": num, "page": page},
    )
    url = f"https://feed.mix.sina.com.cn/api/roll/get?{qs}"
    text = http_get(url, headers={"Referer": SINA_REFERER}, encoding="utf-8")
    assert isinstance(text, str)
    data = json.loads(text)
    items = (((data or {}).get("result") or {}).get("data")) or []
    out: list[dict[str, Any]] = []
    for it in items:
        out.append(
            {
                "title": it.get("title"),
                "ctime": it.get("ctime"),
                "url": it.get("url"),
            }
        )
    return out


def fetch_kline(code: str, period: str, count: int, adjust: str) -> Any:
    # param: code,period,start,end,count,adjust
    param = f"{code},{period},,,{count},{adjust}"
    qs = urllib.parse.urlencode({"param": param})
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?{qs}"
    text = http_get(url, encoding="utf-8")
    assert isinstance(text, str)
    return json.loads(text)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--tencent", metavar="CODES", help="Tencent full quotes, comma-separated")
    g.add_argument("--tencent-simple", metavar="CODES", help="Tencent s_ simple quotes")
    g.add_argument("--sina", metavar="CODES", help="Sina quotes (Referer required)")
    g.add_argument("--news", action="store_true", help="Sina finance roll headlines")
    g.add_argument("--kline", metavar="CODE", help="Tencent fq K-line for one code")
    ap.add_argument("--num", type=int, default=20, help="news page size (default 20)")
    ap.add_argument("--page", type=int, default=1, help="news page (default 1)")
    ap.add_argument("--period", default="day", help="kline period: day/week/month")
    ap.add_argument("--count", type=int, default=120, help="kline bars (default 120)")
    ap.add_argument("--adjust", default="qfq", help="kline adjust: qfq/hfq/ (default qfq)")
    args = ap.parse_args()

    if args.tencent:
        result: Any = fetch_tencent(args.tencent, simple=False)
    elif args.tencent_simple:
        result = fetch_tencent(args.tencent_simple, simple=True)
    elif args.sina:
        result = fetch_sina(args.sina)
    elif args.news:
        result = fetch_news(args.num, args.page)
    else:
        result = fetch_kline(args.kline, args.period, args.count, args.adjust)

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
