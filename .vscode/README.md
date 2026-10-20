# Agenda y Seguimiento de Tareas — ProScience

Sistema web interno para crear, asignar y supervisar las tareas de las áreas de ProScience. La Subgerencia General centraliza las tareas, las asigna a los líderes de área y el sistema calcula vencimientos y envía avisos por correo de forma automática.

## Estado del proyecto

**En desarrollo — etapa local en Windows.** El objetivo actual es una primera versión funcional ejecutándose en un equipo de desarrollo. Todavía no existe servidor ni despliegue en producción.

Este README describe cómo funcionará el sistema según los requerimientos aprobados. Cada sección se actualiza a medida que se completan las fases del plan de tareas; si un comando todavía no funciona, revisa en qué fase va el proyecto.

| Componente | Estado |
| --- | --- |
| Estructura del proyecto y configuración | Pendiente |
| Modelos, autenticación y roles | Pendiente |
| Tareas, vencimientos y panel de seguimiento | Pendiente |
| Sensibilidad, permisos y adjuntos | Pendiente |
| Auditoría | Pendiente |
| Correos en local (Mailpit) | Pendiente |
| Envío real con Microsoft Graph | **Bloqueado**: falta confirmar que el correo es Microsoft 365 |
| Antivirus (ClamAV) | **No probado**: desactivado en local |
| Despliegue en servidor | Fuera de esta etapa |

---

## Funcionalidades de la versión 1

- Inicio de sesión con correo y contraseña; cierre automático por inactividad.
- Gestión de usuarios, áreas y líderes por parte de los administradores (varios administradores posibles).
- Creación de tareas con nombre, descripción, uno o varios responsables, fecha límite, prioridad (Baja, Media, Alta) y nivel de sensibilidad.
- Estados de avance: Pendiente, En proceso, Completada. Solo la Subgerente los cambia.
- Situación temporal calculada automáticamente: En tiempo, En riesgo (2 días calendario o menos), Atrasada, Completada.
- Registro de cumplimiento al completar: fecha de finalización, dentro o fuera del plazo y quién completó.
- Panel de seguimiento con contadores, filtros (área, responsable, prioridad, estado, situación) y paginación.
- Eliminación lógica con papelera y recuperación.
- Adjuntos PDF, DOCX, XLSX, PNG y JPG con validación de tipo real, tamaño máximo y descarga controlada.
- Niveles de sensibilidad 1, 2 y 3; los adjuntos de nivel 3 se cifran.
- Correos automáticos: asignación, día anterior, día del vencimiento, atraso, recordatorio cada 7 días y finalización.
- Auditoría de las acciones importantes.

**Fuera del alcance de la v1:** subtareas, observaciones de responsables, exportación a Excel o PDF, informes avanzados y versión móvil.

---

## Tecnologías

Todo el software es gratuito y de licencia abierta.

| Capa | Tecnología |
| --- | --- |
| Lenguaje | Python 3.13 |
| Framework | Django 5.2 LTS |
| Base de datos | PostgreSQL 17 |
| Interfaz | Plantillas de Django, htmx 2 y Bootstrap 5.3 (servidos localmente, sin CDN) |
| Tareas programadas | Django-Q2, con PostgreSQL como cola |
| Correo en desarrollo | Mailpit (servidor SMTP de prueba) |
| Correo en producción | Microsoft Graph con OAuth, o SMTP cifrado (por confirmar) |
| Calidad y pruebas | pytest-django, coverage, Ruff, pip-audit |
| Control de versiones | Git + GitHub (repositorio privado) |

Librerías principales: `psycopg`, `django-environ`, `argon2-cffi`, `django-axes`, `django-q2`, `django-csp`, `filetype`, `cryptography` y `pip-tools`.

**Para el despliegue futuro (no se usan en local):** Debian 13, Gunicorn, Caddy, ClamAV, restic y GlitchTip.

---

## Requisitos previos (Windows)

| Herramienta | Versión | Comprobación |
| --- | --- | --- |
| Python (con el lanzador `py`) | 3.13.x | `py -3.13 --version` |
| Git para Windows | Reciente | `git --version` |
| PostgreSQL | 17 | `psql --version` |
| Visual Studio Code | Reciente | Extensiones: Python, Pylance, Ruff |
| Mailpit | Reciente | Ejecutable para Windows desde su página oficial |

Agrega `C:\Program Files\PostgreSQL\17\bin` a la variable `PATH` para usar `psql`, `pg_dump` y `pg_restore` desde la terminal.

Permite la activación de entornos virtuales en PowerShell (una sola vez):

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Instalación local

### 1. Clonar el repositorio

```powershell
git clone https://github.com/<organizacion>/<repositorio>.git
cd <repositorio>
```

### 2. Crear y activar el entorno virtual

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Crear la base de datos local

Abre `psql` como `postgres` y crea un usuario de aplicación **sin privilegios de superusuario**:

```sql
CREATE ROLE tareas_app WITH LOGIN PASSWORD 'cambia-esta-clave' NOSUPERUSER NOCREATEROLE CREATEDB;
CREATE DATABASE tareas_dev OWNER tareas_app ENCODING 'UTF8';
```

> `CREATEDB` se concede **solo en local**, porque las pruebas crean una base temporal. En producción el usuario de la aplicación no tendrá ese permiso.

### 4. Configurar las variables de entorno

```powershell
Copy-Item .env.example .env
```

Edita `.env` con tus valores (ver [Variables de entorno](#variables-de-entorno)). Genera las claves así:

```powershell
# SECRET_KEY de Django
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Clave maestra para cifrar adjuntos de nivel 3 (32 bytes en base64)
python -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

### 5. Aplicar migraciones

```powershell
python manage.py migrate
```

Las migraciones crean también los grupos **Administrador**, **Subgerente** y **Líder de área** con sus permisos.

### 6. Crear el primer administrador

No uses `createsuperuser`: un superusuario de Django salta todas las reglas de permisos, incluido el nivel 3. Usa el comando del proyecto, que crea un administrador normal con contraseña temporal:

```powershell
python manage.py recuperar_admin --email admin@ejemplo.local --motivo "Instalación inicial"
```

En el primer inicio de sesión el sistema pedirá cambiar la contraseña temporal.

### 7. (Opcional) Cargar datos de demostración

```powershell
python manage.py cargar_demo
```

Crea áreas, usuarios y tareas **ficticios** en todos los estados y niveles. Nunca uses datos reales en desarrollo.

---

## Variables de entorno

El archivo `.env` **nunca** se sube al repositorio. El repositorio solo incluye `.env.example` con valores de ejemplo.

| Variable | Descripción | Valor local de ejemplo |
| --- | --- | --- |
| `DJANGO_SETTINGS_MODULE` | Configuración a usar | `config.settings.local` |
| `SECRET_KEY` | Clave secreta de Django | *(generada)* |
| `DEBUG` | Modo depuración; solo `True` en local | `True` |
| `ALLOWED_HOSTS` | Nombres de host permitidos | `localhost,127.0.0.1` |
| `DATABASE_URL` | Conexión a PostgreSQL | `postgres://tareas_app:clave@localhost:5432/tareas_dev` |
| `SITE_URL` | URL base para los enlaces de los correos | `http://localhost:8000` |
| `ADJUNTOS_CLAVE_MAESTRA` | Clave de cifrado de adjuntos nivel 3 (solo desarrollo) | *(generada)* |
| `ADJUNTOS_TAMANO_MAX_MB` | Tamaño máximo por archivo | `20` |
| `ANTIVIRUS_ACTIVO` | Análisis antivirus de adjuntos | `False` |
| `SESION_INACTIVIDAD_MINUTOS` | Cierre de sesión por inactividad | `15` |
| `EMAIL_HOST` | Servidor SMTP | `localhost` |
| `EMAIL_PORT` | Puerto SMTP | `1025` (Mailpit) |
| `DEFAULT_FROM_EMAIL` | Remitente de los correos | `notificaciones@ejemplo.local` |

> La clave maestra de desarrollo **nunca** se reutiliza en producción. Si se pierde, los adjuntos de nivel 3 cifrados con ella no se pueden recuperar: guárdala aparte del proyecto.

Contenido de referencia para `.env.example`:

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.local
SECRET_KEY=cambia-esto
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://tareas_app:cambia-esta-clave@localhost:5432/tareas_dev
SITE_URL=http://localhost:8000
ADJUNTOS_CLAVE_MAESTRA=cambia-esto
ADJUNTOS_TAMANO_MAX_MB=20
ANTIVIRUS_ACTIVO=False
SESION_INACTIVIDAD_MINUTOS=15
EMAIL_HOST=localhost
EMAIL_PORT=1025
DEFAULT_FROM_EMAIL=notificaciones@ejemplo.local
```

---

## Ejecución

En desarrollo se necesitan tres procesos, cada uno en su propia terminal con el entorno virtual activado:

```powershell
# 1. Servidor de desarrollo de Django
python manage.py runserver

# 2. Tareas programadas (recordatorios y envío de correos)
python manage.py qcluster

# 3. Mailpit: recibe los correos sin enviarlos a nadie real
mailpit
```

| Servicio | Dirección |
| --- | --- |
| Aplicación | http://localhost:8000 |
| Bandeja de Mailpit | http://localhost:8025 |

> `runserver` es solo para desarrollo. En producción se usará Gunicorn detrás de Caddy, que no funcionan en Windows y se preparan en la etapa de despliegue.

Si `qcluster` presenta problemas en Windows, ejecuta los procesos programados manualmente mientras dure el desarrollo local:

```powershell
python manage.py generar_recordatorios
python manage.py enviar_notificaciones
```

---

## Pruebas y calidad

```powershell
# Pruebas
pytest

# Pruebas con cobertura
coverage run -m pytest
coverage report

# Estilo y errores comunes
ruff check .
ruff format --check .

# Vulnerabilidades conocidas en dependencias
pip-audit
```

Antes de subir cambios, las cuatro verificaciones deben pasar. Las pruebas incluyen la **matriz de permisos**: cada rol contra cada acción y cada nivel de sensibilidad.

---

## Estructura del proyecto

```text
.
├── config/                 # Proyecto Django
│   ├── settings/
│   │   ├── base.py         # Configuración común
│   │   ├── local.py        # Desarrollo en Windows
│   │   └── produccion.py   # Producción (se completa en la etapa de despliegue)
│   └── urls.py
├── cuentas/                # Usuario propio, áreas, roles, recuperar_admin
├── tareas/                 # Tareas, responsables, estados, vencimientos, panel
├── adjuntos/               # Subida, validación, cifrado y descarga controlada
├── autorizacion/           # Reglas de permisos por rol, tarea y nivel
├── notificaciones/         # Bandeja de salida, plantillas de correo, Django-Q2
├── auditoria/              # Registro de eventos
├── templates/              # Plantillas HTML
├── static/
│   └── vendor/             # Bootstrap y htmx locales
├── media/                  # Adjuntos (ignorado por Git, nunca servido directamente)
├── .env.example
├── .gitattributes
├── .gitignore
├── manage.py
├── pyproject.toml          # Configuración de Ruff y pytest
├── requirements.in         # Dependencias directas
├── requirements.txt        # Dependencias fijadas (generado con pip-tools)
└── README.md
```

---

## Roles y permisos

| Acción | Administrador | Subgerente | Líder de área |
| --- | --- | --- | --- |
| Gestionar usuarios, contraseñas y áreas | Sí | No | No |
| Ver tareas | Todas; nivel 3 solo como «restringida» | Todas | Solo las suyas |
| Crear y editar tareas | Niveles 1 y 2 | Sí | No |
| Cambiar estado y completar | No | Sí | No |
| Eliminar y recuperar | Sí | Sí | No |
| Adjuntar archivos | Niveles 1 y 2 | Sí | No |
| Conceder acceso a nivel 3 | No | Sí | No |

Los roles son grupos de Django y el código comprueba permisos, nunca nombres de rol. Ninguna cuenta opera como superusuario. El sistema impide desactivar al último administrador activo.

---

## Seguridad

- **Secretos:** nunca en el código ni en el repositorio. Todo se lee desde `.env`.
- **Contraseñas:** hash Argon2, mínimo 12 caracteres, bloqueo tras intentos fallidos.
- **Autorización:** se verifica en el backend en cada solicitud, por rol, por tarea y por nivel de sensibilidad. Un recurso ajeno responde «no encontrado».
- **Adjuntos:** tipo real verificado, sin macros ni SVG, nombre interno aleatorio, descarga solo a través de la aplicación; nivel 3 cifrado con AES-256-GCM.
- **Correos:** nunca incluyen la descripción de la tarea ni adjuntos; los de nivel 3 son genéricos.
- **Datos:** solo datos ficticios en desarrollo y en el repositorio.
- **Diferencias con producción:** `DEBUG`, claves, cookies seguras, HTTPS y antivirus se configuran de forma distinta en producción. Antes de desplegar debe pasar `python manage.py check --deploy` con la configuración de producción.

**Reportar un problema de seguridad:** comunícalo directamente al responsable técnico. No lo publiques en un *issue* del repositorio.

---

## Flujo de trabajo con Git

- `main` contiene siempre una versión que funciona y pasa las pruebas.
- Cada tarea del plan se trabaja en su propia rama, nombrada con su identificador:

```powershell
git switch -c feature/T7.1-crear-tarea
```

- Mensajes de commit claros, en español, con el tipo de cambio al inicio:

```text
feat: formulario de creación de tareas (T7.1)
fix: corrige cálculo de tareas que vencen hoy (T8.1)
test: matriz de permisos para adjuntos (T14.1)
docs: actualiza instrucciones de instalación
```

- Antes de unir una rama a `main`: pruebas, Ruff y pip-audit sin errores, y README actualizado si cambió algo de instalación o configuración.
- **Nunca** se suben: `.env`, la carpeta `media/`, respaldos, bases de datos, datos reales ni el entorno virtual.

---

## Actualizar dependencias

Las dependencias directas se declaran en `requirements.in` y las versiones exactas se fijan en `requirements.txt`:

```powershell
# Agregar o cambiar una dependencia: editar requirements.in y luego
pip-compile requirements.in

# Actualizar todas a sus últimas versiones compatibles
pip-compile --upgrade requirements.in

# Instalar lo fijado
pip install -r requirements.txt

# Verificar
pip-audit
pytest
```

Django se mantiene en la serie **5.2 LTS** (soporte de seguridad hasta abril de 2028). El salto a la siguiente versión LTS se planifica aparte.

Después de cambiar modelos:

```powershell
python manage.py makemigrations
python manage.py migrate
```

---

## Respaldo y restauración local

Un respaldo completo tiene tres partes: la base de datos, la carpeta `media/` y la clave maestra de adjuntos (guardada aparte).

```powershell
# Respaldar la base de datos
pg_dump -U tareas_app -d tareas_dev -F c -f respaldo_tareas.dump

# Respaldar los adjuntos
Compress-Archive -Path .\media\* -DestinationPath respaldo_media.zip

# Restaurar en una base nueva
createdb -U tareas_app tareas_restaurada
pg_restore -U tareas_app -d tareas_restaurada respaldo_tareas.dump
```

Los respaldos **no** se guardan dentro del repositorio. Los respaldos de producción (restic, copia fuera de la oficina) se definen en la guía de despliegue.

---

## Solución de problemas en Windows

| Problema | Solución |
| --- | --- |
| `Activate.ps1 cannot be loaded` | Ejecuta `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `psql` no se reconoce | Agrega `C:\Program Files\PostgreSQL\17\bin` al `PATH` y abre una nueva terminal |
| Error de conexión a PostgreSQL | Verifica que el servicio `postgresql-x64-17` esté iniciado y revisa `DATABASE_URL` |
| Las pruebas fallan al crear la base | El rol `tareas_app` necesita `CREATEDB` en local |
| `qcluster` no arranca o se detiene | Usa los comandos manuales de la sección [Ejecución](#ejecución) |
| Los correos no aparecen | Comprueba que Mailpit esté corriendo y que `EMAIL_PORT=1025` |
| Archivos con fin de línea mezclado | El `.gitattributes` fuerza LF; ejecuta `git add --renormalize .` |

---

## Hoja de ruta

1. Preparar Windows, Python, VS Code y Git.
2. Repositorio y estructura de Django.
3. PostgreSQL local.
4. Modelos y migraciones.
5. Autenticación y roles.
6. Usuarios, áreas y responsables.
7. Creación, asignación, edición y finalización de tareas.
8. Reglas de vencimiento.
9. Panel de seguimiento.
10. Niveles de sensibilidad y permisos.
11. Adjuntos y sus controles.
12. Auditoría.
13. Correos y tareas programadas.
14. Pruebas funcionales y de permisos.
15. Validación integral en Windows.
16. Documentación local.
17. Guía de despliegue (sin ejecutarla).

El detalle de cada tarea, sus dependencias y criterios de completado está en el plan de tareas técnicas.

---

## Decisiones pendientes

| Decisión | Valor provisional |
| --- | --- |
| ¿El correo @proscience es Microsoft 365? | Desarrollo con Mailpit |
| Destinatarios del recordatorio semanal de atraso | Responsables y Subgerente |
| Tamaño máximo de adjuntos | 20 MB |
| Tiempo de inactividad de la sesión | 15 minutos |
| ¿Se aceptan DOC y XLS antiguos? | No |
| ¿Se permite fecha límite anterior a la creación? | Por definir |
| ¿Se puede reabrir una tarea completada? | No en la v1 |
| Servidor de producción y mantenimiento | Por definir |

---

## Documentación relacionada

- Documento de requerimientos y requisitos del proyecto.
- Análisis funcional y técnico (arquitectura, seguridad, notificaciones, clasificación de la información).
- Plan de tareas técnicas para la versión local en Windows.

---

## Responsable y licencia

**Responsable técnico:** Pasante TI, ProScience.
**Solicitante:** Subgerencia General, ProScience.

Software de uso interno de ProScience. Todos los derechos reservados. Prohibida su copia, distribución o uso fuera de la empresa sin autorización.
