# Explicación detallada de error.py

Este documento explica en detalle qué hace [src/ai_qa_gherkin/error.py](src/ai_qa_gherkin/error.py), clase por clase y comportamiento por comportamiento.

## 1) Objetivo del archivo

El archivo define una jerarquía simple de errores de dominio para la aplicación.

Su propósito principal es:
1. Estandarizar cómo se representan errores internos del proyecto.
2. Diferenciar categorías de error para manejo más claro (configuración vs integración).
3. Permitir `except` más precisos en capas superiores (servicios, orquestador, CLI).

## 2) Contenido del archivo

Código actual:

```python
class AppError(Exception):
    """Base domain error."""
    
class ConfigurationError(AppError):
    """Invalid or missing configuration."""

class IntegrationError(AppError):
    """External integration failure."""
```

## 3) Explicación clase por clase

### 3.1 AppError

```python
class AppError(Exception):
    """Base domain error."""
```

Qué es:
Clase base para errores propios del dominio de la aplicación.

Qué hereda:
Hereda de `Exception`, por lo que es una excepción estándar de Python.

Para qué sirve:
1. Centralizar captura de errores de negocio con `except AppError`.
2. Separar errores de dominio de errores genéricos del runtime.

Comportamiento:
No redefine `__init__` ni agrega atributos; usa comportamiento estándar de Exception.

### 3.2 ConfigurationError

```python
class ConfigurationError(AppError):
    """Invalid or missing configuration."""
```

Qué es:
Subtipo especializado para fallos de configuración.

Casos típicos donde usarlo:
1. Variables de entorno obligatorias ausentes.
2. Valores de configuración inválidos.
3. Inconsistencias entre parámetros de configuración.

Ventaja:
Permite distinguir errores de arranque/configuración de otros errores de ejecución.

### 3.3 IntegrationError

```python
class IntegrationError(AppError):
    """External integration failure."""
```

Qué es:
Subtipo especializado para errores al interactuar con sistemas externos.

Casos típicos donde usarlo:
1. Fallos al consumir Jira/Confluence/Xray/Git.
2. Respuestas inválidas de APIs externas.
3. Problemas de red o disponibilidad de integraciones.

Ventaja:
Permite tratar de forma específica fallas de terceros sin mezclar con errores de configuración local.

## 4) “Validaciones” en este archivo

A diferencia de [src/ai_qa_gherkin/config.py](src/ai_qa_gherkin/config.py), aquí no hay validación de campos, tipos o rangos.

Lo que sí existe es una validación semántica por tipo de excepción:
1. Si lanzas `ConfigurationError`, comunicas causa de configuración.
2. Si lanzas `IntegrationError`, comunicas causa de integración externa.
3. Si capturas `AppError`, capturas ambas categorías de forma unificada.

## 5) Variables y atributos

En este módulo no hay variables globales, constantes ni atributos de clase personalizados.

Todas las clases usan el comportamiento por defecto de `Exception`, por lo que el mensaje del error se pasa normalmente al instanciar:

```python
raise ConfigurationError("Falta JIRA_API_TOKEN")
raise IntegrationError("Jira respondió 503")
```

## 6) Relación de herencia

```text
Exception
└── AppError
    ├── ConfigurationError
    └── IntegrationError
```

Qué permite esta jerarquía:
1. Captura específica:
```python
except ConfigurationError:
    ...
```

2. Captura grupal de dominio:
```python
except AppError:
    ...
```

## 7) Flujo típico de uso en el proyecto

1. Una capa detecta un problema (config o integración).
2. Lanza la excepción específica (`ConfigurationError` o `IntegrationError`).
3. Una capa superior decide respuesta (log, retry, salida controlada, etc.).

Ejemplo conceptual:

```python
if not settings.jira_api_token:
    raise ConfigurationError("JIRA_API_TOKEN no configurado")

if response.status_code >= 500:
    raise IntegrationError("Fallo temporal de Jira")
```

## 8) Conclusión práctica

[src/ai_qa_gherkin/error.py](src/ai_qa_gherkin/error.py) es pequeño, pero muy importante para arquitectura limpia.

Aporta:
1. Taxonomía de errores consistente.
2. Mejor legibilidad y trazabilidad en logs.
3. Manejo de excepciones más preciso en todo el sistema.

No valida datos por sí mismo; su valor está en clasificar correctamente el tipo de falla para que el resto del sistema reaccione de forma adecuada.
