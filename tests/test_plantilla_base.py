from django.conf import settings


def test_archivos_estaticos_de_proveedores_existen():
    static_dir = settings.STATICFILES_DIRS[0]

    assert (static_dir / "vendor" / "bootstrap" / "bootstrap.min.css").is_file()
    assert (static_dir / "vendor" / "bootstrap" / "bootstrap.bundle.min.js").is_file()
    assert (static_dir / "vendor" / "htmx" / "htmx.min.js").is_file()


def test_pagina_de_inicio_usa_recursos_locales(client):
    response = client.get("/")
    content = response.content.decode()

    assert response.status_code == 200
    assert "/static/vendor/bootstrap/bootstrap.min.css" in content
    assert "/static/vendor/bootstrap/bootstrap.bundle.min.js" in content
    assert "/static/vendor/htmx/htmx.min.js" in content
    assert "cdn." not in content.lower()
