# Explicación detallada de `config.py`

Este documento explica **qué hace el archivo de configuración** y cómo se comporta **variable por variable** y **validación por validación**.

---

## 1) Objetivo general del archivo

En `src/ai_qa_gherkin/config.py` se define una clase `Settings` que hereda de `BaseSettings` (de `pydantic-settings`).

Su objetivo es:

1. Leer configuración desde variables de entorno (y desde archivo `.env`).
2. Convertir esos valores al tipo correcto (`str`, `int`, etc.).
3. Aplicar valores por defecto cuando no existe valor en entorno.
4. Exponer una instancia única `settings = Settings()` para que el resto del proyecto use una configuración centralizada.

---

## 2) Importaciones

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
```

- `Field`: permite definir metadatos de cada variable (por ejemplo `alias`, `default`).
- `BaseSettings`: clase base que carga valores desde entorno y `.env`.
- `SettingsConfigDict`: configuración global de cómo se comporta `BaseSettings`.

---

## 3) Configuración global (`model_config`) y sus validaciones implícitas

```python
model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    case_sensitive=False,
    extra="ignore",
)
```

### 3.1 `env_file=".env"`
- Indica que también se leerán variables desde el archivo `.env` ubicado en la raíz del proyecto.
- Validación implícita: si una variable no está en sistema operativo, Pydantic intentará tomarla desde `.env`.

### 3.2 `env_file_encoding="utf-8"`
- Define codificación de lectura del `.env`.
- Evita errores por caracteres especiales.

### 3.3 `case_sensitive=False`
- No distingue mayúsculas/minúsculas al resolver variables de entorno.
- Ejemplo: `jira_base_url`, `JIRA_BASE_URL` o `Jira_Base_Url` pueden mapearse al mismo campo si el sistema lo permite.

### 3.4 `extra="ignore"`
- Si hay variables de entorno adicionales no definidas en la clase, se ignoran.
- Validación implícita: no falla por “campos extra”.

---

## 4) Cómo funciona cada campo (`Field`) internamente

Patrón usado:

```python
nombre_campo: tipo = Field(default=..., alias="NOMBRE_ENV")
```

Qué valida Pydantic en cada campo:

1. **Búsqueda por alias**: primero intenta leer la variable de entorno indicada en `alias`.
2. **Aplicación de default**: si no existe valor en entorno, usa `default` (o valor posicional en `Field("", alias=...)`).
3. **Conversión de tipo**: intenta convertir al tipo declarado (`str`, `int`, etc.).
4. **Error de validación**: si no puede convertir (por ejemplo texto no numérico en un `int`), lanza `ValidationError` al crear `Settings()`.

---

## 5) Variables explicadas una por una

## 5.1 Bloque App

### `app_name: str = "ai-qa-gherkin"`
- No usa alias de entorno.
- Siempre toma este valor por defecto salvo que se cambie en código.
- Validación: debe ser texto (`str`).

### `app_env: str = Field(default="dev", alias="APP_ENV")`
- Lee `APP_ENV`.
- Si no existe, usa `"dev"`.
- Validación: valor final debe ser `str`.
- Uso típico: `dev`, `qa`, `prod`.

### `log_level: str = Field(default="INFO", alias="LOG_LEVEL")`
- Lee `LOG_LEVEL`.
- Default: `"INFO"`.
- Validación: `str`.
- Nota: aquí no se restringe a lista cerrada (`INFO`, `DEBUG`, etc.); cualquier texto pasa como válido.

---

## 5.2 Bloque Jira

### `jira_base_url: str = Field("", alias="JIRA_BASE_URL")`
- Lee `JIRA_BASE_URL`.
- Default: cadena vacía `""`.
- Validación: `str`.
- Observación: no valida formato URL en este archivo.

### `jira_email: str = Field("", alias="JIRA_EMAIL")`
- Lee `JIRA_EMAIL`.
- Default: `""`.
- Validación: `str`.
- Observación: no valida formato de email aquí.

### `jira_api_token: str = Field("", alias="JIRA_API_TOKEN")`
- Lee `JIRA_API_TOKEN`.
- Default: `""`.
- Validación: `str`.
- Seguridad: el archivo no imprime ni expone el token; sólo lo carga.

### `jira_timeout_seconds: int = Field(default=20, alias="JIRA_TIMEOUT_SECONDS")`
- Lee `JIRA_TIMEOUT_SECONDS`.
- Default: `20`.
- Validación: convierte a entero.
- Si pones `JIRA_TIMEOUT_SECONDS=abc`, fallará la creación de `Settings()` por tipo inválido.

---

## 5.3 Bloque Confluence

### `confluence_base_url: str = Field("", alias="CONFLUENCE_BASE_URL")`
- Alias: `CONFLUENCE_BASE_URL`.
- Default: `""`.
- Validación: `str`.

### `confluence_email: str = Field("", alias="CONFLUENCE_EMAIL")`
- Alias: `CONFLUENCE_EMAIL`.
- Default: `""`.
- Validación: `str`.

### `confluence_api_token: str = Field("", alias="CONFLUENCE_API_TOKEN")`
- Alias: `CONFLUENCE_API_TOKEN`.
- Default: `""`.
- Validación: `str`.

### `confluence_timeout_seconds: int = Field(default=20, alias="CONFLUENCE_TIMEOUT_SECONDS")`
- Alias: `CONFLUENCE_TIMEOUT_SECONDS`.
- Default: `20`.
- Validación: entero.

---

## 5.4 Bloque Git Provider

### `git_provider: str = Field(default="github", alias="GIT_PROVIDER")`
- Alias: `GIT_PROVIDER`.
- Default: `"github"`.
- Validación: `str`.
- Observación: aquí no se fuerza enum (`github`/`gitlab`), por lo que cualquier string pasa.

### `git_api_base_url: str = Field("", alias="GIT_API_BASE_URL")`
- Alias: `GIT_API_BASE_URL`.
- Default: `""`.
- Validación: `str`.

### `git_token: str = Field("", alias="GIT_TOKEN")`
- Alias: `GIT_TOKEN`.
- Default: `""`.
- Validación: `str`.

### `git_timeout_seconds: int = Field(default=20, alias="GIT_TIMEOUT_SECONDS")`
- Alias: `GIT_TIMEOUT_SECONDS`.
- Default: `20`.
- Validación: entero.

---

## 5.5 Bloque Xray

### `xray_base_url: str = Field(default="https://xray.cloud.getxray.app", alias="XRAY_BASE_URL")`
- Alias: `XRAY_BASE_URL`.
- Default: URL base de Xray Cloud.
- Validación: `str`.
- Observación: no valida estructura URL (sólo tipo texto).

### `xray_client_id: str = Field("", alias="XRAY_CLIENT_ID")`
- Alias: `XRAY_CLIENT_ID`.
- Default: `""`.
- Validación: `str`.

### `xray_client_secret: str = Field("", alias="XRAY_CLIENT_SECRET")`
- Alias: `XRAY_CLIENT_SECRET`.
- Default: `""`.
- Validación: `str`.

### `xray_timeout_seconds: int = Field(default=30, alias="XRAY_TIMEOUT_SECONDS")`
- Alias: `XRAY_TIMEOUT_SECONDS`.
- Default: `30`.
- Validación: entero.

---

## 5.6 Bloque LLM

### `llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")`
- Alias: `LLM_PROVIDER`.
- Default: `"openai"`.
- Validación: `str`.

### `openai_api_key: str = Field("", alias="OPENAI_API_KEY")`
- Alias: `OPENAI_API_KEY`.
- Default: `""`.
- Validación: `str`.

### `openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")`
- Alias: `OPENAI_MODEL`.
- Default: `"gpt-4o-mini"`.
- Validación: `str`.

### `llm_timeout_seconds: int = Field(default=60, alias="LLM_TIMEOUT_SECONDS")`
- Alias: `LLM_TIMEOUT_SECONDS`.
- Default: `60`.
- Validación: entero.

---

## 5.7 Bloque Retry policy

### `retry_max_attempts: int = Field(default=3, alias="RETRY_MAX_ATTEMPTS")`
- Alias: `RETRY_MAX_ATTEMPTS`.
- Default: `3`.
- Validación: entero.

### `retry_min_seconds: int = Field(default=1, alias="RETRY_MIN_SECONDS")`
- Alias: `RETRY_MIN_SECONDS`.
- Default: `1`.
- Validación: entero.

### `retry_max_seconds: int = Field(default=8, alias="RETRY_MAX_SECONDS")`
- Alias: `RETRY_MAX_SECONDS`.
- Default: `8`.
- Validación: entero.

---

## 6) Validaciones que SÍ existen ahora

1. Conversión de tipos (`str`, `int`).
2. Uso de defaults si falta variable.
3. Lectura por alias de entorno.
4. Ignorar variables extra (`extra="ignore"`).

---

## 7) Validaciones que NO existen todavía (importante)

Actualmente este archivo **no valida**:

1. Que URLs sean válidas.
2. Que emails tengan formato correcto.
3. Que tokens/keys no estén vacíos.
4. Que `log_level` esté en conjunto permitido.
5. Que `git_provider` sea solo `github` o `gitlab`.
6. Que timeouts/retries sean positivos o consistentes (por ejemplo `retry_min <= retry_max`).

Esto significa que parte de la validación real puede estar en capas de servicio (clientes/orquestador), no en `config.py`.

---

## 8) Instanciación final

```python
settings = Settings()
```

Qué ocurre en esa línea:

1. Se crea una instancia única con toda la configuración.
2. Se ejecuta la carga de `.env` + variables de entorno.
3. Se aplican defaults.
4. Se ejecutan conversiones de tipo.
5. Si algún valor no cumple tipo esperado, falla en ese momento.

---

## 9) Flujo mental resumido de lectura de una variable

Ejemplo con `jira_timeout_seconds`:

1. Busca `JIRA_TIMEOUT_SECONDS` en entorno/.env.
2. Si existe, intenta convertirlo a `int`.
3. Si no existe, usa `20`.
4. Si no puede convertir, lanza error de validación.

---

## 10) Conclusión práctica

Tu `config.py` está bien estructurado para centralizar configuración y aplicar validación de tipos básica.

La validación fuerte de negocio (formatos, obligatorios, rangos, consistencia entre campos) todavía no está declarada aquí; por eso, si quieres mayor robustez, el siguiente paso natural sería agregar validadores de Pydantic para campos críticos.
