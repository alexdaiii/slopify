#!/usr/bin/env python3
"""Deep-merge the kit's settings.json into ~/.claude/settings.json.

Run by sbx on every sandbox start (see commands.startup in spec.yaml).
Source of truth: this file's sibling settings.json — kit policy keys like
defaultMode, bypassPermissions, and the sbx-plugin marketplace registration.

Why merge instead of overwrite: Claude Code writes its own keys back to
~/.claude/settings.json (telemetry IDs, accepted-trust prompts, user-added
plugins). A blind overwrite would clobber them on every boot. Deep-merge
keeps everything Claude added while ensuring kit keys are always present
and current.

Conflict policy: on leaf conflicts the kit wins (kit values are policy).
On dict-vs-dict conflicts we recurse. Lists are treated as leaves and
replaced wholesale by the kit — none of the kit's keys are lists today,
but if that changes, revisit this.
"""
import json
import os

SRC = "/home/agent/.config/agents/settings.json"
DST = "/home/agent/.claude/settings.json"


def deep_merge(a: dict, b: dict) -> None:
    """Merge b into a in place. b wins on leaf conflicts."""
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            deep_merge(a[k], v)
        else:
            a[k] = v


def main() -> None:
    with open(SRC) as f:
        kit = json.load(f)

    existing: dict = {}
    if os.path.exists(DST):
        try:
            with open(DST) as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            # Corrupt or unreadable — treat as empty rather than fail boot.
            existing = {}

    deep_merge(existing, kit)

    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with open(DST, "w") as f:
        json.dump(existing, f, indent=2)


if __name__ == "__main__":
    main()
