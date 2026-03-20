#!/usr/bin/env python3
"""Interactive setup wizard for academic-research-mcp Claude Desktop integration."""

import json
import os
import platform
import shutil
import sys
from pathlib import Path


def get_claude_config_path() -> Path:
    """Auto-detect Claude Desktop config path based on OS."""
    system = platform.system()
    if system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    elif system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    else:
        # Linux / other
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def print_header():
    print("=" * 60)
    print("  academic-research-mcp Setup Wizard")
    print("=" * 60)
    print()
    print("[INFO] This wizard helps you configure academic-research-mcp")
    print("       for use with Claude Desktop.")
    print()
    print("[INFO] Most features work WITHOUT any API keys.")
    print("       Translation (Papago) is the only optional feature")
    print("       that requires a free Naver API key.")
    print()


def setup_env(project_dir: Path) -> bool:
    """Ask user about Papago translation setup. Returns True if keys were set."""
    env_path = project_dir / ".env"

    print("-" * 60)
    print("[INFO] Papago Translation Setup (Optional)")
    print()
    print("       Korean translation requires a free Naver Papago API key.")
    print("       You can get one at: https://developers.naver.com")
    print()

    answer = input("Do you want to set up Papago translation now? (y/N): ").strip().lower()

    if answer in ("y", "yes"):
        client_id = input("  Naver Client ID: ").strip()
        client_secret = input("  Naver Client Secret: ").strip()

        if client_id and client_secret:
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(f"NAVER_CLIENT_ID={client_id}\n")
                f.write(f"NAVER_CLIENT_SECRET={client_secret}\n")
            print("[OK] API keys saved to .env")
            return True
        else:
            print("[!!] Empty values provided. Skipping Papago setup.")
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("# No API keys configured. Translation will be disabled.\n")
            return False
    else:
        print("[INFO] Skipping Papago setup. Translation will be disabled.")
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("# No API keys configured. Translation will be disabled.\n")
        return False


def setup_claude_config(project_dir: Path, has_env: bool):
    """Add academic-research MCP entry to Claude Desktop config."""
    print()
    print("-" * 60)
    print("[INFO] Claude Desktop Configuration")
    print()

    config_path = get_claude_config_path()
    print(f"[INFO] Detected config path: {config_path}")

    server_path = str(project_dir / "server.py")
    python_exe = sys.executable

    # Build the MCP entry
    mcp_entry = {
        "command": python_exe,
        "args": [server_path],
    }

    if has_env:
        env_path = str(project_dir / ".env")
        mcp_entry["args"].extend(["--env", env_path])

    # Load or create config
    config = {}
    if config_path.exists():
        # Backup existing config
        backup_path = config_path.with_suffix(".json.bak")
        shutil.copy2(config_path, backup_path)
        print(f"[OK] Existing config backed up to: {backup_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[!!] Could not parse existing config: {e}")
            print("[INFO] Creating new config.")
            config = {}

    # Ensure mcpServers key exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"]["academic-research"] = mcp_entry

    # Write config
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"[OK] MCP entry added to: {config_path}")


def print_success():
    print()
    print("=" * 60)
    print("[OK] Setup complete!")
    print("=" * 60)
    print()
    print("Usage examples in Claude Desktop:")
    print()
    print('  "Search for recent papers on transformer architectures"')
    print('  "Find citations for attention mechanism papers"')
    print('  "Generate BibTeX for paper ID 2301.00001"')
    print('  "Translate this abstract to Korean"')
    print()
    print("[INFO] Restart Claude Desktop to load the new MCP server.")
    print()


def main():
    print_header()

    project_dir = Path(__file__).resolve().parent

    has_env = setup_env(project_dir)
    setup_claude_config(project_dir, has_env)
    print_success()


if __name__ == "__main__":
    main()
