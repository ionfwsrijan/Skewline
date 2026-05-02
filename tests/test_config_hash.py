import json
import random
from pathlib import Path

from config import config_hash, deep_merge, load_validated_config


def test_hash_is_stable_regardless_of_key_order():
    a = {"agent": {"type": "tab_rl"}, "market": {"spread_bps": 5}, "risk": {"max_inventory": 10}}
    keys = list(a.keys())
    random.shuffle(keys)
    b = {k: a[k] for k in keys}
    assert config_hash(a) == config_hash(b)


def test_hash_changes_when_config_value_changes():
    base = {"agent": {"type": "tab_rl"}, "market": {"spread_bps": 5}}
    altered = {"agent": {"type": "tab_rl"}, "market": {"spread_bps": 6}}
    assert config_hash(base) != config_hash(altered)


def test_hash_is_deterministic_across_calls():
    config = {"agent": {"type": "dqn"}, "risk": {"max_inventory": 25}}
    assert config_hash(config) == config_hash(config)


def test_loaded_yaml_hashes_match_equivalent_inline_config():
    cfg: dict = {}
    for name in ("avellaneda_stoikov", "rl_agent", "dqn_agent"):
        path = Path(f"configs/{name}.yaml")
        if not path.exists():
            continue
        loaded = load_validated_config(path)
        inline = json.loads(json.dumps(loaded))
        assert config_hash(loaded) == config_hash(inline)
        cfg[name] = config_hash(loaded)
    assert len(cfg) >= 2  # at least two real configs produce consistent hashes


def test_deep_merge_then_hash_matches_precomputed_key():
    base = {"market": {"spread_bps": 5, "vol_bps": 40}}
    override = {"market": {"vol_bps": 60}}
    merged = deep_merge(base, override)
    expected = {"market": {"spread_bps": 5, "vol_bps": 60}}
    assert merged == expected
    assert config_hash(merged) == config_hash(expected)