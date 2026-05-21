# Docker Sandbox (SBX) Kits

This project provides a sandbox configuration for Claude Code/OpenCode within
a Docker environment using `sbx`. It includes pre-configured MCP servers and
authentication settings.

## Prerequisites

Before running the sandbox, you should set up your API keys. These keys are
managed by the `sbx` host and are injected into the sandbox via a proxy.
Run the following commands to set your secrets:

OpenCode Go/Zen:

``` bash
sbx secret set -g opencode
```

For AllenAI/Semantic Scholar,

```bash
sbx secret set -g allenai
```

Note: Inside the sandbox environment, if you try to inspect these environment
variables
(e.g., echo $OPENCODE_API_KEY), they will literally print as `proxy-managed`.
This is expected behavior as the actual keys are managed by the sandbox proxy
and never directly exposed to the guest microVM.

Docker sbx automatically manages Claude Code `/login`
credentials for you so you don't need to do the secret setup.

## Usage

To run the sandbox, use the following command if this kit is downloaded:

``` bash
sbx run --kit <PATH_TO_KIT_DIR>  opencode
```

If you are getting this kit from GitHub:

```bash
sbx run --kit "git+https://github.com/alexdaiii/opencode-sbx-kit.git#ref=main&dir=opencode/base" opencode
```

You can replace the directory after `&dir=` with the preferred directory.
The protocol can also be `ssh` instead of `https`.

For a Claude Code kit, swap the final agent argument from `opencode` to
`claude` and point `&dir=` at a `claude/*` directory, e.g.
`&dir=claude/base`.

## OpenCode Configuration Details

The sandbox is configured with:

Model: `opencode-go/kimi-k2.6`

### Base Kit

MCP Servers:

* PyCharm: Connected via `host.docker.internal` for local IDE integration.
* DeepWiki: Remote MCP server for code documentation.
* Environment: OPENCODE_ENABLE_EXA is enabled for web search capabilities.

### Paper Search

Adds:

* Semantic Scholar: Remote MCP server (AllenAI) for paper search.

Requires the AllenAI secret to be set before running the sandbox.

### Playwright

Adds:

* Playright: Local MCP server

## Claude Code Configuration Details

The Claude Code kits mirror the OpenCode ones but write
`/home/agent/.claude.json` with Claude Code's `mcpServers` schema instead
of OpenCode's. Claude Code login is handled by the sandbox itself (see
Prerequisites), so the kits do not wire `ANTHROPIC_API_KEY` through the
proxy.

### Base Kit (`claude/base`)

MCP Servers:

* PyCharm: SSE MCP server connected via `host.docker.internal` for local
  IDE integration.
* DeepWiki: Remote HTTP MCP server for code documentation.

### Paper Search (`claude/paper_search`)

Adds:

* Semantic Scholar: Remote HTTP MCP server (AllenAI) for paper search.

Requires the AllenAI secret to be set before running the sandbox.

### Playwright (`claude/playwright`)

Adds:

* Playwright: Local stdio MCP server (`npx @playwright/mcp@latest`).