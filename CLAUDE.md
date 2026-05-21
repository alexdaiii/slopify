# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A collection of [`sbx`](https://docs.anthropic.com/) sandbox **kits** that configure OpenCode (Go) inside a Docker microVM. There is no application code, build step, or test suite — the repo is YAML + JSON + a small tree of files dropped into the sandbox at runtime. Changes are validated by running the kit, not by a CI build.

## Layout

```
opencode/
  base/          # OpenCode Go auth + PyCharm MCP + DeepWiki MCP
  paper_search/  # base + Semantic Scholar (AllenAI) MCP
  playwright/    # base + Playwright local MCP
claude/          # reserved (empty) — future Claude Code kits
```

Each kit directory has two parts:

- `spec.yaml` — the kit manifest (`kind: mixin`). Defines proxy network allowlist, credential sources, env vars, and the `opencode.json` config that gets written into the sandbox via `commands.initFiles`.
- `files/...` — a tree that mirrors the in-sandbox filesystem. The path `files/home/.config/opencode/agents/general-lite.md` lands at `/home/agent/.config/opencode/agents/general-lite.md` in the running sandbox.

The three kits are near-duplicates. They differ only in (a) the MCP server list inside the embedded `opencode.json` and (b) sometimes the `allowedDomains` / `credentials` they require. When changing shared behavior, change all three.

## How a kit gets used

```bash
# Local
sbx run --kit ./opencode/base opencode

# From GitHub (any kit dir)
sbx run --kit "git+https://github.com/alexdaiii/opencode-sbx-kit.git#ref=main&dir=opencode/base" opencode
```

Before first use, host-side secrets must be set so the proxy can inject auth:

```bash
sbx secret set -g opencode   # required for all kits
sbx secret set -g allenai    # required for paper_search
```

Inside the sandbox, `OPENCODE_API_KEY` and `ALLEN_AI_KEY` literally read as the string `proxy-managed` — this is expected. The real values live on the host and are injected by the proxy as HTTP headers (`Authorization: Bearer …`, `x-api-key: …`) on requests to the matching `serviceDomains`.

## Editing conventions

- **`opencode.json` is embedded as YAML literal block** inside `spec.yaml` under `commands.initFiles[].content`. It must be valid JSON. Mind trailing commas — they break the in-sandbox config silently.
- **Adding a new MCP server**: edit the `mcp:` block inside the embedded JSON. If it needs network access, add the host to `network.allowedDomains` and (if it needs auth) wire `serviceDomains` → `serviceAuth` → `credentials.sources` and list any in-sandbox env var under `environment.proxyManaged`.
- **Adding a new kit**: copy a sibling directory under `opencode/`, edit `spec.yaml`, and place any sandbox-side files under `files/<absolute path>`. Then update the README's kit list.
- **Subagent definitions** live in `files/home/.config/opencode/agents/`. They're plain markdown with YAML frontmatter (`mode`, `model`, `permission`). The current `general-lite.md` is identical across all three kits — keep it in sync if you change one.

## Model defaults

Each kit pins `model: opencode-go/kimi-k2.6` and `small_model: opencode-go/deepseek-v4-flash` in the embedded `opencode.json`. The `general-lite` subagent uses the small model.
