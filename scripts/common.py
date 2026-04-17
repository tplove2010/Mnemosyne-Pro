#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONFIDENCE_RANK = {"low": 1, "medium": 2, "high": 3}
EXPLICITNESS_RANK = {"implied": 1, "explicit": 2}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def strip_jsonc_comments(text: str) -> str:
    text = re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)
    return text


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_config(workspace: Path) -> dict[str, Any]:
    defaults = {
        "review_mode": True,
        "non_destructive_install": True,
        "preserve_unknown_memory_artifacts": True,
        "sharing_mode": "scoped",
        "scope_resolution": "narrowest-first",
        "global_promotion": {
            "enabled": True,
            "require_explicit": True,
            "min_repeat_count": 2,
        },
        "intake": {
            "feishu_enabled": True,
            "tasks_enabled": True,
            "feedback_enabled": True,
        },
        "incremental": {
            "use_hash": True,
            "skip_if_no_changes": True,
        },
        "conflicts": {
            "auto_resolve_safe_conflicts": True,
            "require_review_for_scope_change": True,
        },
        "publish": {
            "global_target": "memory/global/preferences.md",
            "fallback_global_target": "MEMORY.md",
        },
    }
    cfg_path = workspace / ".mnemosyne" / "config.jsonc"
    if not cfg_path.exists():
        return defaults
    loaded = json.loads(strip_jsonc_comments(cfg_path.read_text(encoding="utf-8")))
    return deep_merge(defaults, loaded)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def slugify(text: str, fallback: str = "item") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or fallback


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text.strip()
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}, text.strip()
    raw, body = parts
    meta: dict[str, str] = {}
    for line in raw.splitlines()[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, body.strip()


def choose_scope(meta: dict[str, str]) -> tuple[str, str]:
    if meta.get("agent_id"):
        return "agent", meta["agent_id"]
    if meta.get("project_id"):
        return "project", meta["project_id"]
    if meta.get("channel_id"):
        return "channel", meta["channel_id"]
    return "global", "global"


def guess_type(text: str, source_type: str) -> str:
    lower = text.lower()
    preference_kws = ["prefer", "preference", "偏好", "喜欢", "不喜欢", "不要", "别", "conclusion first", "先给结论"]
    rule_kws = ["must", "should", "必须", "应该", "always", "以后都", "规则"]
    project_kws = ["project", "项目", "里程碑", "需求", "roadmap", "milestone"]
    channel_kws = ["channel", "群", "飞书群", "thread", "mention", "频道"]
    feedback_kws = ["feedback", "结果", "执行", "failed", "succeeded", "bug", "问题"]
    if any(k in lower for k in preference_kws):
        return "preference"
    if any(k in lower for k in rule_kws):
        return "rule"
    if any(k in lower for k in project_kws):
        return "project_context"
    if any(k in lower for k in channel_kws):
        return "channel_norm"
    if source_type == "tasks" or any(k in lower for k in feedback_kws):
        return "task_feedback"
    return "fact"


def logical_key(scope_type: str, scope_key: str, record_type: str, topic: str) -> str:
    return f"{scope_type}:{scope_key}|{record_type}|{slugify(topic, record_type)}"


def marker_for_key(key: str) -> str:
    return f"<!-- mnemosyne:key:{key} -->"


def detect_environment(root: Path) -> dict[str, Any]:
    memory_dir = root / "memory"
    mnemo_dir = root / ".mnemosyne"
    dreams_dir = memory_dir / ".dreams"
    dreams_md = root / "DREAMS.md"
    memory_md = root / "MEMORY.md"
    daily_files = sorted(memory_dir.glob("*.md")) if memory_dir.exists() else []
    scoped_native = []
    for rel in ["memory/global", "memory/agents", "memory/projects", "memory/channels"]:
        if (root / rel).exists():
            scoped_native.append(rel)
    legacy_paths = [p for p in [memory_dir / "inbox", memory_dir / "review"] if p.exists()]
    custom_sidecars = []
    transcript_markers = []
    if root.exists():
        for candidate in root.iterdir():
            if not candidate.is_dir():
                continue
            name = candidate.name.lower()
            if candidate.name in {"memory", ".mnemosyne", ".git", ".github", "node_modules"}:
                continue
            if any(token in name for token in ["memory", "recall", "dream"]):
                custom_sidecars.append(candidate.name)
            if any(token in name for token in ["session", "transcript", "conversation", "history"]):
                transcript_markers.append(candidate.name)

    env_class = "fresh"
    if mnemo_dir.exists():
        env_class = "mnemosyne-existing"
    elif legacy_paths:
        env_class = "legacy-mnemosyne-v1"
    elif dreams_dir.exists() or dreams_md.exists():
        env_class = "builtin-dreaming"
    elif memory_md.exists() and (daily_files or scoped_native):
        env_class = "builtin-daily"
    elif memory_md.exists() or memory_dir.exists():
        env_class = "builtin-basic"
    elif custom_sidecars:
        env_class = "custom-memory-sidecars"

    if env_class == "fresh" and transcript_markers:
        env_class = "transcript-heavy"

    return {
        "workspace": str(root),
        "class": env_class,
        "has_MEMORY_md": memory_md.exists(),
        "has_memory_dir": memory_dir.exists(),
        "daily_file_count": len(daily_files),
        "scoped_native_paths": scoped_native,
        "has_dreaming": dreams_dir.exists() or dreams_md.exists(),
        "has_mnemosyne": mnemo_dir.exists(),
        "legacy_paths": [str(p.relative_to(root)) for p in legacy_paths],
        "custom_sidecars": custom_sidecars,
        "transcript_markers": transcript_markers,
        "recommended_install_mode": "sidecar-only" if env_class != "fresh" else "sidecar-plus-memory",
        "safe_to_create_memory_md": not memory_md.exists(),
    }


def ensure_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8")
