#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Container, Horizontal
    from textual.screen import ModalScreen
    from textual.widgets import Button, Footer, Header, Input, Label, RadioButton, RadioSet, Static
except ImportError:
    App = None


ToolName = Literal["claude", "codex"]

APP_NAME = "ai-login-switcher"

IS_WINDOWS = platform.system().lower() == "windows"
IS_LINUX = platform.system().lower() == "linux"

HOME = Path.home()

BASE_DIR = HOME / ".ai-login-switcher"
PROFILES_DIR = BASE_DIR / "profiles"
EMPTY_DIR = BASE_DIR / "empty"
STATE_FILE = BASE_DIR / "state.json"

CLAUDE_TARGET = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(HOME / ".claude")))
CODEX_TARGET = Path(os.environ.get("CODEX_HOME", str(HOME / ".codex")))

TOOL_TARGETS: dict[ToolName, Path] = {
    "claude": CLAUDE_TARGET,
    "codex": CODEX_TARGET,
}


@dataclass
class ToolIdentity:
    email: str = ""
    workspace: str = ""
    auth_mode: str = ""
    logged_in: str = "unknown"
    raw_status: str = ""


@dataclass
class ProfileMeta:
    id: str
    custom_name: str = ""
    notes: str = ""
    claude: ToolIdentity = field(default_factory=ToolIdentity)
    codex: ToolIdentity = field(default_factory=ToolIdentity)

    @property
    def label(self) -> str:
        return self.custom_name or self.id


def fail(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def ensure_supported_os() -> None:
    if not (IS_WINDOWS or IS_LINUX):
        fail("This tool is intended for Windows and Linux only.")


def ensure_dirs() -> None:
    BASE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    PROFILES_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    EMPTY_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    (EMPTY_DIR / "claude").mkdir(mode=0o700, parents=True, exist_ok=True)
    (EMPTY_DIR / "codex").mkdir(mode=0o700, parents=True, exist_ok=True)
    private_chmod(BASE_DIR)


def private_chmod(path: Path) -> None:
    if IS_WINDOWS:
        return

    try:
        if path.is_symlink():
            return
        if path.is_dir():
            path.chmod(0o700)
            for child in path.rglob("*"):
                try:
                    if child.is_symlink():
                        continue
                    child.chmod(0o700 if child.is_dir() else 0o600)
                except OSError:
                    pass
        elif path.exists():
            path.chmod(0o600)
    except OSError:
        pass


def validate_profile_id(profile_id: str) -> None:
    if not profile_id or profile_id in {".", "..", "empty"}:
        raise ValueError("Invalid profile id")
    if "/" in profile_id or "\\" in profile_id:
        raise ValueError("Profile id must not contain path separators")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", profile_id):
        raise ValueError("Profile id may only contain letters, numbers, dot, underscore, and dash")


def profile_dir(profile_id: str) -> Path:
    validate_profile_id(profile_id)
    return PROFILES_DIR / profile_id


def profile_tool_dir(profile_id: str, tool: ToolName) -> Path:
    if profile_id == "empty":
        return EMPTY_DIR / tool
    return profile_dir(profile_id) / tool


def meta_path(profile_id: str) -> Path:
    return profile_dir(profile_id) / "meta.json"


def identity_from_dict(value: Any) -> ToolIdentity:
    if not isinstance(value, dict):
        return ToolIdentity()
    return ToolIdentity(
        email=str(value.get("email", "") or ""),
        workspace=str(value.get("workspace", "") or ""),
        auth_mode=str(value.get("auth_mode", "") or ""),
        logged_in=str(value.get("logged_in", "unknown") or "unknown"),
        raw_status=str(value.get("raw_status", "") or ""),
    )


def load_meta(profile_id: str) -> ProfileMeta:
    path = meta_path(profile_id)
    if not path.exists():
        return ProfileMeta(id=profile_id, custom_name=profile_id)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ProfileMeta(id=profile_id, custom_name=profile_id)

    return ProfileMeta(
        id=str(data.get("id", profile_id) or profile_id),
        custom_name=str(data.get("custom_name", "") or ""),
        notes=str(data.get("notes", "") or ""),
        claude=identity_from_dict(data.get("claude")),
        codex=identity_from_dict(data.get("codex")),
    )


def save_meta(meta: ProfileMeta) -> None:
    pdir = profile_dir(meta.id)
    pdir.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = meta_path(meta.id)
    path.write_text(json.dumps(asdict(meta), indent=2), encoding="utf-8")
    private_chmod(path)


def load_state() -> dict[str, Any]:
    ensure_dirs()
    if not STATE_FILE.exists():
        return {"active": {"claude": "empty", "codex": "empty"}}

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {}

    data.setdefault("active", {})
    data["active"].setdefault("claude", "empty")
    data["active"].setdefault("codex", "empty")
    return data


def save_state(state: dict[str, Any]) -> None:
    ensure_dirs()
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    private_chmod(STATE_FILE)


def list_profile_ids() -> list[str]:
    ensure_dirs()
    return sorted(p.name for p in PROFILES_DIR.iterdir() if p.is_dir())


def list_metas() -> list[ProfileMeta]:
    return [load_meta(pid) for pid in list_profile_ids()]


def init_profile(profile_id: str) -> None:
    ensure_dirs()
    validate_profile_id(profile_id)

    pdir = profile_dir(profile_id)
    pdir.mkdir(mode=0o700, parents=True, exist_ok=True)
    (pdir / "claude").mkdir(mode=0o700, parents=True, exist_ok=True)
    (pdir / "codex").mkdir(mode=0o700, parents=True, exist_ok=True)

    if not meta_path(profile_id).exists():
        save_meta(ProfileMeta(id=profile_id, custom_name=profile_id))

    private_chmod(pdir)


def _rmtree_onerror(func: Any, path: str, exc_info: Any) -> None:
    """Retry Windows deletes after making files writable."""
    try:
        os.chmod(path, 0o700)
        func(path)
    except OSError:
        raise exc_info[1]


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path, onerror=_rmtree_onerror)


def copytree_clean(src: Path, dst: Path) -> None:
    if dst.exists() or dst.is_symlink():
        remove_path(dst)
    shutil.copytree(src, dst)


def link_or_copy_dir(src: Path, dst: Path) -> str:
    if dst.exists() or dst.is_symlink():
        try:
            remove_path(dst)
        except OSError as exc:
            fail(
                f"Could not replace {dst}: {exc}\n"
                "Close Claude/Codex and any terminals using that folder, then retry. "
                "On Windows this often happens when Codex plugin cache files are locked."
            )

    dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        os.symlink(src, dst, target_is_directory=True)
        mode = "symlink"
    except OSError:
        shutil.copytree(src, dst)
        mode = "copy"

    private_chmod(dst)
    return mode


def current_switch_mode(tool: ToolName) -> str:
    target = TOOL_TARGETS[tool]
    if target.is_symlink():
        return "symlink"
    if target.exists():
        return "copy-or-real-directory"
    return "missing"


def run_cli(command: list[str], extra_env: dict[str, str] | None = None) -> tuple[int, str, str]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"Command not found: {command[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"Command timed out: {' '.join(command)}"


def try_load_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def deep_find_first(obj: Any, keys: set[str]) -> str:
    if isinstance(obj, dict):
        for key, value in obj.items():
            normalized = key.lower().replace("_", "").replace("-", "").replace(" ", "")
            if normalized in keys and isinstance(value, (str, int, float, bool)):
                return str(value)

        for value in obj.values():
            found = deep_find_first(value, keys)
            if found:
                return found

    if isinstance(obj, list):
        for item in obj:
            found = deep_find_first(item, keys)
            if found:
                return found

    return ""


def extract_email_from_text(text: str) -> str:
    match = re.search(r"[\w.\-+%]+@[\w.\-]+\.[A-Za-z]{2,}", text or "")
    return match.group(0) if match else ""


def extract_labeled_value(text: str, labels: list[str]) -> str:
    for label in labels:
        pattern = rf"{re.escape(label)}\s*[:=]\s*(.+)"
        match = re.search(pattern, text or "", flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            value = re.sub(r"\s{2,}.*$", "", value)
            return value
    return ""


def detect_auth_mode_from_text(text: str, exit_code: int) -> str:
    low = (text or "").lower()

    if "not logged" in low or "not authenticated" in low:
        return "not logged in"
    if "api key" in low or "apikey" in low:
        return "api key"
    if "chatgpt" in low:
        return "chatgpt"
    if "subscription" in low:
        return "subscription"
    if "oauth" in low:
        return "oauth"
    if "logged in" in low or "authenticated" in low or exit_code == 0:
        return "logged in"
    return ""


def discover_claude_identity() -> ToolIdentity:
    code, stdout, stderr = run_cli(["claude", "auth", "status"])
    combined = "\n".join(x for x in [stdout, stderr] if x)

    identity = ToolIdentity(
        logged_in="true" if code == 0 else "false",
        raw_status=combined[:4000],
    )

    data = try_load_json(stdout)
    if data:
        identity.email = deep_find_first(data, {"email", "emailaddress", "username", "useremail", "accountemail"})
        identity.workspace = deep_find_first(data, {"workspace", "workspacename", "organization", "organizationname", "org", "team", "teamname", "account"})
        identity.auth_mode = deep_find_first(data, {"authmode", "mode", "provider", "type", "loginmethod", "method"})
        return identity

    code2, stdout2, stderr2 = run_cli(["claude", "auth", "status", "--text"])
    combined2 = "\n".join(x for x in [stdout2, stderr2] if x)

    if combined2:
        identity.logged_in = "true" if code2 == 0 else identity.logged_in
        identity.raw_status = combined2[:4000]
        identity.email = extract_email_from_text(combined2)
        identity.workspace = extract_labeled_value(combined2, ["workspace", "organization", "org", "team", "account"])
        identity.auth_mode = detect_auth_mode_from_text(combined2, code2)
    else:
        identity.email = extract_email_from_text(combined)
        identity.workspace = extract_labeled_value(combined, ["workspace", "organization", "org", "team", "account"])
        identity.auth_mode = detect_auth_mode_from_text(combined, code)

    return identity


def discover_codex_identity() -> ToolIdentity:
    code, stdout, stderr = run_cli(["codex", "login", "status"])
    combined = "\n".join(x for x in [stdout, stderr] if x)

    identity = ToolIdentity(
        logged_in="true" if code == 0 else "false",
        raw_status=combined[:4000],
    )

    data = try_load_json(stdout)
    if data:
        identity.email = deep_find_first(data, {"email", "emailaddress", "username", "useremail", "accountemail"})
        identity.workspace = deep_find_first(data, {"workspace", "workspacename", "organization", "organizationname", "org", "team", "teamname", "account"})
        identity.auth_mode = deep_find_first(data, {"authmode", "mode", "provider", "type", "loginmethod", "method"})
        return identity

    identity.email = extract_email_from_text(combined)
    identity.workspace = extract_labeled_value(combined, ["workspace", "organization", "org", "team", "account"])
    identity.auth_mode = detect_auth_mode_from_text(combined, code)

    return identity


def refresh_profile_identity(tool: ToolName, profile_id: str) -> ToolIdentity:
    if profile_id == "empty":
        return ToolIdentity(logged_in="false", auth_mode="empty")

    meta = load_meta(profile_id)

    if tool == "claude":
        identity = discover_claude_identity()
        meta.claude = identity
    else:
        identity = discover_codex_identity()
        meta.codex = identity

    save_meta(meta)
    return identity


def switch_tool(tool: ToolName, profile_id: str, refresh: bool = True) -> None:
    ensure_dirs()

    if profile_id != "empty" and not profile_dir(profile_id).exists():
        fail(f"Profile does not exist: {profile_id}")

    src = profile_tool_dir(profile_id, tool)
    src.mkdir(mode=0o700, parents=True, exist_ok=True)

    target = TOOL_TARGETS[tool]
    mode = link_or_copy_dir(src, target)

    state = load_state()
    state.setdefault("active", {})
    state["active"][tool] = profile_id
    state.setdefault("switch_mode", {})
    state["switch_mode"][tool] = mode
    save_state(state)

    if refresh and profile_id != "empty":
        refresh_profile_identity(tool, profile_id)


def capture_tool(tool: ToolName, profile_id: str) -> None:
    ensure_dirs()
    init_profile(profile_id)

    target = TOOL_TARGETS[tool]
    dest = profile_tool_dir(profile_id, tool)

    if not target.exists() and not target.is_symlink():
        fail(f"Nothing to capture; target does not exist: {target}")

    if dest.exists() or dest.is_symlink():
        remove_path(dest)

    if target.is_symlink():
        real = target.resolve()
        if not real.exists():
            fail(f"Target symlink is broken: {target}")
        shutil.copytree(real, dest)
    elif target.is_dir():
        shutil.copytree(target, dest)
    else:
        fail(f"Expected directory for {tool}: {target}")

    private_chmod(dest)

    switch_tool(tool, profile_id, refresh=True)


def read_json_file(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def claude_credentials_file(root: Path) -> Path | None:
    for name in (".credentials.json", "credentials.json"):
        path = root / name
        if path.is_file():
            return path
    return None


def codex_credentials_file(root: Path) -> Path | None:
    for name in ("auth.json", "credentials.json"):
        path = root / name
        if path.is_file():
            return path
    return None


def has_valid_credentials(tool: ToolName, root: Path) -> bool:
    """Return whether a tool home contains a plausibly usable credentials file."""
    if tool == "claude":
        path = claude_credentials_file(root)
        data = read_json_file(path) if path else None
        if not data:
            return False
        return bool(
            data.get("claudeAiOauth")
            or data.get("oauthAccount")
            or data.get("primaryApiKey")
            or data.get("apiKey")
        )

    path = codex_credentials_file(root)
    data = read_json_file(path) if path else None
    if not data:
        return False
    return bool(
        data.get("OPENAI_API_KEY")
        or data.get("openai_api_key")
        or data.get("api_key")
        or data.get("tokens")
        or data.get("id_token")
        or data.get("access_token")
    )


def credential_status_for_root(tool: ToolName, root: Path) -> str:
    if tool == "claude":
        path = claude_credentials_file(root)
        if not path:
            return "no credentials file"
        return f"valid credentials ({path.name})" if has_valid_credentials(tool, root) else f"invalid credentials ({path.name})"

    if tool == "codex":
        path = codex_credentials_file(root)
        if not path:
            return "no Codex credentials file"
        return f"valid Codex credentials ({path.name})" if has_valid_credentials(tool, root) else f"invalid Codex credentials ({path.name})"

    return "unknown"


def credential_status(tool: ToolName, profile_id: str) -> str:
    if profile_id == "empty":
        return "empty credentials"
    return credential_status_for_root(tool, profile_tool_dir(profile_id, tool))


def auto_import_existing_credentials() -> None:
    """Save existing tool homes as first credentials so first run starts useful."""
    ensure_dirs()
    state = load_state()
    changed = False

    for tool in ["claude", "codex"]:
        target = TOOL_TARGETS[tool]
        if not has_valid_credentials(tool, target):
            continue

        has_saved = any(has_valid_credentials(tool, profile_tool_dir(meta.id, tool)) for meta in list_metas())
        if has_saved:
            continue

        profile_id = f"{tool}-default"
        init_profile(profile_id)
        dest = profile_tool_dir(profile_id, tool)
        if dest.exists() or dest.is_symlink():
            remove_path(dest)
        if target.is_symlink():
            real = target.resolve()
            shutil.copytree(real, dest)
        else:
            shutil.copytree(target, dest)
        private_chmod(dest)
        state.setdefault("active", {})[tool] = profile_id
        changed = True

    if changed:
        save_state(state)


def status_summary(identity: ToolIdentity) -> str:
    raw = identity.raw_status or ""
    data = try_load_json(raw)
    parts: list[str] = []
    if data:
        for label, keys in [
            ("model", {"model", "displayname", "modelid", "id"}),
            ("context", {"usedpercentage", "contextusedpercent", "contextpercentage"}),
            ("input", {"totalinputtokens", "inputtokens"}),
            ("output", {"totaloutputtokens", "outputtokens"}),
            ("cost", {"totalcostusd", "costusd", "cost"}),
            ("limit", {"usedpercentage", "percentused"}),
        ]:
            value = deep_find_first(data, keys)
            if value:
                parts.append(f"{label}: {value}")
    else:
        for label in ["model", "context", "tokens", "cost", "rate limit", "usage"]:
            value = extract_labeled_value(raw, [label])
            if value:
                parts.append(f"{label}: {value}")
    return " | ".join(parts) if parts else (raw[:240] if raw else "No status available; run refresh after logging in.")


def identity_for(meta: ProfileMeta, tool: ToolName) -> ToolIdentity:
    return meta.claude if tool == "claude" else meta.codex


def print_status() -> None:
    ensure_dirs()
    auto_import_existing_credentials()
    state = load_state()
    active = state.get("active", {})
    claude_id = active.get("claude", "empty")
    codex_id = active.get("codex", "empty")

    print("Active contexts")
    print("================")
    print_context_line("claude", claude_id)
    print()
    print_context_line("codex", codex_id)


def print_context_line(tool: ToolName, profile_id: str) -> None:
    target = TOOL_TARGETS[tool]

    if profile_id == "empty":
        print(f"{tool.capitalize()}: empty credentials")
        print(f"  Target: {target}")
        print(f"  Switch mode: {current_switch_mode(tool)}")
        return

    meta = load_meta(profile_id)
    ident = identity_for(meta, tool)

    print(f"{tool.capitalize()}: {profile_id} - {meta.label}")
    print(f"  Email: {ident.email or 'unknown'}")
    print(f"  Workspace: {ident.workspace or 'unknown'}")
    print(f"  Auth mode: {ident.auth_mode or 'unknown'}")
    print(f"  Logged in: {ident.logged_in}")
    print(f"  Credential status: {credential_status(tool, profile_id)}")
    print(f"  Target: {target}")
    print(f"  Switch mode: {current_switch_mode(tool)}")


def edit_profile_cli(profile_id: str) -> None:
    init_profile(profile_id)
    meta = load_meta(profile_id)

    print("Leave blank to keep existing value.")
    custom_name = input(f"Custom name [{meta.custom_name}]: ").strip()
    notes = input(f"Notes [{meta.notes}]: ").strip()

    if custom_name:
        meta.custom_name = custom_name
    if notes:
        meta.notes = notes

    save_meta(meta)
    print(f"Updated profile: {profile_id}")


def print_profiles() -> None:
    auto_import_existing_credentials()
    state = load_state()
    active = state.get("active", {})

    print("Profiles")
    print("========")
    for meta in list_metas():
        claude_marker = "C" if active.get("claude") == meta.id else " "
        codex_marker = "X" if active.get("codex") == meta.id else " "

        print(f"[{claude_marker}{codex_marker}] {meta.id} - {meta.label}")
        print(f"     Claude: {meta.claude.email or 'unknown'} / {meta.claude.workspace or 'unknown'} / {meta.claude.auth_mode or 'unknown'}")
        print(f"     Codex:  {meta.codex.email or 'unknown'} / {meta.codex.workspace or 'unknown'} / {meta.codex.auth_mode or 'unknown'}")


if App is not None:

    class EditMetaScreen(ModalScreen[ProfileMeta | None]):
        def __init__(self, meta: ProfileMeta):
            super().__init__()
            self.meta = meta

        def compose(self) -> ComposeResult:
            yield Container(
                Label(f"Edit profile metadata: {self.meta.id}"),
                Input(value=self.meta.custom_name, placeholder="Custom name", id="custom_name"),
                Input(value=self.meta.notes, placeholder="Notes", id="notes"),
                Horizontal(
                    Button("Save", id="save", variant="success"),
                    Button("Cancel", id="cancel"),
                ),
                id="edit-dialog",
            )

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "cancel":
                self.dismiss(None)
                return

            self.meta.custom_name = self.query_one("#custom_name", Input).value.strip()
            self.meta.notes = self.query_one("#notes", Input).value.strip()
            self.dismiss(self.meta)


    class NewProfileScreen(ModalScreen[str | None]):
        def compose(self) -> ComposeResult:
            yield Container(
                Label("Create new profile"),
                Input(placeholder="profile id, e.g. work-main", id="profile_id"),
                Horizontal(
                    Button("Create", id="create", variant="success"),
                    Button("Cancel", id="cancel"),
                ),
                id="edit-dialog",
            )

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "cancel":
                self.dismiss(None)
                return

            value = self.query_one("#profile_id", Input).value.strip()
            self.dismiss(value or None)


    class LoginSwitcherApp(App):
        CSS = """
        #root { padding: 1 2; }
        #active { border: solid $accent; padding: 1 2; margin-bottom: 1; height: auto; }
        #buttons { height: auto; margin-top: 1; }
        #tool_columns { height: 1fr; }
        #claude_column, #codex_column { width: 1fr; padding: 0 1; }
        Button { margin-right: 1; margin-bottom: 1; }
        RadioSet { height: 1fr; border: solid $primary; padding: 1; }
        #status { border: solid $accent; padding: 1 2; margin-top: 1; height: auto; }
        #edit-dialog { width: 80; height: auto; border: thick $accent; background: $surface; padding: 1 2; }
        """

        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("r", "refresh_table", "Refresh"),
            Binding("s", "switch_selected", "Select active"),
            Binding("a", "add_login", "Add/login"),
            Binding("d", "remove_selected", "Remove"),
            Binding("f", "refresh_identity", "Fetch status"),
        ]

        current_tool: ToolName = "claude"

        def compose(self) -> ComposeResult:
            yield Header()
            yield Container(
                Static(id="active"),
                Horizontal(
                    Container(Label("Claude credentials"), RadioSet(id="claude_profiles"), id="claude_column"),
                    Container(Label("Codex credentials"), RadioSet(id="codex_profiles"), id="codex_column"),
                    id="tool_columns",
                ),
                Static(id="status"),
                Horizontal(
                    Button("Set active", id="switch_selected", variant="primary"),
                    Button("Add new/login", id="add_login", variant="success"),
                    Button("Remove", id="remove_selected", variant="error"),
                    Button("Fetch status", id="refresh_identity"),
                    id="buttons",
                ),
                id="root",
            )
            yield Footer()

        def on_mount(self) -> None:
            self.refresh_all()

        def refresh_all(self) -> None:
            self.refresh_active_panel()
            self.refresh_radio_lists()
            self.refresh_status_panel()

        def profile_label(self, meta: ProfileMeta, tool: ToolName) -> str:
            ident = identity_for(meta, tool)
            email = ident.email or "unknown email"
            workspace = ident.workspace or "unknown workspace"
            return f"{email} | {workspace} ({meta.id})"

        def refresh_active_panel(self) -> None:
            state = load_state()
            active = state.get("active", {})
            lines = ["Select a credential set under Claude or Codex, then choose an action. Save each Claude or Codex login once, then switch that tool between saved credentials."]
            for tool in ["claude", "codex"]:
                pid = active.get(tool, "empty")
                lines.append(f"{tool.capitalize()}: {pid} | target={TOOL_TARGETS[tool]} | {credential_status(tool, pid)}")
            self.query_one("#active", Static).update("\n".join(lines))

        def refresh_radio_lists(self) -> None:
            state = load_state()
            active = state.get("active", {})
            metas = list_metas()
            for tool in ["claude", "codex"]:
                radio = self.query_one(f"#{tool}_profiles", RadioSet)
                radio.remove_children()
                empty_pressed = active.get(tool) == "empty"
                radio.mount(RadioButton("empty credentials", id=f"{tool}::empty", value=empty_pressed))
                for meta in metas:
                    pressed = active.get(tool) == meta.id
                    radio.mount(RadioButton(self.profile_label(meta, tool), id=f"{tool}::{meta.id}", value=pressed))

        def selected_profile_id(self, tool: ToolName | None = None) -> str | None:
            tool = tool or self.current_tool
            radio = self.query_one(f"#{tool}_profiles", RadioSet)
            pressed = radio.pressed_button
            if not pressed or not pressed.id:
                return None
            return pressed.id.split("::", 1)[1]

        def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
            if event.radio_set.id == "codex_profiles":
                self.current_tool = "codex"
            elif event.radio_set.id == "claude_profiles":
                self.current_tool = "claude"
            self.refresh_status_panel()

        def refresh_status_panel(self) -> None:
            state = load_state()
            pid = state.get("active", {}).get(self.current_tool, "empty")
            if pid == "empty":
                text = f"{self.current_tool.capitalize()} status: empty credentials"
            else:
                meta = load_meta(pid)
                ident = identity_for(meta, self.current_tool)
                text = f"{self.current_tool.capitalize()} active token/status\n{status_summary(ident)}"
            self.query_one("#status", Static).update(text)

        def action_refresh_table(self) -> None:
            self.refresh_all()

        def action_switch_selected(self) -> None:
            pid = self.selected_profile_id()
            if pid:
                switch_tool(self.current_tool, pid, refresh=True)
                self.refresh_all()

        def action_add_login(self) -> None:
            def after_new(profile_id: str | None) -> None:
                if not profile_id:
                    return
                try:
                    init_profile(profile_id)
                    switch_tool(self.current_tool, "empty", refresh=False)
                    self.notify(f"Empty {self.current_tool} credentials activated. Run login, then capture {profile_id}.")
                except Exception as exc:
                    self.notify(str(exc), severity="error")
                    return
                self.refresh_all()
            self.push_screen(NewProfileScreen(), after_new)

        def action_remove_selected(self) -> None:
            pid = self.selected_profile_id()
            if not pid or pid == "empty":
                return
            pdir = profile_dir(pid)
            if pdir.exists():
                remove_path(pdir)
            state = load_state()
            for tool in ["claude", "codex"]:
                if state.get("active", {}).get(tool) == pid:
                    state["active"][tool] = "empty"
            save_state(state)
            self.refresh_all()

        def action_refresh_identity(self) -> None:
            pid = load_state().get("active", {}).get(self.current_tool, "empty")
            if pid != "empty":
                refresh_profile_identity(self.current_tool, pid)
            self.refresh_all()

        def on_button_pressed(self, event: Button.Pressed) -> None:
            mapping = {
                "switch_selected": self.action_switch_selected,
                "add_login": self.action_add_login,
                "remove_selected": self.action_remove_selected,
                "refresh_identity": self.action_refresh_identity,
            }
            action = mapping.get(event.button.id or "")
            if action:
                action()


def run_tui() -> None:
    auto_import_existing_credentials()
    if App is None:
        fail("Textual is not installed. Install dependencies or use the packaged binary.")
    LoginSwitcherApp().run()


def main() -> None:
    ensure_supported_os()

    parser = argparse.ArgumentParser(prog=APP_NAME, description="Switch between saved Claude and Codex credentials. Use --help after any command for details.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("tui", help="open the guided terminal UI")
    sub.add_parser("status", help="show which Claude/Codex credentials are active")
    sub.add_parser("list", help="list saved credential sets")
    sub.add_parser("help", help="show this help message")

    p_init = sub.add_parser("init", help="create a saved credential set")
    p_init.add_argument("profile_id")

    p_edit = sub.add_parser("edit")
    p_edit.add_argument("profile_id")

    p_switch = sub.add_parser("switch")
    p_switch.add_argument("tool", choices=["claude", "codex"])
    p_switch.add_argument("profile_id", nargs="?")
    p_switch.add_argument("--empty", action="store_true")

    p_capture = sub.add_parser("capture", help="save the current home-folder credentials under a name")
    p_capture.add_argument("tool", choices=["claude", "codex"])
    p_capture.add_argument("profile_id")

    p_add = sub.add_parser("add", help="alias for capture: save current credentials under a name")
    p_add.add_argument("tool", choices=["claude", "codex"])
    p_add.add_argument("profile_id")

    p_refresh = sub.add_parser("refresh", help="refresh metadata for the active credentials, or a specific tool/profile")
    p_refresh.add_argument("tool", nargs="?", choices=["claude", "codex"])
    p_refresh.add_argument("profile_id", nargs="?")

    sub.add_parser("refresh-active")

    args = parser.parse_args()

    if args.cmd == "help":
        parser.print_help()
    elif args.cmd == "tui":
        run_tui()
    elif args.cmd == "status":
        print_status()
    elif args.cmd == "list":
        print_profiles()
    elif args.cmd == "init":
        init_profile(args.profile_id)
        print(f"Created profile: {args.profile_id}")
    elif args.cmd == "edit":
        edit_profile_cli(args.profile_id)
    elif args.cmd == "switch":
        profile_id = "empty" if args.empty else args.profile_id
        if not profile_id:
            fail("Provide a profile_id or use --empty")

        switch_tool(args.tool, profile_id, refresh=True)
        print_status()
    elif args.cmd in {"capture", "add"}:
        capture_tool(args.tool, args.profile_id)
        print(f"Saved {args.tool} credentials as: {args.profile_id}")
        print_status()
    elif args.cmd == "refresh":
        if args.tool and args.profile_id:
            switch_tool(args.tool, args.profile_id, refresh=False)
            refresh_profile_identity(args.tool, args.profile_id)
        elif not args.tool and not args.profile_id:
            state = load_state()
            for tool in ["claude", "codex"]:
                pid = state.get("active", {}).get(tool, "empty")
                if pid != "empty":
                    refresh_profile_identity(tool, pid)
        else:
            fail("Use either 'refresh' for active credentials or 'refresh <claude|codex> <credential-set>'.")
        print_status()
    elif args.cmd == "refresh-active":
        state = load_state()
        active = state.get("active", {})

        for tool in ["claude", "codex"]:
            pid = active.get(tool, "empty")
            if pid != "empty":
                refresh_profile_identity(tool, pid)

        print_status()


if __name__ == "__main__":
    main()
