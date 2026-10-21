def usuario_normalizado(request, credentials):
    """Cuenta los intentos por correo sin importar mayúsculas."""
    valor = (credentials or {}).get("username") or request.POST.get("username", "")
    return valor.strip().lower()
