from normalize import normalize_name
def test_normalize_complex():
    assert normalize_name("  AMIR ALI ") == "amir-ali"
def test_preserve_safe():
    assert normalize_name("amir-ali") == "amir-ali"
