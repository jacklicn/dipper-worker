---
name: stock
description: Fetch China A-share / HK / US quotes and finance headlines via free Tencent & Sina public APIs (GBK text; Sina needs Referer). Use for 行情、涨跌、指数、个股快照、滚动财经要闻.
metadata: {"dipper-bot":{"emoji":"📈","requires":{"bins":["python"]}}}
---

# Stock quotes & finance headlines

Use when the user asks for live/near-live market quotes, index snapshots, simple K-line context, or rolling finance news. Prefer this skill’s APIs over inventing scrapers.

**Do not use `web_fetch` for these quote endpoints** — responses are GBK (not UTF-8), and Sina requires a `Referer` header. Use `exec` with the helper script below, or equivalent Python/`curl` that decodes GBK.

## Code prefixes

| Prefix | Market |
|--------|--------|
| `sh` | Shanghai (沪) |
| `sz` | Shenzhen (深) |
| `hk` | Hong Kong |
| `us` | US |

Examples: `sh000001` 上证指数 · `sz399001` 深证成指 · `sz399006` 创业板指 · `sh000300` 沪深300 · `sh000688` 科创50 · `sh000905` 中证500 · `sh600519` 贵州茅台 · `sz000001` 平安银行.

Batch quotes: comma-separated codes, about **50** symbols max per Tencent request.

## Helper (preferred)

From a workspace that has seeded skills (or the bundled path):

```bash
python skills/stock/scripts/fetch_quote.py --tencent sh000001,sz399001,sz399006
python skills/stock/scripts/fetch_quote.py --tencent-simple sh000001
python skills/stock/scripts/fetch_quote.py --sina sh000001,sz399001
python skills/stock/scripts/fetch_quote.py --news --num 20
python skills/stock/scripts/fetch_quote.py --kline sh000001 --period day --count 120
```

If the skill lives only under the package builtins, adjust the path (e.g. read `SKILL.md` location first). Write any ad-hoc parse scripts under `outputs/`.

## 一、腾讯行情（实测可用）

### 1. 实时行情快照（主力）

```
https://qt.gtimg.cn/q=sh000001,sz399001,sz399006
```

- 参数：股票代码逗号拼接，前缀区分市场（`sh` / `sz` / `hk` / `us`），一次最多约 50 只
- 返回：GBK 文本，每只一行 `v_sh000001="字段~字段~..."`，用 `~` 分隔
- 关键字段（以指数为例；`[0]` 为市场/类型标记）：`[1]` 名称 · `[2]` 代码 · `[3]` 现价 · `[4]` 昨收 · `[5]` 今开 · `[6]` 成交量 · `[30]` 时间戳 · `[31]` 涨跌额 · `[32]` 涨跌幅 · `[33]` 最高 · `[34]` 最低 · `[36]` 成交额

### 2. 简化接口

```
https://qt.gtimg.cn/q=s_sh000001
```

只返回现价 + 涨跌幅等精简字段（代码前加 `s_`）。

### 3. K 线

```
https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh000001,day,,,320,qfq
```

- `param`：`代码,周期,起始,结束,条数,复权`（周期如 `day` / `week` / `month`；`qfq` 前复权）
- 返回 JSON，按接口字段取 OHLC

## 二、新浪财经（实测可用）

### 1. 实时行情

```
https://hq.sinajs.cn/list=sh000001,sz399001,sz399006
```

- **必须**请求头：`Referer: https://finance.sina.com.cn`，否则易 403/500
- 返回：GBK 的 `var hq_str_sh000001="名称,今开,昨收,现价,最高,最低,...时间"`（逗号分隔）

### 2. 当日要闻（滚动资讯）

```
https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&num=50&page=1
```

- `pageid=153` 财经频道 · `lid=2516` 财经-全部滚动 · `num` 条数 · `page` 页码
- JSON：`result.data[]` 含 `title`、`ctime`（Unix 秒）、`url`

## Workflow

1. Confirm symbols (map 中文名 → `sh`/`sz`… codes if needed).
2. Fetch Tencent snapshot (primary); optionally cross-check with Sina.
3. For narrative context, fetch Sina roll news (`--news`).
4. For trend color, pull a short K-line (`--kline`) — do not invent prices.
5. Summarize for the user: price, change %, range, volume/amount when present, timestamp; cite source. Keep rate low (free public APIs; learning/research use).

## Usage notes

1. Tencent and Sina **quotes** are **GBK** — decode with `gbk` (helper does this).
2. Sina quotes **require** `Referer: https://finance.sina.com.cn`.
3. Control request frequency; data is unofficial/public and for learning/research, not trading advice.
4. Prefer quoting **live tool results** over memory of earlier sessions.
