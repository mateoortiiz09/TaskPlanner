def test_zona_horaria_de_colombia(settings):
    assert settings.TIME_ZONE == "America/Bogota"
    assert settings.USE_TZ is True


def test_idioma_espanol_colombia(settings):
    assert settings.LANGUAGE_CODE == "es-co"


def test_debug_desactivado_en_base():
    from config.settings import base

    assert base.DEBUG is False
