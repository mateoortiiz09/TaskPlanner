document.addEventListener("click", function (evento) {
  var boton = evento.target.closest("[data-alternar-contrasena]");
  if (boton) {
    var campo = document.getElementById(boton.dataset.alternarContrasena);
    var mostrar = campo.type === "password";
    campo.type = mostrar ? "text" : "password";
    boton.textContent = mostrar ? "Ocultar" : "Mostrar";
    boton.setAttribute("aria-pressed", mostrar ? "true" : "false");
    return;
  }
  var fila = evento.target.closest("tr[data-href]");
  if (fila && !evento.target.closest("a, button, input, select, label, form")) {
    window.location.href = fila.dataset.href;
  }
});

document.addEventListener("keydown", function (evento) {
  if (evento.key !== "Enter" || !evento.target.closest) {
    return;
  }
  var fila = evento.target.closest("tr[data-href]");
  if (fila) {
    window.location.href = fila.dataset.href;
  }
});
