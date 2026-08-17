#!/usr/bin/env python3
"""Call a model provider and save the generated result into outputs/.

Default path is the OpenAI-compatible POST {apiBase}/chat/completions. Vendor
adapters (see PROVIDER_ADAPTERS) cover providers with a non-compatible request
shape. Pure standard library; no third-party dependencies.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def _http_post_json(url, extra_headers, payload, timeout):
    headers = {"Content-Type": "application/json", **extra_headers}
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _call_openai_compatible(api_base, api_key, model, prompt, system, timeout, max_tokens, temperature):
    url = api_base.rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    return _http_post_json(url, {"Authorization": f"Bearer {api_key}"}, payload, timeout)


# Add vendor adapters here. Each receives the same arguments and returns the
# response body as parsed JSON. Example for a hypothetical non-compatible API:
# def _call_example_vendor(api_base, api_key, model, prompt, system, timeout, max_tokens, temperature):
#     url = f"{api_base.rstrip('/')}/generate"
#     payload = {"input": prompt, "model_id": model}
#     resp = _http_post_json(url, {"X-Key": api_key}, payload, timeout)
#     return resp

PROVIDER_ADAPTERS = {
    "openai": _call_openai_compatible,  # also: deepseek, qwen, moonshot, etc.
    # "example_vendor": _call_example_vendor,
}


def _extract_text(data):
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"no choices in response: {data}")
    content = choices[0].get("message", {}).get("content")
    if content is None:
        raise RuntimeError(f"empty message content: {data}")
    if isinstance(content, str):
        return content
    if isinstance(content, list):  # multimodal text parts
        return "\n".join(
            p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"
        )
    return str(content)


def main():
    parser = argparse.ArgumentParser(description="Call a model API and save the result.")
    parser.add_argument("--api-base", help="API base URL (env: MODEL_API_BASE)")
    parser.add_argument("--api-key", help="API key (env: MODEL_API_KEY)")
    parser.add_argument("--model", help="Model name (env: MODEL_NAME)")
    parser.add_argument("--provider", default="openai", help="Provider adapter to use (default: openai)")
    parser.add_argument("--prompt", required=True, help="User prompt")
    parser.add_argument("--system", default=None, help="Optional system instruction")
    parser.add_argument("--out", default=None, help="Output path (default: outputs/model-result-<ts>.md)")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--base-dir", default=".", help="Workspace root for the default outputs path")
    args = parser.parse_args()

    api_base = args.api_base or os.environ.get("MODEL_API_BASE")
    api_key = args.api_key or os.environ.get("MODEL_API_KEY")
    model = args.model or os.environ.get("MODEL_NAME")
    missing = [n for n, v in (("api base", api_base), ("api key", api_key), ("model", model)) if not v]
    if missing:
        parser.error(f"missing required value(s): {', '.join(missing)}")

    adapter = PROVIDER_ADAPTERS.get(args.provider)
    if adapter is None:
        parser.error(f"unknown provider adapter '{args.provider}'; available: {', '.join(PROVIDER_ADAPTERS)}")

    try:
        data = adapter(api_base, api_key, model, args.prompt, args.system, args.timeout, args.max_tokens, args.temperature)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"network error: {e.reason}", file=sys.stderr)
        return 1
    except (TimeoutError, json.JSONDecodeError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    base_dir = Path(args.base_dir)
    out_path = Path(args.out) if args.out else base_dir / "outputs" / f"model-result-{int(time.time())}.md"
    if not out_path.is_absolute():
        out_path = base_dir / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    text = _extract_text(data)
    out_path.write_text(text, encoding="utf-8")
    print(f"saved: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
