"""Tests for the JSON-Bag tokenizer. Run: python tokenizer_test.py"""
from collections import Counter

from tokenizer import _load_json, is_atomic, tokenize


def test_single_game_state_happy_path():
    """Defaults (mode="both", ordered=True) on a single game-state dict."""
    state = {
        "turn": 3,
        "players": [
            {"name": "Alice", "score": 10},
            {"name": "Bob", "score": 7},
        ],
        "board": {"width": 8},
        "ratio": 1.5,
    }
    bag = tokenize(state)
    assert isinstance(bag, Counter)
    # Root atomic: path starts with "." (empty root prefix + "." + key)
    assert bag[".turn.3"] == 1
    # Dict branch: only ONE token per atomic value (ordered/unordered split is list-only)
    assert bag[".board.width.8"] == 1
    assert ".board.width" not in bag  # no num-suffix token by default
    # List elements get BOTH positional and flattened companion tokens
    assert bag[".players[0].name.Alice"] == 1
    assert bag[".players.name.Alice"] == 1
    assert bag[".players[1].name.Bob"] == 1
    assert bag[".players.name.Bob"] == 1
    assert bag[".players[0].score.10"] == 1
    # Floats are tokenized but never freq-expanded (not int)
    assert bag[".ratio.1.5"] == 1
    assert ".ratio" not in bag


def test_modes():
    state = {"players": [{"name": "Alice"}, {"name": "Bob"}]}
    ordered_bag = tokenize(state, mode="ordered")
    assert ordered_bag[".players[0].name.Alice"] == 1
    assert ".players.name.Alice" not in ordered_bag
    unordered_bag = tokenize(state, mode="unordered")
    assert unordered_bag[".players.name.Alice"] == 1
    assert ".players[0].name.Alice" not in unordered_bag
    both_bag = tokenize(state, mode="both")
    assert both_bag[".players[0].name.Alice"] == 1
    assert both_bag[".players.name.Alice"] == 1
    # char mode: frequency of characters of the stringified object, no path tokens
    assert tokenize({"a": 1}, mode="char") == Counter(str({"a": 1}))


def test_list_of_states_ordered_false():
    """Trajectory input (list of states) must use ordered=False to drop [i] prefixes."""
    s1 = {"turn": 3, "score": 10}
    s2 = {"turn": 3, "score": 12}
    bag = tokenize([s1, s2], ordered=False)
    assert ".turn[0].3" not in bag and ".[0].turn.3" not in bag
    # Frequencies accumulate across states sharing paths/values
    assert bag[".turn.3"] == 2
    assert bag[".score.10"] == 1
    assert bag[".score.12"] == 1
    # With ordered=True (default) the positional tokens appear as well.
    # Note: root-list elements get NO leading dot in ordered mode (upstream
    # asymmetry — ordered_prefix = "" + "[0]", and the dot only comes from
    # key_prefix = prefix + "." + key inside dict recursion).
    bag_ordered = tokenize([s1])
    assert bag_ordered["[0].turn.3"] == 1
    assert bag_ordered[".[0].turn.3"] == 0
    assert bag_ordered[".turn.3"] == 1


def test_num_suffix_frequency():
    """Numeric value n > 0 at path X adds stripped-path token X with frequency += n."""
    bag = tokenize({"number": 4}, num_suffix_frequency=True)
    assert bag[".number.4"] == 1
    assert bag[".number"] == 4
    # List elements expand under both positional and flattened paths
    bag = tokenize({"deck": [2]}, num_suffix_frequency=True)
    assert bag[".deck[0].2"] == 1
    assert bag[".deck[0]"] == 2
    assert bag[".deck.2"] == 1
    assert bag[".deck"] == 2
    # Sentinels: negative values are tokenized but NOT expanded
    bag = tokenize({"capacity": -1}, num_suffix_frequency=True)
    assert bag[".capacity.-1"] == 1
    assert ".capacity" not in bag


def test_booleans_excluded_from_expansion():
    """bool is an int subclass — must never trigger num-suffix expansion."""
    bag = tokenize({"flag": True}, num_suffix_frequency=True)
    assert bag[".flag.True"] == 1
    assert ".flag" not in bag
    # Same exclusion inside lists (both branches)
    bag = tokenize({"flags": [True]}, num_suffix_frequency=True)
    assert bag[".flags[0].True"] == 1
    assert ".flags[0]" not in bag
    assert bag[".flags.True"] == 1
    assert ".flags" not in bag


def test_nested_json_string():
    """String values that are themselves JSON are parsed and recursed into."""
    state = {"state": '{"hp": 5}'}
    bag = tokenize(state)
    assert bag[".state.hp.5"] == 1
    assert ".state.'{'hp': 5}'" not in bag  # not treated as an atomic string
    # Non-JSON strings stay atomic
    bag = tokenize({"name": "Alice"})
    assert bag[".name.Alice"] == 1


def test_invalid_top_level_raises():
    try:
        tokenize(42)
        raised = False
    except NotImplementedError:
        raised = True
    assert raised, "tokenize(42) should raise NotImplementedError"


def test_helpers():
    assert is_atomic("x") and is_atomic(3) and is_atomic(None)
    assert not is_atomic({}) and not is_atomic([])
    assert _load_json('{"a": 1}') == {"a": 1}
    assert _load_json("not json") == "not json"
    assert _load_json(5) == 5


def test_empty_containers():
    assert tokenize({}) == Counter()
    assert tokenize([]) == Counter()
    assert tokenize({"empty": {}}) == Counter()


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    if failed:
        raise SystemExit(f"{failed}/{len(tests)} tests failed")
    print(f"All {len(tests)} tests passed.")


if __name__ == "__main__":
    main()
