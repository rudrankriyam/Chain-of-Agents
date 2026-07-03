"""Tests for chunking and word-count helpers in chain_of_agents.utils."""

from chain_of_agents.utils import count_words, get_default_prompts, split_into_chunks


class TestSplitIntoChunks:
    def test_empty_text_returns_no_chunks(self):
        assert split_into_chunks("", 100) == []

    def test_whitespace_only_text_returns_no_chunks(self):
        assert split_into_chunks("   \n\n   \n\n ", 100) == []

    def test_short_text_single_chunk(self):
        text = "one two three four five"
        chunks = split_into_chunks(text, 100)
        assert chunks == [text]

    def test_chunks_respect_chunk_size(self):
        words = [f"word{i}" for i in range(250)]
        text = " ".join(words)
        chunk_size = 100
        chunks = split_into_chunks(text, chunk_size)
        assert all(len(chunk.split()) <= chunk_size for chunk in chunks)

    def test_no_words_lost_when_splitting(self):
        words = [f"word{i}" for i in range(523)]
        text = " ".join(words)
        chunks = split_into_chunks(text, 100)
        recombined = " ".join(chunks).split()
        assert recombined == words

    def test_paragraphs_kept_together_when_they_fit(self):
        text = "para one words here\n\npara two words here"
        chunks = split_into_chunks(text, 100)
        assert len(chunks) == 1
        assert "para one" in chunks[0] and "para two" in chunks[0]

    def test_oversized_paragraph_is_split(self):
        text = " ".join(f"w{i}" for i in range(30))
        chunks = split_into_chunks(text, 10)
        assert len(chunks) == 3
        assert all(len(chunk.split()) == 10 for chunk in chunks)

    def test_empty_paragraphs_are_skipped(self):
        text = "alpha beta\n\n\n\n\n\ngamma delta"
        chunks = split_into_chunks(text, 100)
        assert chunks == ["alpha beta gamma delta"]


class TestCountWords:
    def test_empty_string(self):
        assert count_words("") == 0

    def test_simple_sentence(self):
        assert count_words("the quick brown fox") == 4

    def test_extra_whitespace_ignored(self):
        assert count_words("  spaced\t\tout \n words  ") == 3


class TestDefaultPrompts:
    def test_returns_worker_and_manager_prompts(self):
        worker_prompt, manager_prompt = get_default_prompts()
        assert "worker" in worker_prompt.lower()
        assert "manager" in manager_prompt.lower()
