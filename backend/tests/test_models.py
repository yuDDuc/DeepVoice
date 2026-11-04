import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.models import chunk_text, remove_repetitions


def test_chunk_text_prefers_sentences_and_limits_words():
    assert chunk_text('one two. three four!', 25) == ['One two.', 'Three four!']
    assert all(len(chunk.split()) <= 3 for chunk in chunk_text('one two three four five six', 3))


def test_chunk_text_empty_and_one_word():
    assert chunk_text('', 25) == []
    assert chunk_text('hello', 25) == ['Hello']


def test_remove_repetitions_and_slashes():
    assert remove_repetitions('<pad> bạn biết cỏ cỏ cỏ cỏ / nhanh nhanh nhanh chóng </s>') == 'bạn biết cỏ nhanh chóng'
    assert '<' not in remove_repetitions('<tag>taller than you</tag>')
