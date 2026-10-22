# Registro de decisiones del proyecto

## Confirmadas

### Tres roles como grupos de Django
- **Decisión:** Administrador, Subgerente y Líder de área se representan como grupos; ninguna cuenta Administrador es superusuario.
- **Motivo:** aplicar permisos explícitos sin omitir las reglas de autorización del sistema.
- **Estado:** Confirmada.

### Responsables de tareas
- **Decisión:** los responsables de una tarea son líderes de área.
- **Motivo:** asignar y consultar el trabajo mediante la estructura organizativa.
- **Estado:** Confirmada.

### Vencimientos
- **Decisión:** los vencimientos se calculan en días calendario y zona `America/Bogota`. Una tarea está en riesgo cuando faltan dos días o menos, incluido el día del vencimiento (`DIAS_EN_RIESGO`); queda atrasada desde el día siguiente.
- **Motivo:** usar un umbral explícito y coherente con el calendario local.
- **Estado:** Confirmada.

### Estados
- **Decisión:** los estados son Pendiente, En proceso y Completada. Solo la Subgerente puede cambiarlos; no hay porcentajes de avance.
- **Motivo:** mantener un flujo de trabajo breve y verificable.
- **Estado:** Confirmada.

### Tareas completadas
- **Decisión:** las tareas completadas no se editan ni cambian de estado; no existe reapertura.
- **Motivo:** conservar el registro de finalización.
- **Estado:** Confirmada.

### Sensibilidad
- **Decisión:** hay dos niveles mediante la casilla «Información restringida», desmarcada por defecto. Se eliminaron los permisos explícitos; los responsables siempre ven su tarea.
- **Motivo:** simplificar la clasificación y el control de acceso al contenido restringido.
- **Estado:** Confirmada.

### Facultades del Administrador sobre tareas
- **Decisión:** el Administrador gestiona usuarios y áreas; puede crear y editar tareas no restringidas; ve las restringidas enmascaradas; puede eliminarlas y recuperarlas. No puede crear, marcar ni editar tareas restringidas, cambiar estados, completar tareas ni adjuntar archivos.
- **Motivo:** separar la administración de cuentas de la operación de tareas restringidas.
- **Estado:** Confirmada.

### Administración de usuarios por la Subgerente
- **Decisión:** la Subgerente no administra usuarios.
- **Motivo:** mantener la administración de cuentas bajo el rol Administrador.
- **Estado:** Confirmada.

### Restablecimiento de contraseñas
- **Decisión:** el Administrador restablece contraseñas con una clave temporal de cambio obligatorio; al restablecerla se cierran las sesiones del usuario.
- **Motivo:** exigir que la persona establezca su propia contraseña y revocar sesiones anteriores.
- **Estado:** Confirmada.

### Recuperación administrativa
- **Decisión:** la recuperación administrativa se realiza únicamente con el comando `recuperar_admin`, por el responsable técnico.
- **Motivo:** restringir y auditar una operación de contingencia.
- **Estado:** Confirmada.

### Avisos de cambio de rol privilegiado
- **Decisión:** los cambios de rol privilegiado (Administrador o Subgerente) se notifican solo a los demás administradores.
- **Motivo:** limitar la divulgación de cambios de privilegios.
- **Estado:** Confirmada.

### Adjuntos
- **Decisión:** se permiten PDF, DOCX, XLSX, PNG y JPG, con máximo de 20 MB configurable y validación por firma. Se rechazan macros y SVG; los archivos se guardan fuera del proyecto web. Los adjuntos de tareas restringidas se cifran con AES-256-GCM y, al restringir una tarea, se cifran sus adjuntos existentes. Solo la Subgerente adjunta.
- **Motivo:** validar los tipos aceptados y proteger archivos restringidos en reposo.
- **Estado:** Confirmada.

### Auditoría
- **Decisión:** la auditoría es de solo inserción y nunca guarda nombres de tareas, nombres de archivos ni contraseñas.
- **Motivo:** preservar un historial técnico minimizando datos sensibles.
- **Estado:** Confirmada.

### Correo
- **Decisión:** se usa una bandeja de salida con clave única y reintentos. Las tareas restringidas solo generan avisos genéricos. En desarrollo se usa Mailpit; en producción se usará Microsoft Graph con RBAC para aplicaciones de Exchange Online, limitado al buzón de notificaciones.
- **Motivo:** evitar duplicados, manejar fallos transitorios y no exponer información restringida por correo.
- **Estado:** Confirmada.

### Recordatorios
- **Decisión:** se envían avisos el día anterior, el día del vencimiento, el día siguiente y cada siete días de atraso. Se generan cada hora desde las 7:00; las tareas programadas usan Django-Q2 sobre PostgreSQL.
- **Motivo:** automatizar avisos periódicos usando la cola respaldada por la base de datos.
- **Estado:** Confirmada.

### Licencias de software
- **Decisión:** el software utilizado es 100 % gratuito y de licencia abierta.
- **Motivo:** mantener la solución sin costos de licenciamiento de software.
- **Estado:** Confirmada.

### Servidor de producción Windows
- **Decisión:** el servidor de producción será Windows, en lugar del plan inicial con Debian 13. Equivalencias: Waitress en lugar de Gunicorn; Caddy sin cambios; WinSW o NSSM en lugar de systemd; Microsoft Defender en lugar de ClamAV; BitLocker en lugar de LUKS; restic con el Programador de tareas; registros en archivo y en el Visor de eventos en lugar de GlitchTip.
- **Motivo:** decisión del proyecto de cambiar la plataforma del servidor.
- **Estado:** Confirmada.

## Provisionales

### Destinatarios del recordatorio semanal
- **Decisión:** los destinatarios del recordatorio semanal de atraso son responsables y Subgerente.
- **Motivo:** pendiente de confirmación definitiva.
- **Estado:** Provisional.

### Clasificación y conservación de información
- **Decisión:** la clasificación de la información y los plazos de conservación requieren revisión de Gerencia o del contador.
- **Motivo:** confirmar criterios de negocio y obligaciones de conservación.
- **Estado:** Provisional.

## Pendientes

### Recuperación de contraseña por correo
- **Decisión:** queda pendiente decidir la recuperación por correo; la recomendación es no implementarla.
- **Motivo:** decisión de seguridad aún no aprobada.
- **Estado:** Pendiente.

### Fecha límite anterior a la creación
- **Decisión:** validar que la fecha límite no sea anterior a la fecha de creación (D6).
- **Motivo:** pendiente de resolver como regla funcional.
- **Estado:** Pendiente.

### Reapertura de tareas completadas
- **Decisión:** decidir si se permite reabrir tareas completadas (D8).
- **Motivo:** pendiente de definición funcional.
- **Estado:** Pendiente.

### Segundo administrador para roles privilegiados
- **Decisión:** aprobar si se requiere un segundo administrador para asignar roles privilegiados.
- **Motivo:** definir un control de doble aprobación.
- **Estado:** Pendiente.

### Edición y licencia de Windows
- **Decisión:** elegir Windows 10/11 Pro o Windows Server para el servidor y confirmar su licencia.
- **Motivo:** falta definir la plataforma concreta y su licenciamiento.
- **Estado:** Pendiente.

### Mantenimiento y servidor
- **Decisión:** definir quién mantendrá el sistema y comprar el servidor.
- **Motivo:** asignar responsabilidades operativas y recursos.
- **Estado:** Pendiente.

### Activación de Microsoft Graph
- **Decisión:** activar Microsoft Graph para correo.
- **Motivo:** requiere la intervención de un administrador de Exchange.
- **Estado:** Pendiente.
