"""Tests for neotree.preset."""

import pytest

from neotree.preset import PRESETS, get_preset_patterns


class TestPresets:
    @pytest.mark.parametrize(
        ("preset", "required_patterns"),
        [
            ("python", ["__pycache__", "*.pyc", ".venv", ".git"]),
            ("node", ["node_modules", ".git"]),
            ("rust", ["target", ".git"]),
        ],
    )
    def test_language_presets(self, preset: str, required_patterns: list[str]) -> None:
        """Known language presets must include expected patterns.

        Args:
            preset: Preset name to test.
            required_patterns: Patterns expected in the resulting list.
        """
        patterns = get_preset_patterns(preset)
        for pattern in required_patterns:
            assert pattern in patterns

    def test_generic_preset(self) -> None:
        patterns = get_preset_patterns("generic")
        assert ".git" in patterns
        assert ".DS_Store" in patterns
        # No duplicate generic entries
        assert patterns.count(".git") == 1

    def test_unknown_preset_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown preset"):
            get_preset_patterns("java")

    def test_all_presets_are_lists(self) -> None:
        for name, patterns in PRESETS.items():
            assert isinstance(patterns, list), f"Preset '{name}' should be a list"
            assert all(isinstance(p, str) for p in patterns)
