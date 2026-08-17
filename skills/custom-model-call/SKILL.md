---
name: custom-model-call
description: Call a model provider that is not in the built-in vendor catalog. Use whenever the user wants to use a model service not supported out of the box (custom api base / api key / model), or supplies a vendor-specific endpoint, and wants the generated result saved into the outputs directory.
license: MIT
---

# Custom Model Call

## When to use

Use when the requested model service is not covered by the built-in provider
catalog (see `provider-catalog.ts` built-in vendors). Typical cases: a private
gateway, a newly launched vendor, a self-hosted endpoint, or any provider whose
api base is not among the built-in defaults.

Do **not** use it when the provider already exists in the built-in catalog —
use the built-in path instead.

## Workflow

### 1. Collect the three values

Ask the user, one at a time, for:

- **API base** — base URL as given, e.g. `https://api.example.com/v1`.
- **API key** — treat as a secret: pass via CLI argument or environment
  variable, never write it into any file.
- **Model name** — the exact model id the provider expects.

Never guess these values. If any is missing, keep asking.

### 2. Run the script

From the workspace root:

```bash
python "skills/custom-model-call/scripts/call_model.py" \
  --api-base "<API base>" \
  --api-key "<API key>" \
  --model "<model name>" \
  --prompt "<user prompt>" \
  [--system "<system instructions>"] \
  [--out "outputs/<name>.md"]
```

- Flags also read from env vars `MODEL_API_BASE`, `MODEL_API_KEY`, `MODEL_NAME`
  when omitted.
- Default output is `outputs/model-result-<timestamp>.md` — always inside the
  workspace `outputs/` directory, matching app conventions.
- When the vendor is **not** OpenAI-compatible (vendor-specific request shape),
  extend `call_model.py` with a provider adapter (see the `PROVIDER_ADAPTERS`
  registry in the script) rather than hand-rolling a new script each time.

### 3. Report

- State the saved file's relative path.
- On failure, print the provider's error message verbatim (HTTP status + body);
  likely causes: wrong api base, invalid/expired api key, unknown model name.
  Ask the user to correct the corresponding value and retry.
