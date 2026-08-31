"""JSON-Bag tokenizer: turn a JSON game state into a token-frequency dict.

Tokens are path-prefix tokens of the form ``key.sub[i].value``: every atomic
value contributes a ``<path>.<value>`` token, where ``<path>`` is the dotted
key path from the root and list elements are indexed as ``[i]`` (ordered
mode) and/or flattened onto the shared list path (unordered mode). See
README.md for the concept and the available options.
"""
import json
from collections import Counter
from typing import Any, Dict, List, Literal, Union


def is_atomic(obj: Any) -> bool:
    return not isinstance(obj, (dict, list))


def _load_json(s: Any) -> Any:
    if isinstance(s, str):
        try:
            return json.loads(s)
        except json.decoder.JSONDecodeError:
            return s
    return s


# Set ordered to False if collection is List to prevent ordered-prefix when tokenizing a list of JSONs
# (even when mode="ordered")
def tokenize(collection: Union[Dict, List], prefix: str = '', ordered=True,
             mode: Literal["both", "ordered", "unordered", "char"] = "both",
             filter_player=False, binning=False, pair_xy=False,
             num_suffix_frequency: bool = False) -> Counter:
    if mode == "char":
        return Counter(str(collection))
    try:
        assert isinstance(collection, (dict, list))
    except AssertionError:
        print(collection)
        print(type(collection))
        # raise AssertionError()
    tokens = Counter()
    if isinstance(collection, list):
        for i in range(len(collection)):
            ordered_prefix = prefix + f"[{int(i)}]"
            obj = _load_json(collection[i])
            if is_atomic(obj):
                is_numeric_obj = isinstance(obj, int) and not isinstance(obj, bool)
                if ordered and mode != "unordered":
                    tokens[ordered_prefix + "." + str(obj)] += 1
                    if num_suffix_frequency and is_numeric_obj and obj > 0:
                        tokens[ordered_prefix] += obj
                if mode != "ordered" or not ordered:
                    tokens[prefix + "." + str(obj)] += 1
                    if num_suffix_frequency and is_numeric_obj and obj > 0:
                        tokens[prefix] += obj
            else:
                if ordered and mode != "unordered":
                    tokens.update(tokenize(obj, ordered_prefix, mode=mode,
                                           filter_player=filter_player, binning=binning, pair_xy=pair_xy,
                                           num_suffix_frequency=num_suffix_frequency))
                if mode != "ordered" or not ordered:
                    tokens.update(tokenize(obj, prefix, mode=mode,
                                           filter_player=filter_player, binning=binning, pair_xy=pair_xy,
                                           num_suffix_frequency=num_suffix_frequency))
    elif isinstance(collection, dict):
        # TODO Parameterize this
        if filter_player and "player" in collection.keys() and collection["player"] > 0:  # filter every player but first
            # print("FILTERED")
            return tokens
        pair_xy_value = {"x": -99, "y": -99}
        for key, value in collection.items():
            key_prefix = prefix + "." + str(key)
            value = _load_json(value)
            if is_atomic(value):
                is_numeric_value = isinstance(value, int) and not isinstance(value, bool)
                is_binning_value = binning and (key == "x" or key == "y")
                is_pair_xy_value = pair_xy and (key == "x" or key == "y")
                # binning numerical value
                if is_binning_value:
                    n = 2
                    value = int(value / n) * n
                if key in pair_xy_value:
                    pair_xy_value[key] = value
                    if pair_xy:
                        continue
                tokens[key_prefix + "." + str(value)] += 1
                if num_suffix_frequency and is_numeric_value and value > 0 and not is_binning_value and not is_pair_xy_value:
                    tokens[key_prefix] += value
            else:
                tokens.update(tokenize(value, key_prefix, mode=mode,
                                       filter_player=filter_player, binning=binning, pair_xy=pair_xy,
                                       num_suffix_frequency=num_suffix_frequency))
        if pair_xy and pair_xy_value["x"] >= 0:
            x, y = pair_xy_value["x"], pair_xy_value["y"]
            tokens[f"{prefix}.x.{x}.y.{y}"] += 1
    else:
        raise NotImplementedError
    return tokens


def _parse_args(argv):
    import argparse
    parser = argparse.ArgumentParser(
        prog="tokenizer",
        description="Tokenize a single JSON game state into a token-frequency dict (JSON-Bag).")
    parser.add_argument("json_file", nargs="?", default="-",
                        help="path to a JSON game state file, or '-' to read stdin (default)")
    parser.add_argument("--mode", choices=("both", "ordered", "unordered", "char"), default="both",
                        help="tokenization mode (default: both)")
    parser.add_argument("--no-ordered", dest="ordered", action="store_false",
                        help="drop positional [i] prefixes; use when the input is a list of states (trajectory)")
    parser.add_argument("--num-suffix-freq", dest="num_suffix_frequency", action="store_true",
                        help="for a numeric value n > 0 at path X, also add token X with frequency += n")
    return parser.parse_args(argv)


def _main(argv=None) -> None:
    import sys
    args = _parse_args(argv)
    if args.json_file == "-":
        state = json.load(sys.stdin)
    else:
        with open(args.json_file, "r", encoding="utf-8") as f:
            state = json.load(f)
    bag = tokenize(state, ordered=args.ordered, mode=args.mode,
                   num_suffix_frequency=args.num_suffix_frequency)
    print(json.dumps(dict(bag), indent=2))


if __name__ == "__main__":
    _main()
