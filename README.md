# JSON-Bag

Minimal, dependency-free implementation of the **JSON-Bag tokenizer**: it turns a JSON game state into a bag-of-tokens (a token-frequency dict), giving a simple game-agnostic representation for learning and analysis. No game-specific code needed.

Introduced in "JSON-Bag: A generic game trajectory representation" (IEEE CoG 2025): https://arxiv.org/abs/2508.00712.

A demonstration on how to use this framework to make game agnostic value functions "Game-Agnostic Value Functions through Automatic JSON Feature Extraction" (IEEE CoG 2026): https://arxiv.org/abs/2608.30056

## Concept

Every atomic value in the JSON document contributes one token of the form:

```
key.subkey[i].value
```

- the token is the **dotted key path** from the root, plus the value;
- list elements get a positional prefix `[i]` (ordered mode) and/or are flattened onto the shared list path (unordered mode);
- string values that are themselves JSON documents are parsed and recursed into;
- the result is a `collections.Counter` mapping each token to its frequency.

Example — `{"players": [{"score": 10}]}` tokenizes (default `mode="both"`) to:

```
.players[0].score.10   1   # ordered (positional)
.players.score.10      1   # unordered (flattened)
```

## Modes

| `mode`             | Tokens emitted                                                        |
| ------------------ | --------------------------------------------------------------------- |
| `"both"` (default) | positional `[i]` **and** flattened companion tokens for list elements |
| `"ordered"`        | only positional `[i]` tokens                                          |
| `"unordered"`      | only flattened tokens (list indices dropped)                          |
| `"char"`           | degenerate: character frequencies of `str(state)`                     |

**Trajectory caveat:** when the input is a *list of states* (a trajectory) rather than a single state dict, pass `ordered=False` so the states themselves don't receive positional prefixes.

## Options

```python
tokenize(collection, prefix='', ordered=True, mode="both",
         filter_player=False, binning=False, pair_xy=False,
         num_suffix_frequency=False) -> Counter
```

- `num_suffix_frequency` — for a numeric value `n > 0` at path `X`, also add the value-stripped path token `X` with frequency `+= n`, so quantities act as token **weights** instead of being locked inside token strings. Booleans, floats, and non-positive/sentinel values (`0`, `-1`, ...) are excluded. Examples below.
- `filter_player` — skip every dict containing `"player" > 0` (multi-player hidden-information ablation).
- `binning` — floor `x`/`y` coordinate values to multiples of 2.
- `pair_xy` — merge `x`/`y` pairs into a single combined token.

### `num_suffix_frequency` examples

Without the option, a numeric value only changes the token's *identity*, never any frequency — `4` and `1` produce unrelated tokens (`...number.4` vs `...number.1`) that each weigh the same in the bag:

```python
state = {"deck": [{"number": 4}, {"number": 4}]}

tokenize(state, mode="unordered")
# {'.deck.number.4': 2}        <- the value 4 is just part of the token string
```

With `num_suffix_frequency=True`, the value-stripped path token is added with the numeric value as its frequency, so quantities accumulate additively across the state:

```python
tokenize(state, mode="unordered", num_suffix_frequency=True)
# {'.deck.number.4': 2,
#  '.deck.number': 8}          <- 4 + 4 accumulated across both cards
```

(With the default `mode="both"`, the positional companions `.deck[0].number.4: 1` and `.deck[0].number: 4` appear as well.)

Only positive integers expand — booleans, floats, and sentinel values are tokenized normally but get no weighted companion token:

```python
state = {"flag": True, "capacity": -1, "ratio": 1.5, "count": 2}

tokenize(state, mode="unordered", num_suffix_frequency=True)
# {'.flag.True': 1, '.capacity.-1': 1, '.ratio.1.5': 1,
#  '.count.2': 1, '.count': 2} <- only '.count' gets the weighted companion token
```

## Usage

### Library

```python
import json
from tokenizer import tokenize

state = json.load(open("game_state.json"))
bag = tokenize(state)                            # Counter: token -> frequency
bag = tokenize(state, mode="unordered")          # drop list indices
bag = tokenize(trajectory, ordered=False)        # trajectory = list of states
bag = tokenize(state, num_suffix_frequency=True) # expand numeric counts
```

### CLI

```bash
python tokenizer.py game_state.json                 # prints the token-frequency dict
python tokenizer.py game_state.json --mode unordered --num-suffix-freq
cat game_state.json | python tokenizer.py           # stdin also works
```

## Requirements

Python 3.13+

## Tests

```bash
python tokenizer_test.py
```

## TODO
- Scripts to make prototype + feature selection with Random Forest
- Raw data from JSON-Bag value functions paper
