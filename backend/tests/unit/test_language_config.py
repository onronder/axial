import pytest

from core.language_config import DEFAULT_REGCONFIG, LANG_TO_REGCONFIG, get_regconfig


@pytest.mark.parametrize(
    ("lang_code", "expected"),
    [
        ("tr", "turkish"),
        ("en", "english"),
        ("de", "german"),
        ("TR", "turkish"),
        ("ja", DEFAULT_REGCONFIG),
        ("zh", DEFAULT_REGCONFIG),
        (None, DEFAULT_REGCONFIG),
        ("", DEFAULT_REGCONFIG),
    ],
)
def test_get_regconfig_maps_supported_and_fallback_languages(lang_code, expected):
    assert get_regconfig(lang_code) == expected


def test_language_mapping_covers_expected_builtin_regconfigs():
    assert len(LANG_TO_REGCONFIG) == 28

