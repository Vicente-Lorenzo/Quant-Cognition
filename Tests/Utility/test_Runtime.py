import shlex
import random

import pytest

from Library.Utility.Runtime import join_arguments, split_arguments

def reference(arguments):
    tokens = shlex.split(arguments, posix=False) if arguments else []
    return [token[1:-1] if len(token) > 1 and token[0] == token[-1] and token[0] in "\"'" else token for token in tokens]

def outcome(function, arguments):
    try: return function(arguments)
    except ValueError: return ValueError

def test_split_arguments_unquotes_and_keeps_windows_paths():
    assert split_arguments('--run "C:\\Users\\Admin\\Runs\\a b" --plot') == ["--run", "C:\\Users\\Admin\\Runs\\a b", "--plot"]
    assert split_arguments("") == [] and split_arguments(None) == []

def test_split_arguments_refuses_an_unclosed_quote():
    with pytest.raises(ValueError):
        split_arguments('--ticker "EURUSD')

def test_split_arguments_round_trips_join_arguments():
    parts = ["--strategy", "Trend", "--run", "C:\\Temp\\Runs\\a b", "--label", ""]
    assert split_arguments(join_arguments(parts)) == parts

def test_split_arguments_agrees_with_non_posix_shlex():
    generator = random.Random(7)
    alphabet = ["a", "b", " ", " ", "\"", "'", "\t", "-", "=", "\n", "\r", "\\", "#", "\x0b", "\u00e9", "\u00a0"]
    for _ in range(20000):
        text = "".join(generator.choice(alphabet) for _ in range(generator.randint(0, 14)))
        assert outcome(split_arguments, text) == outcome(reference, text), ascii(text)