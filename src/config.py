from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL = {
    "seed",
    "horizon_steps",
    "dt",
    "initial_price",
    "price_process",
    "order_flow",
    "latency",
    "fees",
    "risk",
    "agent",
}


class ConfigError(ValueError):
    """Raised when an experiment config is malformed."""


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML config, with a tiny fallback for simple project configs."""
    path = Path(path)
    try:
        import yaml

        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except ModuleNotFoundError:
        return _parse_minimal_yaml(path.read_text(encoding="utf-8"))


def load_validated_config(path: str | Path) -> dict[str, Any]:
    config = load_config(path)
    validate_config(config, source=str(path))
    return config


def validate_config(config: dict[str, Any], source: str = "<memory>") -> None:
    missing = REQUIRED_TOP_LEVEL - set(config)
    if missing:
        raise ConfigError(f"{source}: missing top-level config keys: {sorted(missing)}")
    _positive(config, "horizon_steps")
    _positive(config, "dt")
    _positive(config, "initial_price")
    _non_negative(config["price_process"], "sigma", source)
    _non_negative(config["price_process"], "jump_intensity", source)
    _non_negative(config["price_process"], "jump_std", source)
    _non_negative(config["order_flow"], "noise_intensity", source)
    _non_negative(config["order_flow"], "informed_intensity", source)
    _positive(config["order_flow"], "max_market_order_size", source)
    _non_negative(config["latency"], "quote_latency_steps", source)
    _non_negative(config["latency"], "jitter_steps", source)
    _non_negative(config["latency"], "spike_probability", source)
    _non_negative(config["latency"], "spike_steps", source)
    if float(config["latency"].get("spike_probability", 0.0)) > 1.0:
        raise ConfigError(f"{source}: latency.spike_probability must be <= 1")
    if "external_lob" in config:
        _positive(config["external_lob"], "levels", source)
        _positive(config["external_lob"], "quantity", source)
        _non_negative(config["external_lob"], "half_spread_bps", source)
        _non_negative(config["external_lob"], "ttl_steps", source)
    if "multi_asset" in config and config["multi_asset"].get("enabled", False):
        _positive(config["multi_asset"], "hedge_initial_price", source)
        _non_negative(config["multi_asset"], "hedge_sigma", source)
        corr = float(config["multi_asset"].get("correlation", 0.0))
        if corr < -1.0 or corr > 1.0:
            raise ConfigError(f"{source}: multi_asset.correlation must be in [-1, 1]")
    _non_negative(config["risk"], "max_position", source)
    _non_negative(config["risk"], "max_drawdown", source)
    if not config["agent"].get("type"):
        raise ConfigError(f"{source}: agent.type is required")


def deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def config_hash(config: dict[str, Any]) -> str:
    payload = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _positive(config: dict[str, Any], key: str, source: str = "<memory>") -> None:
    if float(config.get(key, 0)) <= 0:
        raise ConfigError(f"{source}: {key} must be positive")


def _non_negative(config: dict[str, Any], key: str, source: str = "<memory>") -> None:
    if float(config.get(key, 0)) < 0:
        raise ConfigError(f"{source}: {key} must be non-negative")


def _parse_minimal_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        key, _, value = raw.strip().partition(":")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value.strip() == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _coerce_scalar(value.strip())
    return root


def _coerce_scalar(value: str) -> Any:
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip("'\"")
