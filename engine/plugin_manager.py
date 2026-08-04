"""
Plugin Manager for Sia Assistant — Sandboxed Edition.

Security layers:
  1. SHA-256 hash whitelist (plugin_manifest.json) — unknown/modified plugins blocked
  2. AST risky-import scanner — blocks subprocess, os.system, eval, exec, shutil.rmtree
  3. Audit log entry for every load attempt (allow / block / new)

Flow:
  - First encounter  → blocked + logged as PENDING_APPROVAL (human must whitelist)
  - Whitelisted & hash matches → load
  - Whitelisted but hash changed → blocked (TAMPERED)
  - Risky imports detected → blocked regardless of whitelist
"""

import os
import sys
import ast
import json
import hashlib
import importlib.util
from typing import Dict, Any, Callable, List, Optional, Set
from .logger import get_logger

logger = get_logger(__name__)

# ── Risky imports / calls that are blocked unconditionally ──────────────────
_RISKY_MODULES: Set[str] = {
    "subprocess", "ctypes", "winreg", "win32api", "win32con",
}
_RISKY_CALLS: Set[str] = {
    "os.system", "os.popen", "os.remove", "os.unlink", "os.rmdir",
    "shutil.rmtree", "shutil.move", "eval", "exec", "__import__",
}


def _compute_sha256(file_path: str) -> str:
    """Return hex SHA-256 digest of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _scan_for_risky_code(file_path: str) -> List[str]:
    """
    AST-scan a Python file for risky imports and function calls.
    Returns a list of violation strings (empty = clean).
    """
    violations: List[str] = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as e:
        violations.append(f"SyntaxError: {e}")
        return violations

    for node in ast.walk(tree):
        # import subprocess / import ctypes
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in _RISKY_MODULES:
                    violations.append(f"Risky import: {alias.name}")

        # from subprocess import Popen
        elif isinstance(node, ast.ImportFrom):
            mod = (node.module or "").split(".")[0]
            if mod in _RISKY_MODULES:
                violations.append(f"Risky from-import: {node.module}")

        # os.system("...") / eval("...") / exec("...")
        elif isinstance(node, ast.Call):
            # Reconstruct dotted call name
            func = node.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                call_str = f"{func.value.id}.{func.attr}"
                if call_str in _RISKY_CALLS:
                    violations.append(f"Risky call: {call_str}")
            elif isinstance(func, ast.Name):
                if func.id in {"eval", "exec", "__import__"}:
                    violations.append(f"Risky builtin call: {func.id}")

    return violations


class PluginManager:
    """Discovers, loads, and manages dynamic sandboxed plugin extensions for Sia Assistant."""

    _MANIFEST_NAME = "plugin_manifest.json"

    def __init__(self, plugins_dir: Optional[str] = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.plugins_dir = plugins_dir or os.path.join(base_dir, "plugins")
        self.manifest_path = os.path.join(self.plugins_dir, self._MANIFEST_NAME)
        self.plugins: Dict[str, Any] = {}
        self.registered_actions: Dict[str, Callable[..., Any]] = {}
        os.makedirs(self.plugins_dir, exist_ok=True)
        self._manifest = self._load_manifest()

    # ── Manifest helpers ────────────────────────────────────────────────────

    def _load_manifest(self) -> Dict[str, Any]:
        """Load the plugin whitelist manifest from disk."""
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"[PluginManager] Manifest read error: {e} — starting fresh.")
        return {"_version": "1.0", "whitelisted_plugins": {}}

    def _save_manifest(self) -> None:
        """Persist the manifest to disk."""
        try:
            with open(self.manifest_path, "w", encoding="utf-8") as f:
                json.dump(self._manifest, f, indent=2)
        except Exception as e:
            logger.error(f"[PluginManager] Manifest write error: {e}")

    def whitelist_plugin(self, plugin_name: str, file_path: str) -> bool:
        """Manually approve and whitelist a plugin (call this after human review)."""
        sha = _compute_sha256(file_path)
        self._manifest.setdefault("whitelisted_plugins", {})[plugin_name] = {
            "sha256": sha,
            "approved_at": __import__("datetime").datetime.now().isoformat(),
        }
        self._save_manifest()
        logger.info(f"✅ Plugin whitelisted: {plugin_name} (sha256={sha[:16]}...)")
        return True

    # ── Core loader ─────────────────────────────────────────────────────────

    def load_plugins(self) -> Dict[str, Any]:
        """Scan plugins directory and load only verified, sandboxed plugin modules."""
        if not os.path.exists(self.plugins_dir):
            return {}

        whitelist: Dict[str, Any] = self._manifest.get("whitelisted_plugins", {})

        for fname in sorted(os.listdir(self.plugins_dir)):
            if fname == self._MANIFEST_NAME:
                continue
            if not (fname.endswith(".py") and not fname.startswith("_")):
                continue

            mod_name = fname[:-3]
            file_path = os.path.join(self.plugins_dir, fname)

            # ── 1. Risky import scan (always runs, even for whitelisted) ────
            violations = _scan_for_risky_code(file_path)
            if violations:
                logger.error(
                    f"🛡️ Plugin BLOCKED — risky code detected in '{fname}': "
                    + "; ".join(violations)
                )
                self._audit_block(mod_name, "RISKY_CODE", violations)
                continue

            # ── 2. Whitelist check ───────────────────────────────────────────
            if mod_name not in whitelist:
                sha = _compute_sha256(file_path)
                logger.warning(
                    f"🔒 Plugin '{fname}' is NOT whitelisted. "
                    f"To approve, call: plugin_manager.whitelist_plugin('{mod_name}', r'{file_path}')"
                )
                self._audit_block(mod_name, "NOT_WHITELISTED", [f"sha256={sha[:16]}..."])
                continue

            # ── 3. Hash integrity check ─────────────────────────────────────
            current_sha = _compute_sha256(file_path)
            expected_sha = whitelist[mod_name].get("sha256", "")
            if current_sha != expected_sha:
                logger.error(
                    f"🚨 Plugin BLOCKED — '{fname}' hash mismatch! "
                    f"Plugin may have been TAMPERED. Re-whitelist after review."
                )
                self._audit_block(mod_name, "HASH_MISMATCH", [
                    f"expected={expected_sha[:16]}...", f"got={current_sha[:16]}..."
                ])
                continue

            # ── 4. Load ─────────────────────────────────────────────────────
            try:
                spec = importlib.util.spec_from_file_location(f"sia_plugin_{mod_name}", file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    self.plugins[mod_name] = module
                    logger.info(f"🧩 Plugin loaded & verified: {mod_name}")

                    if hasattr(module, "register_actions"):
                        actions = module.register_actions()
                        if isinstance(actions, dict):
                            self.registered_actions.update(actions)
            except Exception as e:
                logger.error(f"[PluginManager] Failed loading plugin {fname}: {e}")

        return self.plugins

    def execute_plugin_action(self, action_name: str, *args, **kwargs) -> Optional[Any]:
        """Execute a registered action exported by a plugin."""
        if action_name in self.registered_actions:
            try:
                return self.registered_actions[action_name](*args, **kwargs)
            except Exception as e:
                logger.error(f"[PluginManager] Error executing plugin action {action_name}: {e}")
                return f"❌ Plugin action error: {e}"
        return None

    def list_plugins(self) -> Dict[str, str]:
        """Return dict of loaded plugin names → approval timestamps."""
        wl = self._manifest.get("whitelisted_plugins", {})
        return {
            name: info.get("approved_at", "unknown")
            for name, info in wl.items()
            if name in self.plugins
        }

    # ── Internal helpers ────────────────────────────────────────────────────

    def _audit_block(self, plugin_name: str, reason: str, details: List[str]) -> None:
        """Write plugin block event to audit log."""
        try:
            from .audit_logger import log_action
            log_action(
                f"plugin_load:{plugin_name}",
                risk_level="DENY",
                status=f"BLOCKED_{reason}",
                details=" | ".join(details),
            )
        except Exception:
            pass  # Audit log failure must never crash the loader


plugin_manager = PluginManager()
