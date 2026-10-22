# TaskPlanner

## 1. Qué es TaskPlanner

TaskPlanner es una intranet de ProScience Lab S.A.S. para organizar y supervisar
el trabajo interno. La Subgerente crea las tareas, las asigna a los líderes de
área y consulta su avance desde un panel central.

Cada tarea tiene responsables, prioridad, estado y fecha límite. El sistema
calcula los vencimientos en días calendario y envía avisos por correo cuando una
tarea se asigna, se acerca a su fecha límite o está atrasada.

La aplicación incluye áreas y usuarios propios, control de acceso por rol,
adjuntos validados, auditoría y avisos de correo. El modo local utiliza datos de
demostración y Mailpit para que las pruebas no envíen mensajes a destinatarios
reales.

## 2. Roles y permisos

La matriz de referencia es `ESPERADO` en `tests/test_matriz_permisos.py`.

| Capacidad | Administrador | Subgerente | Líder de área |
|---|---|---|---|
| Gestionar usuarios y áreas | Sí | No | No |
| Consultar el panel de administración | Sí | No | No |
| Ver tareas | Todas; las restringidas aparecen enmascaradas | Todas y con contenido | Solo las asignadas |
| Crear tareas no restringidas | Sí | Sí | No |
| Editar tareas no restringidas | Sí | Sí | No |
| Crear o editar tareas restringidas | No | Sí | No |
| Cambiar estado y completar tareas | No | Sí | No |
| Eliminar y recuperar tareas | Sí | Sí | No |
| Adjuntar archivos | No | Sí | No |
| Consultar auditoría | Sí | Sí | No |

Los responsables siempre pueden consultar sus propias tareas restringidas. Una
tarea completada no se puede editar ni cambiar de estado.

## 3. Tecnología

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.13 |
| Framework web | Django 5.2 |
| Base de datos | PostgreSQL 18 |
| Panel de administración | django-unfold |
| Protección contra intentos de acceso | django-axes |
| Hash de contraseñas | Argon2 mediante argon2-cffi |
| Tareas programadas | Django-Q2 con PostgreSQL como cola |
| Interfaz | htmx y Bootstrap servidos desde archivos locales |
| Cifrado de adjuntos | cryptography (AES-256-GCM) |
| Correo local | Mailpit |
| Correo de producción | Microsoft Graph |

Las herramientas y dependencias utilizadas son gratuitas y de licencia abierta.
Las versiones fijadas de las dependencias de Python están en `requirements.txt`.

## 4. Instalación local en Windows

Requisitos: Git, Python 3.13, PostgreSQL 18 y PowerShell.

### Clonar y preparar el entorno

```powershell
git clone https://github.com/mateoortiiz09/TaskPlanner.git
Set-Location TaskPlanner
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Crear la base de datos y el usuario de aplicación

En `psql`, con una cuenta administradora de PostgreSQL, crea una cuenta local de
aplicación sin privilegios de superusuario. `CREATEDB` permite a pytest crear
una base temporal de pruebas en desarrollo; no se debe conceder este permiso
al usuario de la aplicación en producción.

```sql
CREATE ROLE taskplanner_app WITH LOGIN PASSWORD 'elige-una-clave-local'
    NOSUPERUSER NOCREATEROLE CREATEDB;
CREATE DATABASE taskplanner_dev OWNER taskplanner_app ENCODING 'UTF8';
```

### Configurar el archivo local

```powershell
Copy-Item .env.example .env
```

Genera una clave de Django y una clave maestra de 32 bytes para el cifrado de
adjuntos. Copia cada resultado a la variable correspondiente en `.env`; no
compartas esos valores ni los guardes en Git.

```powershell
.\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
.\.venv\Scripts\python.exe -c "import base64, secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

Completa también `POSTGRES_DB`, `POSTGRES_USER` y `POSTGRES_PASSWORD` con los
datos locales de la base. No reutilices contraseñas de personas o de otros
sistemas.

### Migrar y arrancar

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py crear_datos_demo
.\.venv\Scripts\python.exe manage.py cargar_datos_demo
.\.venv\Scripts\python.exe manage.py runserver
```

`crear_datos_demo` prepara las áreas y cuentas ficticias; `cargar_datos_demo`
crea tareas y adjuntos de ejemplo. Ambos comandos solo se ejecutan con `DEBUG`
activado. Para recuperar o crear una cuenta administrativa individual, el
responsable técnico puede usar `recuperar_admin --email <correo> --motivo
"Instalación local"`; la contraseña temporal se muestra una sola vez en la
salida del comando y debe cambiarse al iniciar sesión.

La aplicación queda disponible en `http://127.0.0.1:8000/`.

## 5. Variables de entorno

La tabla refleja todas las variables de `.env.example`. Los textos como
`replace-with-...` son marcadores de ejemplo, no credenciales válidas.

| Variable | Valor predeterminado de `.env.example` | Uso | Secreta |
|---|---|---|---|
| `SECRET_KEY` | `replace-with-a-generated-local-secret` | Clave criptográfica de Django; reemplazar por una generada. | Sí |
| `DEBUG` | `True` | Activa el modo de desarrollo local. | No |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Hosts aceptados por Django. | No |
| `POSTGRES_DB` | `taskplanner_dev` | Nombre de la base PostgreSQL. | No |
| `POSTGRES_USER` | `taskplanner_app` | Usuario de conexión de la aplicación. | No |
| `POSTGRES_PASSWORD` | `replace-with-a-local-password` | Contraseña del usuario PostgreSQL. | Sí |
| `POSTGRES_HOST` | `localhost` | Servidor de PostgreSQL. | No |
| `POSTGRES_PORT` | `5432` | Puerto de PostgreSQL. | No |
| `SESION_INACTIVIDAD_MINUTOS` | `15` | Inactividad máxima antes de expirar la sesión. | No |
| `SESION_DURACION_MAXIMA_HORAS` | `10` | Duración máxima absoluta de la sesión. | No |
| `DIAS_EN_RIESGO` | `2` | Días calendario para clasificar una tarea como en riesgo. | No |
| `ADJUNTOS_DIR` | Vacío; se usa `almacen_adjuntos` en el proyecto. | Directorio externo donde se guardan adjuntos. | No |
| `ADJUNTOS_CLAVE_MAESTRA` | Vacío | Clave maestra base64 para cifrar adjuntos restringidos. | Sí |
| `ADJUNTOS_TAMANO_MAX_MB` | `20` | Tamaño máximo permitido por adjunto. | No |
| `ANTIVIRUS_ACTIVO` | `False` | Activa o desactiva el análisis antivirus. | No |
| `ANTIVIRUS_COMANDO` | `clamdscan --no-summary --fdpass` | Comando usado cuando se activa el antivirus. | No |
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` | Backend de correo local o alternativo. | No |
| `EMAIL_HOST` | `localhost` | Servidor SMTP. | No |
| `EMAIL_PORT` | `1025` | Puerto SMTP; 1025 corresponde a Mailpit local. | No |
| `EMAIL_USE_TLS` | `False` | Indica si la conexión SMTP usa TLS. | No |
| `DEFAULT_FROM_EMAIL` | `TaskPlanner <notificaciones@proscience.local>` | Remitente de los correos. | No |
| `TASKPLANNER_URL_BASE` | `http://127.0.0.1:8000` | URL usada para construir enlaces de correo. | No |
| `NOTIFICACIONES_MAX_INTENTOS` | `5` | Máximo de intentos de envío antes de marcar el correo como fallido. | No |
| `NOTIFICACIONES_HORA_INICIO` | `7` | Hora local desde la que se generan recordatorios. | No |
| `GRAPH_TENANT_ID` | Vacío | Identificador del tenant de Microsoft Entra ID. | No |
| `GRAPH_CLIENT_ID` | Vacío | Identificador de la aplicación registrada para Graph. | No |
| `GRAPH_CLIENT_SECRET` | Vacío | Credencial de cliente para Microsoft Graph. | Sí |
| `GRAPH_REMITENTE` | Vacío | Buzón autorizado para enviar por Graph. | No |

`config/settings/base.py` carga `.env` con python-dotenv y configura PostgreSQL
con las variables de conexión enumeradas en la tabla; no se usa django-environ
ni una variable única de URL de conexión.

## 6. Correo en desarrollo

Mailpit captura los correos localmente. En este equipo está instalado en
`C:\Herramientas\mailpit`; escucha SMTP en el puerto `1025` y ofrece la bandeja
web en `http://localhost:8025/`.

```powershell
Start-Process -FilePath "C:\Herramientas\mailpit\mailpit.exe" -WorkingDirectory "C:\Herramientas\mailpit"
```

Comprueba que los puertos estén disponibles antes de probar notificaciones. Los
mensajes se quedan en Mailpit y no se entregan a los destinatarios. Al cerrar
con `Ctrl+C` la terminal donde se ejecuta Mailpit, el servicio se detiene.

## 7. Tareas programadas

En una terminal ejecuta una vez `programar_tareas` para crear o actualizar las
tareas periódicas. En otra terminal deja activo Django-Q2 con `qcluster`; ambos
procesos requieren que PostgreSQL esté encendido.

```powershell
.\.venv\Scripts\python.exe manage.py programar_tareas
.\.venv\Scripts\python.exe manage.py qcluster
```

La configuración de Django-Q2 en `config/settings/base.py` usa PostgreSQL como
cola. `programar_tareas` encola el envío de correos pendientes cada minuto y la
generación de recordatorios cada hora. El generador espera hasta
`NOTIFICACIONES_HORA_INICIO` (por defecto, las 7:00 en `America/Bogota`).

El calendario de recordatorios es:

| Momento | Aviso |
|---|---|
| Un día antes del vencimiento | `DIA_ANTERIOR` |
| Día del vencimiento | `VENCIMIENTO` |
| Primer día de atraso | `ATRASO` |
| Desde el octavo día de atraso y luego cada siete días | `ATRASO_SEMANAL` |

Los avisos diarios se envían a los responsables; el aviso semanal también se
envía a la Subgerente. Este destinatario semanal es provisional. No se generan
recordatorios para tareas completadas o eliminadas.

Para ejecutar operaciones manuales:

```powershell
.\.venv\Scripts\python.exe manage.py generar_recordatorios
.\.venv\Scripts\python.exe manage.py generar_recordatorios --forzar
.\.venv\Scripts\python.exe manage.py generar_recordatorios --fecha 2026-10-22
.\.venv\Scripts\python.exe manage.py enviar_notificaciones
```

`--forzar` omite la hora mínima y `--fecha` simula una fecha ISO (`AAAA-MM-DD`).
La bandeja de salida utiliza claves únicas y reintentos para evitar duplicados
y manejar fallos temporales.

## 8. Comandos de administración del proyecto

Estos son todos los comandos propios registrados en las aplicaciones del
proyecto. Los comandos `qcluster`, `migrate` y `runserver` pertenecen a Django o
Django-Q2, no son comandos propios de TaskPlanner.

| Comando | Función | Solo desarrollo |
|---|---|---|
| `recuperar_admin --email <correo> --motivo <texto>` | Crea o reactiva una cuenta Administrador normal, registra auditoría y entrega una contraseña temporal de cambio obligatorio. | No; solo lo ejecuta el responsable técnico. |
| `crear_datos_demo [--contrasena <valor>]` | Crea o actualiza áreas y cuentas ficticias, limpia bloqueos de acceso y permite iniciar sesión con los datos de demostración. | Sí; requiere `DEBUG=True`. |
| `cargar_datos_demo [--reiniciar] [--volumen N]` | Carga escenarios, estados y adjuntos de demostración; permite reiniciar escenarios o generar tareas para pruebas de volumen. | Sí; requiere `DEBUG=True`. |
| `programar_tareas` | Crea o actualiza, de forma idempotente, las tareas periódicas de envío y recordatorios. | No. |
| `generar_recordatorios [--forzar] [--fecha AAAA-MM-DD]` | Genera avisos de vencimiento para la fecha actual o una fecha de prueba. | No; `--forzar` y `--fecha` son útiles para pruebas. |
| `enviar_notificaciones [--limite N]` | Procesa los correos pendientes de la bandeja de salida. | No. |

Los comandos Django-Q2 disponibles para operar el proceso incluyen
`manage.py qcluster`. En desarrollo, utiliza Mailpit como backend SMTP.

## 9. Pruebas y calidad

Ejecuta los comandos desde la raíz con el intérprete del entorno virtual:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format .
.\.venv\Scripts\python.exe manage.py check
```

La suite actual contiene **298 pruebas**. La matriz de permisos está en
`tests/test_matriz_permisos.py`; `pytest --collect-only -q` permite consultar el
número de casos recogidos sin ejecutarlos.

## 10. Estructura del proyecto

```text
.
├── adjuntos/          # Validación, almacenamiento, cifrado y descarga de archivos
├── auditoria/         # Eventos de auditoría y consultas de auditoría
├── autorizacion/      # Reglas de acceso a tareas y contenido restringido
├── config/            # Configuración, URLs y arranque de Django
├── cuentas/           # Usuario propio, áreas, roles y comandos administrativos
├── docs/              # Decisiones y cambios documentales del proyecto
├── locale/            # Traducciones fuente .po y compiladas .mo
├── notificaciones/    # Bandeja de salida, Graph y recordatorios programados
├── scripts/           # Herramientas del proyecto, incluida la compilación de traducciones
├── static/            # CSS, JavaScript, Bootstrap y htmx locales
├── tareas/            # Tareas, asignaciones, vencimientos, panel y datos de demo
├── templates/         # Plantillas de páginas y correos
├── tests/             # Pruebas automatizadas
├── .env.example       # Plantilla de variables locales, sin credenciales reales
├── manage.py          # Interfaz de administración de Django
├── pyproject.toml     # Configuración de pytest y Ruff
└── requirements.txt   # Dependencias Python fijadas
```

## 11. Seguridad

- Las contraseñas se validan con un mínimo de 12 caracteres y se almacenan con
  Argon2. Una contraseña no debe parecerse al correo ni al nombre del usuario.
- django-axes bloquea intentos fallidos por cuenta y dirección IP. El límite
  configurado es de cinco fallos.
- Las sesiones expiran después de 15 minutos de inactividad y tienen una
  duración máxima absoluta de 10 horas.
- Los permisos dependen de grupos y reglas de tarea; las cuentas Administrador
  no son superusuarios de Django.
- Las tareas restringidas se muestran enmascaradas a quien no tenga permiso
  para ver el contenido. Los responsables siempre pueden ver las tareas que
  tienen asignadas.
- Se aceptan PDF, DOCX, XLSX, PNG y JPG, con validación de firma y un máximo
  predeterminado de 20 MB. Se rechazan macros y SVG. El análisis antivirus es
  configurable.
- Los adjuntos se guardan fuera del proyecto web. Los adjuntos restringidos se
  cifran con AES-256-GCM; al marcar una tarea como restringida se cifran también
  los adjuntos que ya tenía.
- La auditoría es de solo inserción y no guarda nombres de tareas, nombres de
  archivos ni contraseñas.
- Los correos de tareas restringidas usan un asunto y un cuerpo genéricos, sin
  incluir el título ni la descripción de la tarea.

## 12. Despliegue

El servidor de producción será Windows. Ver `docs/despliegue-windows.md` (fase
17, pendiente).

## 13. Problemas conocidos en Windows

- `pip freeze > archivo` en PowerShell puede escribir UTF-16. Para guardar el
  resultado en UTF-8, en un archivo temporal fuera del repositorio, usa:

  ```powershell
  .\.venv\Scripts\python.exe -c "import subprocess, sys, tempfile; from pathlib import Path; destino = Path(tempfile.gettempdir()) / 'taskplanner-freeze.txt'; destino.write_text(subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True), encoding='utf-8', newline='\n')"
  ```

- Las ventanas de incógnito de Chrome y Edge comparten cookies. Para probar
  varios usuarios, usa navegadores o perfiles distintos.
- `git diff` puede abrir un visor; sal con `q` o usa `git --no-pager diff`.
- `runserver` necesita PostgreSQL encendido. En esta instalación, el servicio es
  `postgresql-x64-18`.
- `Ctrl+C` en la terminal donde corre Mailpit lo detiene.
- No uses una contraseña que se parezca al correo o al nombre del usuario.
