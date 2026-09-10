import json
from collections.abc import Callable
from os import PathLike
from pathlib import Path


def write_jsonc(
        kit_path: PathLike,
        mod_fns: list[Callable[[dict], None]]
):
    base_kit = {
      "$schema": "https://opencode.ai/config.json",
      "model": "opencode-go/gpt-5.6-luna",
      "small_model": "opencode-go/deepseek-v4-flash",
      "enabled_providers": [
        "opencode-go",
        "opencode"
      ],
      "mcp": {
          "pycharm": {
            "enabled": True,
            "type": "remote",
            "url": "http://host.docker.internal:64342/sse",
            "headers": {}
          },
          "deepwiki": {
            "enabled": True,
            "type": "remote",
            "url": "https://mcp.deepwiki.com/mcp"
          }
      },
      "permission": "allow",
      "agent": {
        "flash": {
          "mode": "subagent",
          "description": "{file:~/.config/agents/flash.description.txt}",
          "model": "opencode-go/deepseek-v4-flash",
          "permission": {
            "edit": "allow",
            "bash": "allow"
          },
          "prompt": "{file:~/.config/agents/flash.prompt.md}"
        }
      }
    }

    for mod_fn in mod_fns:
        mod_fn(base_kit)


    with open(kit_path, "w") as f:
        json.dump(base_kit, f, indent=2)


def add_anthropic_api_handler(kit_spec: dict):
    kit_spec["provider"] = {
        "opencode-go": {
          "options": {
            "baseURL": "http://host.docker.internal:11434/zen/go/v1"
          }
        }
    }
    kit_spec["model"] = "opencode-go/glm-5.3-flash"
    return

def add_paper_search(kit_spec: dict):
    kit_spec["mcp"] |= {
        "semanticscholar": {
            "enabled": True,
            "type": "remote",
            "url": "https://asta-tools.allen.ai/mcp/v1",
            "headers": {
                "x-api-key": "proxy-managed"
            }
        },
        "paperclip": {
            "enabled": True,
            "type": "remote",
            "url": "https://paperclip.gxl.ai/mcp",
            "headers": {
                "X-API-Key": "proxy-managed"
            }
        }
    }


def add_playright_handler(kit_spec: dict):
    kit_spec["mcp"] |= {
        "playright": {
            "enabled": True,
            "type": "local",
            "command": ["npx", "@playwright/mcp@latest"]
        }
    }
    return


def main():
    kits = {
        "base": [],
        "base-ant": [add_anthropic_api_handler],
        "paper_search": [add_paper_search],
        "paper_search-ant": [add_anthropic_api_handler, add_paper_search],
        "playwright": [add_playright_handler],
        "playwright-ant": [add_anthropic_api_handler, add_playright_handler],
    }

    kit_base_dir = Path(__file__).parent.parent

    for kit_name, mod_fns in kits.items():
        output_dir = kit_base_dir / f"{kit_name}/files/home/.config/opencode/opencode.jsonc"
        write_jsonc(output_dir, mod_fns)



if __name__ == "__main__":
    main()
