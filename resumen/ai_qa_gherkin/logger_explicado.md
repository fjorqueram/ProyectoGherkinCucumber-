# Explicación detallada de `logger.py`

Este documento describe en detalle qué hace el archivo `src/ai_qa_gherkin/logger.py`, línea por línea, comportamiento por comportamiento y parámetro por parámetro.

---

## 1) Objetivo del archivo

`logger.py` centraliza la configuración de logs para toda la aplicación usando la librería **Loguru**.

Tiene dos responsabilidades principales:

1. Configurar el logger global (`setup_logger`).
2. Entregar loggers “enriquecidos” con contexto (`get_logger`) para que cada mensaje incluya datos útiles como servicio y operación.

---

## 2) Importaciones

```python
import sys
from loguru import logger
from ai_qa_gherkin.config import settings
```

### `import sys`
- Se usa para acceder a `sys.stdout`.
- `sys.stdout` es la salida estándar de consola donde se escribirán los logs.

### `from loguru import logger`
- Importa el logger global de Loguru.
- Este objeto permite remover sinks, agregar sinks nuevos, definir formato y escribir logs.

### `from ai_qa_gherkin.config import settings`
- Importa la configuración central del proyecto.
- Desde aquí se consumen:
  - `settings.log_level`
  - `settings.app_name`

---

## 3) Función `setup_logger()`

```python
def setup_logger():
    logger.remove()  # Remove the default logger

    logger.add(
        sys.stdout,
        level=settings.log_level.upper(),
        backtrace=False,
        diagnose=False,
        enqueue=True,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level} | "
            "{extra[service]} | "
            "{extra[operation]} | "
            "{message}"
        ),
    )
```

### 3.1 `logger.remove()`
- Quita el/los handlers (sinks) por defecto de Loguru.
- Objetivo: evitar formatos duplicados o configuración no controlada.
- Resultado: limpias la configuración previa y dejas sólo la que defines abajo.

### 3.2 `logger.add(...)`
Agrega un sink nuevo (destino + reglas) para el logger.

#### Parámetro 1: `sys.stdout`
- Destino de salida.
- Todos los logs irán a consola estándar (útil para ejecución local, contenedores y CI/CD).

#### `level=settings.log_level.upper()`
- Nivel mínimo de log que se emitirá.
- Toma `settings.log_level` (por ejemplo `info`) y lo convierte a mayúsculas (`INFO`).
- Comportamiento:
  - Si el nivel es `INFO`, se muestran `INFO`, `WARNING`, `ERROR`, etc.
  - Mensajes por debajo del nivel se filtran.
- Nota de validación:
  - Este archivo no valida que el nivel sea válido; depende de que en configuración venga uno correcto para Loguru.

#### `backtrace=False`
- Desactiva trazas extendidas de errores de Loguru.
- Efecto práctico:
  - Menos detalle interno al mostrar excepciones.
  - Logs más limpios y con menor exposición de internals.

#### `diagnose=False`
- Desactiva el diagnóstico profundo de variables locales en excepciones.
- Efecto práctico:
  - Mejora privacidad/seguridad al no volcar información sensible de contexto.
  - Menor verbosidad en errores.

#### `enqueue=True`
- Activa cola interna para logging asíncrono/thread-safe.
- Efecto práctico:
  - Menor bloqueo del hilo principal al escribir logs.
  - Más robusto en escenarios concurrentes.

#### `format=(...)`
Define formato de cada línea de log. Está compuesto por cinco bloques:

1. `{time:YYYY-MM-DD HH:mm:ss.SSS}`
   - Timestamp con milisegundos.
   - Ejemplo: `2026-07-09 19:45:12.153`.

2. `{level}`
   - Nivel del log (`INFO`, `ERROR`, etc.).

3. `{extra[service]}`
   - Campo de contexto llamado `service`.
   - Se espera que venga de `logger.bind(service=...)`.

4. `{extra[operation]}`
   - Campo de contexto llamado `operation`.
   - Se espera que venga de `logger.bind(operation=...)`.

5. `{message}`
   - Texto principal del evento de log.

Formato final esperado por línea:

```text
<time> | <level> | <service> | <operation> | <message>
```

---

## 4) Función `get_logger(operation: str = "general")`

```python
def get_logger(operation: str = "general"):
    return logger.bind(service=settings.app_name, operation=operation)
```

### 4.1 Parámetro `operation: str = "general"`
- Permite etiquetar el contexto de negocio/técnico del log.
- Si no envías nada, usa `"general"`.

### 4.2 `logger.bind(service=settings.app_name, operation=operation)`
- Devuelve un logger “hijo” con campos extra fijos:
  - `service`: nombre de app desde configuración (`settings.app_name`).
  - `operation`: el valor recibido por parámetro.
- Beneficio:
  - No tienes que repetir contexto en cada mensaje.
  - El formato definido en `setup_logger` puede consumir esos extras de forma consistente.

---

## 5) Flujo de uso correcto dentro del proyecto

Flujo típico:

1. Al iniciar la app, ejecutar `setup_logger()` una vez.
2. En cada módulo/servicio, pedir logger contextual: `log = get_logger("nombre_operacion")`.
3. Escribir mensajes: `log.info("...")`, `log.error("...")`, etc.

Si omites `setup_logger()`, Loguru puede usar su configuración por defecto (distinta al formato esperado por este proyecto).

---

## 6) “Validaciones” y garantías reales en este archivo

Aunque no hay validadores tipo Pydantic aquí, sí hay controles implícitos de comportamiento:

1. **Normalización de nivel** con `.upper()`.
2. **Estandarización de formato** al forzar un único `logger.add(...)` después de `logger.remove()`.
3. **Contexto obligatorio en diseño** (`service` y `operation`) porque el formato los exige.

---

## 7) Riesgos o puntos a vigilar

1. Si alguien loguea con `logger` directo (sin `get_logger`) y usa este formato, podrían faltar `extra[service]` o `extra[operation]`.
2. Si `settings.log_level` no es reconocido por Loguru, puede fallar al configurar.
3. Si `setup_logger()` se ejecuta múltiples veces, puede reconfigurar repetidamente el logger (aunque primero limpia con `remove()`).

---

## 8) Variables y valores usados (resumen rápido)

- `settings.log_level`
  - Fuente: configuración global.
  - Uso: definir umbral mínimo de logs.

- `settings.app_name`
  - Fuente: configuración global.
  - Uso: poblar campo `service` en cada logger contextual.

- `operation` (argumento de `get_logger`)
  - Fuente: llamada del consumidor.
  - Uso: poblar campo `operation` en formato de salida.

- `sys.stdout`
  - Fuente: módulo `sys`.
  - Uso: destino de impresión de logs.

---

## 9) Conclusión práctica

`logger.py` implementa una estrategia de logging limpia y consistente:

1. Configuración centralizada.
2. Formato homogéneo con contexto de servicio y operación.
3. Control de verbosidad por `LOG_LEVEL`.
4. Configuración más segura para producción (`diagnose=False`, `backtrace=False`).

En otras palabras, este archivo garantiza que los logs de tu sistema sean legibles, trazables y útiles para diagnóstico sin exponer demasiado detalle sensible.
