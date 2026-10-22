from normalize import normalize_name
def test_multiple_words():
    assert normalize_name("  LAYLA ALI ") == "layla-ali"
