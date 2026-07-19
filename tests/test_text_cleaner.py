from ai_qa_gherkin.utils.text_cleaner import TextCleaner


def test_clean_repairs_mojibake_and_rare_spaces():
    text = "  Validaci\u00c3\u00b3n\u00a0 de   datos  inv\u00c3\u00a1lidos  "

    assert TextCleaner.clean(text, auto_learn=False) == (
        "Validaci\u00f3n de datos inv\u00e1lidos"
    )


def test_clean_repairs_double_mojibake():
    text = "Caracter\u00c3\u0192\u00c2\u00adstica: Validaci\u00c3\u0192\u00c2\u00b3n"

    assert TextCleaner.clean(text, auto_learn=False) == (
        "Caracter\u00edstica: Validaci\u00f3n"
    )


def test_clean_preserves_feature_line_breaks():
    text = (
        "Caracter\u00c3\u00adstica: Demo\n\n"
        "  Escenario: Texto   raro\n"
        "    Dado que est\u00c3\u00a1 disponible"
    )

    cleaned = TextCleaner.clean(text, auto_learn=False)

    assert "Caracter\u00edstica: Demo" in cleaned
    assert "  Escenario: Texto raro" in cleaned
    assert "\n    Dado que est\u00e1 disponible" in cleaned


def test_valid_words_are_not_rewritten():
    cleaned = TextCleaner.clean("Datos inv\u00e1lidos muestran error", auto_learn=False)

    assert cleaned == "Datos inv\u00e1lidos muestran error"
