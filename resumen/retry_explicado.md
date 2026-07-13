# Explicación detallada de retry.py

Este documento explica en detalle qué hace [src/ai_qa_gherkin/retry.py](src/ai_qa_gherkin/retry.py): constantes, clases de error y configuración de reintentos, parte por parte.

## 1) Objetivo del archivo

El archivo centraliza la estrategia de reintentos del proyecto usando Tenacity.

Su propósito es:
1. Definir qué errores sí son reintentables.
2. Definir qué errores no se deben reintentar.
3. Configurar una política única de retry con tope de intentos y espera exponencial.
4. Registrar en logs cuándo se va a volver a intentar.

## 2) Importaciones y para qué se usa cada una

```python
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential, before_sleep_log
from loguru import logger
from ai_qa_gherkin.config import settings
```

1. retry
Decorador/fábrica principal de Tenacity para aplicar reintentos.

2. retry_if_exception_type
Condición de retry basada en tipo de excepción.

3. stop_after_attempt
Estrategia de parada: cortar tras N intentos.

4. wait_exponential
Estrategia de espera con backoff exponencial.

5. before_sleep_log
Hook para escribir log justo antes de dormir entre intentos.

6. logger
Logger de Loguru usado para registrar eventos de retry.

7. settings
Config global desde [src/ai_qa_gherkin/config.py](src/ai_qa_gherkin/config.py), de donde toma:
- retry_max_attempts
- retry_min_seconds
- retry_max_seconds

## 3) Constante TRANSIENT_HTTP_STATUS

```python
TRANSIENT_HTTP_STATUS = (429, 502, 503, 504)
```

Representa códigos HTTP transitorios que típicamente ameritan retry.

Qué significa cada uno:
1. 429: Too Many Requests (throttling/rate limit).
2. 502: Bad Gateway.
3. 503: Service Unavailable.
4. 504: Gateway Timeout.

Importante:
En este archivo la constante solo se declara; no se consume directamente en retry_policy().
Normalmente se usa en clientes HTTP para mapear respuestas a TransientError.

## 4) Clases de excepción

### 4.1 TransientError

```python
class TransientError(Exception):
    """Retryable error (timeouts, throttling, temporary upstream failures)."""
```

Semántica:
Error recuperable. Si se lanza esta excepción, la política sí reintenta.

Casos típicos:
- timeouts
- saturación temporal de API
- fallas intermitentes de red o upstream

### 4.2 PermanentError

```python
class PermanentError(Exception):
    """Non-retryable error (auth, permissions, invalid requests)."""
```

Semántica:
Error no recuperable por retry. Conceptualmente no debe reintentarse.

Casos típicos:
- 401 Unauthorized
- 403 Forbidden
- request inválida

Importante:
retry_policy() solo reintenta TransientError, por lo que PermanentError quedará fuera del retry automáticamente.

## 5) Función retry_policy()

```python
def retry_policy():
    return retry(
        reraise=True,
        stop=stop_after_attempt(settings.retry_max_attempts),
        wait=wait_exponential(
            multiplier=1,
            min=settings.retry_min_seconds,
            max=settings.retry_max_seconds
        ),
        retry=retry_if_exception_type(TransientError),
        before_sleep=before_sleep_log(logger, logger.level("WARNING").no),
    )
```

Esta función devuelve una configuración reutilizable de Tenacity.

Se usa típicamente como decorador:

```python
@retry_policy()
def llamada_externa(...):
    ...
```

### 5.1 reraise=True

Qué hace:
Después de agotar reintentos, vuelve a lanzar la excepción final.

Efecto:
No silencia errores; permite que capas superiores los manejen.

### 5.2 stop=stop_after_attempt(settings.retry_max_attempts)

Qué hace:
Limita la cantidad total de intentos.

Variable usada:
- settings.retry_max_attempts

Comportamiento:
Si vale 3, Tenacity intentará hasta 3 veces y luego fallará.

Validación implícita esperada:
Debe ser entero positivo para comportamiento correcto.

### 5.3 wait=wait_exponential(...)

Configura backoff exponencial entre intentos.

Parámetros:
1. multiplier=1
   Base de la exponencial.

2. min=settings.retry_min_seconds
   Espera mínima.

3. max=settings.retry_max_seconds
   Espera máxima.

Variables usadas:
- settings.retry_min_seconds
- settings.retry_max_seconds

Comportamiento práctico:
El tiempo de espera crece de forma exponencial pero nunca baja de min ni supera max.

### 5.4 retry=retry_if_exception_type(TransientError)

Qué valida:
Solo reintenta cuando la excepción sea del tipo TransientError (o subtipo).

Consecuencia:
- TransientError: sí retry.
- PermanentError: no retry.
- Cualquier otra excepción no contemplada: no retry, salvo que herede de TransientError.

### 5.5 before_sleep=before_sleep_log(logger, logger.level("WARNING").no)

Qué hace:
Antes de dormir entre reintentos, escribe un log.

Parámetros:
1. logger
   Instancia de Loguru para emitir mensaje.

2. logger.level("WARNING").no
   Nivel numérico WARNING.

Efecto:
Cada retry queda trazado, útil para observabilidad y diagnóstico.

## 6) Validación por validación (resumen)

Aquí no hay validadores tipo Pydantic, pero sí reglas efectivas de decisión:

1. Validación de tipo de error para reintentar
Regla: solo TransientError activa retry.

2. Validación de límite de intentos
Regla: máximo definido por retry_max_attempts.

3. Validación de ventana de espera
Regla: wait exponencial acotado por min y max.

4. Validación de propagación de error
Regla: al agotarse los intentos, se relanza excepción original/final.

## 7) Variables y elementos clave, uno por uno

1. TRANSIENT_HTTP_STATUS
Tupla de códigos HTTP transitorios potencialmente mapeables a TransientError.

2. settings.retry_max_attempts
Cantidad máxima de intentos.

3. settings.retry_min_seconds
Límite inferior de espera entre intentos.

4. settings.retry_max_seconds
Límite superior de espera entre intentos.

5. multiplier=1
Factor base del crecimiento exponencial.

6. logger
Registra advertencias antes de cada sleep de retry.

## 8) Flujo mental de ejecución

Cuando una función decorada con @retry_policy() falla:

1. Se captura la excepción.
2. Si es TransientError, se decide reintentar.
3. Se escribe log WARNING antes de esperar.
4. Espera según backoff exponencial (entre min y max).
5. Repite hasta llegar al máximo de intentos.
6. Si no se recupera, reraise=True relanza la excepción.

## 9) Qué no valida este archivo (importante)

Este módulo no valida por sí mismo:
1. Que retry_min_seconds <= retry_max_seconds.
2. Que retry_max_attempts sea > 0.
3. Conversión de tipos desde string de entorno (eso ocurre en config).
4. Mapeo HTTP -> excepción (eso debería ocurrir en clientes externos).

## 10) Conclusión práctica

[src/ai_qa_gherkin/retry.py](src/ai_qa_gherkin/retry.py) implementa una política de resiliencia clara:
1. Reintentar solo lo transitorio.
2. Frenar en errores permanentes.
3. Usar backoff exponencial acotado.
4. Mantener trazabilidad por logging.

Eso ayuda a evitar fallos intermitentes sin entrar en reintentos infinitos ni ocultar errores reales.
