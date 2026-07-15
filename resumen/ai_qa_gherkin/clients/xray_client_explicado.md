# Explicacion detallada de xray_client.py

Este documento explica en detalle que hace `src/ai_qa_gherkin/clients/xray_client.py`, metodo por metodo, validacion por validacion y variable por variable.

---

## 1) Objetivo del archivo

El archivo implementa un cliente HTTP para comunicarse con Xray Cloud.

Su proposito es:

1. Autenticarse contra Xray usando `client_id` y `client_secret`.
2. Guardar temporalmente el bearer token en memoria durante la ejecucion.
3. Importar archivos `.feature` en formato Cucumber/Gherkin a Xray.
4. Importar resultados de ejecucion Cucumber JSON a Xray.
5. Clasificar errores como transitorios o permanentes.
6. Aplicar reintentos automaticos solo cuando el fallo parece recuperable.

Este cliente trabaja con el modo Xray Cucumber: el Gherkin es la fuente de verdad y los resultados se importan como Cucumber JSON.

---

## 2) Importaciones

```python
from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from ai_qa_gherkin.config import settings
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models import XrayImportResponse
from ai_qa_gherkin.retry import PermanentError, TransientError, retry_policy
```

### `from __future__ import annotations`

Permite que las anotaciones de tipos se evaluen de forma diferida.

En este archivo ayuda a usar tipos como:

```python
self.xray_token: str | None = None
```

Esto indica que `xray_token` puede ser un `str` o `None`.

### `from typing import Any`

`Any` representa un valor de cualquier tipo.

Se usa cuando la estructura exacta puede variar, por ejemplo:

```python
dict[str, Any]
```

Eso significa: diccionario con claves `str` y valores de cualquier tipo.

En este cliente se usa porque las respuestas JSON de Xray pueden contener distintos campos segun el endpoint y el resultado de la importacion.

### `from urllib.parse import quote`

`quote` codifica texto para que sea seguro dentro de una URL.

Se usa con `test_type_name`:

```python
quote(test_type_name)
```

Ejemplo:

- Valor original: `Cucumber Test`
- Valor codificado: `Cucumber%20Test`

Esto evita que espacios o caracteres especiales rompan la query string.

### `import httpx`

`httpx` es la libreria usada para hacer peticiones HTTP.

En este archivo se usa para:

1. Hacer `POST` al endpoint de autenticacion.
2. Hacer `POST` para importar features.
3. Hacer `POST` para importar resultados de ejecucion.
4. Detectar errores de timeout.
5. Detectar errores de red.

### `from ai_qa_gherkin.config import settings`

Importa la configuracion global del proyecto.

Desde `settings` este cliente lee:

- `settings.xray_base_url`
- `settings.xray_client_id`
- `settings.xray_client_secret`
- `settings.xray_timeout_seconds`

Estos valores normalmente vienen desde `.env`.

### `from ai_qa_gherkin.logger import get_logger`

Importa una funcion para construir un logger contextual.

El logger permite registrar eventos operacionales como:

- inicio de autenticacion
- importacion de una feature
- importacion de resultados

### `from ai_qa_gherkin.models import XrayImportResponse`

Importa el modelo que representa la respuesta interna al importar resultados de ejecucion.

El modelo tiene esta forma:

```python
class XrayImportResponse(BaseModel):
    success: bool
    payload: dict[str, Any] = Field(default_factory=dict)
```

En este cliente se usa en `import_execution_results`.

### `from ai_qa_gherkin.retry import PermanentError, TransientError, retry_policy`

Importa:

- `PermanentError`: error no reintentable.
- `TransientError`: error reintentable.
- `retry_policy`: decorador que reintenta automaticamente cuando ocurre un `TransientError`.

---

## 3) Logger contextual

```python
log = get_logger("xray_client")
```

Crea un logger identificado como `xray_client`.

Variable:

- `log`: objeto usado para escribir mensajes informativos.

Uso:

```python
log.info("Authenticating with Xray...")
```

Importante:

El codigo registra eventos, pero no imprime el token ni el `client_secret`, lo cual es correcto desde seguridad.

---

## 4) Clase `XrayClient`

```python
class XrayClient:
```

Esta clase encapsula toda la comunicacion con Xray.

La idea es que el resto del proyecto no tenga que saber:

- como autenticarse
- que endpoint usar
- como construir headers
- como enviar archivos
- como manejar errores HTTP
- como clasificar errores reintentables

---

## 5) Constructor `__init__`

```python
def __init__(self) -> None:
    self.base_url = settings.xray_base_url.rstrip("/")
    self.client_id = settings.xray_client_id
    self.client_secret = settings.xray_client_secret
    self.timeout = settings.xray_timeout_seconds
    self.xray_token: str | None = None
```

El constructor prepara el cliente con los valores de configuracion.

### Variable `self.base_url`

```python
self.base_url = settings.xray_base_url.rstrip("/")
```

Toma la URL base de Xray desde configuracion.

Valor por defecto en `config.py`:

```python
https://xray.cloud.getxray.app
```

Validacion/normalizacion:

```python
.rstrip("/")
```

Esto elimina barras `/` al final de la URL.

Ejemplos:

- Entrada: `https://xray.cloud.getxray.app/`
- Resultado: `https://xray.cloud.getxray.app`

Por que importa:

Luego el codigo concatena rutas como:

```python
f"{self.base_url}/api/v2/authenticate"
```

Si no se quitara la barra final, podria quedar:

```text
https://xray.cloud.getxray.app//api/v2/authenticate
```

### Variable `self.client_id`

```python
self.client_id = settings.xray_client_id
```

Guarda el identificador de cliente de Xray.

Origen:

```env
XRAY_CLIENT_ID
```

Uso:

Se envia en el body de autenticacion.

### Variable `self.client_secret`

```python
self.client_secret = settings.xray_client_secret
```

Guarda el secreto del cliente de Xray.

Origen:

```env
XRAY_CLIENT_SECRET
```

Uso:

Se envia en el body de autenticacion.

Nota de seguridad:

Es un secreto. No debe imprimirse, commitearse ni aparecer en logs.

### Variable `self.timeout`

```python
self.timeout = settings.xray_timeout_seconds
```

Define cuantos segundos esperara cada request HTTP antes de fallar por timeout.

Valor por defecto en `config.py`:

```python
30
```

Uso:

```python
httpx.Client(timeout=self.timeout)
```

### Variable `self.xray_token`

```python
self.xray_token: str | None = None
```

Guarda el bearer token devuelto por Xray despues de autenticarse.

Estados posibles:

- `None`: aun no hay token.
- `str`: ya existe un token autenticado.

Importante:

El token se guarda solo en memoria del objeto. No se escribe en archivos.

---

## 6) Metodo `_handle_error`

```python
def _handle_error(self, response: httpx.Response) -> None:
    if response.status_code in (429, 500, 502, 503, 504):
        raise TransientError(f"Xray transient: {response.status_code}: {response.text[:300]}")
    raise PermanentError(f"Xray permanent: {response.status_code}: {response.text[:300]}")
```

Este metodo centraliza como se interpretan respuestas HTTP fallidas.

Parametro:

- `response`: respuesta HTTP recibida desde Xray.

Tipo:

```python
httpx.Response
```

Retorno:

```python
None
```

En realidad, si hay error, este metodo no retorna normalmente: lanza una excepcion.

### Validacion `response.status_code in (429, 500, 502, 503, 504)`

```python
if response.status_code in (429, 500, 502, 503, 504):
```

Evalua si el codigo HTTP corresponde a un fallo posiblemente temporal.

Codigos considerados transitorios:

- `429`: demasiadas solicitudes o rate limit.
- `500`: error interno del servidor.
- `502`: bad gateway.
- `503`: servicio no disponible.
- `504`: gateway timeout.

Si el codigo esta en esa lista:

```python
raise TransientError(...)
```

Esto activa la politica de reintentos cuando el metodo que llama a `_handle_error` esta decorado con `@retry_policy()`.

### Error transitorio

```python
raise TransientError(f"Xray transient: {response.status_code}: {response.text[:300]}")
```

Construye un mensaje con:

- origen: `Xray`
- tipo: `transient`
- codigo HTTP
- primeros 300 caracteres del body de respuesta

La parte:

```python
response.text[:300]
```

limita el texto para no registrar respuestas completas.

### Error permanente

```python
raise PermanentError(f"Xray permanent: {response.status_code}: {response.text[:300]}")
```

Si el codigo no esta en la lista transitoria, el error se considera permanente.

Ejemplos tipicos:

- `400`: request invalida.
- `401`: autenticacion fallida.
- `403`: sin permisos.
- `404`: endpoint o recurso no encontrado.

Al lanzar `PermanentError`, la politica de retry no reintenta.

Nota de seguridad:

Aunque el texto se limita a 300 caracteres, conviene evitar mostrar cuerpos de respuesta con informacion sensible. Si Xray devolviera detalles delicados, estos podrian quedar en logs o errores.

---

## 7) Metodo `authenticate`

```python
@retry_policy()
def authenticate(self) -> str:
```

Este metodo autentica contra Xray y devuelve un bearer token.

Decorador:

```python
@retry_policy()
```

Significa que si dentro del metodo se lanza `TransientError`, se reintentara segun la configuracion del proyecto.

No reintenta si ocurre `PermanentError`.

### Variable `url`

```python
url = f"{self.base_url}/api/v2/authenticate"
```

Construye el endpoint de autenticacion.

Ejemplo final:

```text
https://xray.cloud.getxray.app/api/v2/authenticate
```

### Variable `payload`

```python
payload = {"client_id": self.client_id, "client_secret": self.client_secret}
```

Construye el cuerpo JSON que Xray espera para autenticar.

Contenido:

- `client_id`: identificador del cliente.
- `client_secret`: secreto del cliente.

Se envia como JSON en:

```python
client.post(url, json=payload)
```

Nota:

Este payload contiene secreto. El codigo no lo imprime.

### Log de autenticacion

```python
log.info("Authenticating with Xray...")
```

Registra que comenzo el proceso de autenticacion.

No registra credenciales ni token.

### Bloque `try`

```python
try:
```

Agrupa la llamada HTTP para capturar errores especificos de red o timeout.

### Cliente HTTP

```python
with httpx.Client(timeout=self.timeout) as client:
```

Crea un cliente HTTP temporal.

Variable:

- `client`: cliente usado para enviar la peticion.

Uso de `with`:

Al salir del bloque, el cliente se cierra automaticamente.

Timeout:

Usa `self.timeout`, que viene de `XRAY_TIMEOUT_SECONDS`.

### Variable `response`

```python
response = client.post(url, json=payload)
```

Ejecuta una peticion HTTP `POST`.

Envia:

- URL: endpoint de autenticacion.
- JSON: `payload`.

`response` contiene:

- status code
- headers
- body
- texto de respuesta
- JSON si corresponde

### Validacion `response.status_code >= 400`

```python
if response.status_code >= 400:
    self._handle_error(response)
```

Evalua si la respuesta HTTP representa error.

Regla:

- `100-399`: no entra en esta validacion.
- `400-599`: se considera fallo.

Si hay fallo:

1. Llama a `_handle_error(response)`.
2. `_handle_error` decide si es `TransientError` o `PermanentError`.
3. Si es transitorio, `@retry_policy()` puede reintentar.
4. Si es permanente, el metodo falla sin retry.

### Variable `token`

```python
token = response.text.strip().replace('"', "")
```

Xray devuelve el token como texto.

Este codigo limpia el valor recibido.

Partes:

```python
response.text
```

Obtiene el cuerpo como texto.

```python
.strip()
```

Elimina espacios, saltos de linea o tabulaciones al inicio y al final.

```python
.replace('"', "")
```

Elimina comillas dobles.

Esto se hace porque algunas respuestas de autenticacion pueden venir como string JSON con comillas, por ejemplo:

```text
"eyJhbGciOi..."
```

Luego queda:

```text
eyJhbGciOi...
```

### Validacion `if not token`

```python
if not token:
    raise PermanentError("Empty Xray token")
```

Comprueba que el token no este vacio.

Casos que fallan:

- `""`
- texto compuesto solo por espacios, porque antes se hizo `.strip()`

Por que es `PermanentError`:

Si Xray respondio sin token pero sin status de error, el cliente no puede continuar. Reintentar probablemente no solucionaria una respuesta invalida o inesperada.

### Asignacion `self.xray_token`

```python
self.xray_token = token
```

Guarda el token en memoria dentro del objeto.

Esto permite que otros metodos puedan reutilizarlo mediante `_auth_headers`.

### Retorno

```python
return token
```

Devuelve el token autenticado.

### Manejo de timeout

```python
except httpx.TimeoutException as e:
    raise TransientError(f"Xray timeout: {e}") from e
```

Si la peticion tarda mas que `self.timeout`, `httpx` lanza `TimeoutException`.

El codigo la transforma en `TransientError`.

Consecuencia:

Como `authenticate` tiene `@retry_policy()`, el timeout se reintenta.

### Manejo de error de red

```python
except httpx.NetworkError as e:
    raise TransientError(f"Xray network error: {e}") from e
```

Si ocurre un problema de red, se transforma en `TransientError`.

Ejemplos:

- DNS no resuelve.
- conexion interrumpida.
- fallo temporal de red.

Consecuencia:

Tambien puede activar retry.

---

## 8) Metodo `_auth_headers`

```python
def _auth_headers(self) -> dict[str, str]:
    if not self.xray_token:
        self.authenticate()
    return {"Authorization": f"Bearer {self.xray_token}"}
```

Este metodo construye el header de autorizacion para llamadas autenticadas.

Retorno:

```python
dict[str, str]
```

Es decir, un diccionario de strings.

### Validacion `if not self.xray_token`

```python
if not self.xray_token:
```

Verifica si el cliente ya tiene token.

Casos que entran:

- `self.xray_token is None`
- `self.xray_token == ""`

Si no hay token:

```python
self.authenticate()
```

El cliente se autentica antes de construir headers.

### Retorno del header

```python
return {"Authorization": f"Bearer {self.xray_token}"}
```

Construye:

```http
Authorization: Bearer <token>
```

Variable usada:

- `self.xray_token`: token guardado en memoria.

Nota:

Este metodo no valida expiracion del token. Solo verifica si existe. Si Xray responde luego con `401`, el error se tratara como permanente por `_handle_error`.

---

## 9) Metodo `import_feature_cucumber`

```python
@retry_policy()
def import_feature_cucumber(
    self,
    project_key: str,
    feature_text: str,
    test_type_name: str,
    file_name: str = "smoke.feature",
) -> dict[str, Any]:
```

Este metodo importa una feature Cucumber/Gherkin a Xray.

Se usa para crear o actualizar tests Cucumber en Xray a partir de texto `.feature`.

Decorador:

```python
@retry_policy()
```

Reintenta solo si se lanza `TransientError`.

### Parametro `project_key`

```python
project_key: str
```

Clave del proyecto Jira/Xray donde se importara la feature.

Ejemplo:

```text
QA
```

Se usa en la URL:

```python
?projectKey={project_key}
```

### Parametro `feature_text`

```python
feature_text: str
```

Contenido completo del archivo `.feature`.

Ejemplo conceptual:

```gherkin
Feature: Login
  Scenario: Given valid credentials When login Then access is granted
```

Se convierte a bytes UTF-8 antes de enviarlo.

### Parametro `test_type_name`

```python
test_type_name: str
```

Nombre del tipo de test en Xray.

Se agrega como query param:

```python
&testType={quote(test_type_name)}
```

Como puede tener espacios o caracteres especiales, se codifica con `quote`.

### Parametro `file_name`

```python
file_name: str = "smoke.feature"
```

Nombre del archivo que se enviara en el multipart upload.

Tiene valor por defecto:

```text
smoke.feature
```

No necesariamente debe existir como archivo fisico; aqui se usa como nombre dentro del upload.

### Variable `token`

```python
token = self.authenticate()
```

Autentica contra Xray y obtiene token.

Detalle importante:

Este metodo llama a `authenticate()` siempre, incluso si ya existe `self.xray_token`.

Eso significa que para cada importacion de feature se solicita un token nuevo.

### Variable `url`

```python
url = (
    f"{self.base_url}/api/v2/import/feature"
    f"?projectKey={project_key}"
    f"&testType={quote(test_type_name)}"
)
```

Construye la URL de importacion de features.

Partes:

1. Endpoint base:

```text
/api/v2/import/feature
```

2. Proyecto:

```text
?projectKey=<project_key>
```

3. Tipo de test:

```text
&testType=<test_type_name_codificado>
```

Ejemplo:

```text
https://xray.cloud.getxray.app/api/v2/import/feature?projectKey=QA&testType=Cucumber%20Test
```

### Variable `headers`

```python
headers = {"Authorization": f"Bearer {token}"}
```

Construye el header de autorizacion usando el token recien obtenido.

Resultado:

```http
Authorization: Bearer <token>
```

### Variable `files`

```python
files = {"file": (file_name, feature_text.encode("utf-8"), "text/plain")}
```

Construye el multipart file upload esperado por Xray.

Estructura:

```python
{
    "file": (
        file_name,
        feature_text.encode("utf-8"),
        "text/plain"
    )
}
```

Detalle por parte:

- `"file"`: nombre del campo multipart.
- `file_name`: nombre enviado para el archivo.
- `feature_text.encode("utf-8")`: contenido convertido a bytes.
- `"text/plain"`: MIME type del contenido.

Por que `encode("utf-8")`:

HTTP envia bytes, no texto Python puro. UTF-8 permite conservar acentos y caracteres especiales del Gherkin.

### Log de importacion

```python
log.info(
    f"Importing Cucumber feature to Xray project={project_key} testType={test_type_name}"
)
```

Registra:

- proyecto destino
- tipo de test

No registra el feature completo ni el token.

### Cliente HTTP

```python
with httpx.Client(timeout=self.timeout) as client:
```

Crea cliente HTTP con timeout configurado.

### Variable `response`

```python
response = client.post(url, headers=headers, files=files)
```

Hace un `POST` con:

- URL de importacion.
- Header bearer.
- Archivo multipart.

### Validacion `response.status_code >= 400`

```python
if response.status_code >= 400:
    self._handle_error(response)
```

Si Xray responde con error HTTP:

1. `_handle_error` clasifica el fallo.
2. `TransientError` permite retry.
3. `PermanentError` corta sin retry.

### Parseo JSON

```python
try:
    data = response.json()
    return data if isinstance(data, dict) else {"raw": data}
```

Primero intenta interpretar la respuesta como JSON.

Variable:

- `data`: resultado de `response.json()`.

Validacion:

```python
isinstance(data, dict)
```

Comprueba si el JSON recibido es un objeto/diccionario.

Si `data` es diccionario:

```python
return data
```

Si `data` es otro tipo, por ejemplo lista o string:

```python
return {"raw": data}
```

Esto normaliza la salida para que el metodo siempre retorne `dict[str, Any]`.

### Manejo de respuesta no JSON

```python
except ValueError:
    txt = response.text.strip()
    if txt:
        return {"raw": txt}
    raise PermanentError("Invalid Xray import response")
```

Si `response.json()` falla, `httpx` levanta `ValueError`.

Luego el codigo intenta rescatar texto plano.

Variable:

- `txt`: cuerpo de respuesta como texto, sin espacios al inicio o final.

Validacion:

```python
if txt:
```

Si hay texto, retorna:

```python
{"raw": txt}
```

Esto permite conservar una respuesta no JSON pero util.

Si no hay JSON ni texto:

```python
raise PermanentError("Invalid Xray import response")
```

Se considera error permanente porque la respuesta no tiene un formato util para continuar.

### Manejo de timeout

```python
except httpx.TimeoutException as e:
    raise TransientError(f"Xray timeout: {e}") from e
```

Si la importacion excede el timeout, se lanza `TransientError`.

Como el metodo tiene `@retry_policy()`, se reintentara.

### Manejo de error de red

```python
except httpx.NetworkError as e:
    raise TransientError(f"Xray network error: {e}") from e
```

Si falla la red, se transforma en error transitorio.

---

## 10) Metodo `import_execution_results`

```python
@retry_policy()
def import_execution_results(
    self, cucumber_json: dict[str, Any], project_key: str
) -> XrayImportResponse:
```

Este metodo importa resultados de ejecucion Cucumber JSON a Xray.

Se usa despues de ejecutar pruebas automatizadas y obtener un reporte Cucumber JSON.

Decorador:

```python
@retry_policy()
```

Reintenta ante `TransientError`.

### Parametro `cucumber_json`

```python
cucumber_json: dict[str, Any]
```

Representa el JSON de resultados Cucumber.

Puede incluir:

- features ejecutadas
- scenarios
- steps
- estados de ejecucion
- errores
- duraciones

Se envia como JSON en el body del request.

### Parametro `project_key`

```python
project_key: str
```

Clave del proyecto Jira/Xray donde se asociaran los resultados.

### Variable `url`

```python
url = f"{self.base_url}/api/v2/import/execution/cucumber"
```

Construye endpoint de importacion de resultados Cucumber.

Ejemplo:

```text
https://xray.cloud.getxray.app/api/v2/import/execution/cucumber
```

### Variable `params`

```python
params = {"projectKey": project_key}
```

Define los query parameters del request.

`httpx` lo convertira a:

```text
?projectKey=<project_key>
```

### Variable `headers`

```python
headers = {**self._auth_headers(), "Content-Type": "application/json"}
```

Construye los headers de la peticion.

Partes:

```python
self._auth_headers()
```

Devuelve:

```python
{"Authorization": "Bearer <token>"}
```

Luego:

```python
{**self._auth_headers(), "Content-Type": "application/json"}
```

Fusiona ese diccionario con:

```python
{"Content-Type": "application/json"}
```

Resultado:

```python
{
    "Authorization": "Bearer <token>",
    "Content-Type": "application/json"
}
```

Validacion indirecta:

Si no existe `self.xray_token`, `_auth_headers()` llama a `authenticate()`.

### Log de importacion

```python
log.info(f"Importing execution results to Xray project={project_key}")
```

Registra el proyecto destino.

No registra el JSON completo ni el token.

### Cliente HTTP con headers por defecto

```python
with httpx.Client(timeout=self.timeout, headers=headers) as client:
```

Crea cliente HTTP con:

- timeout configurado
- headers aplicados a sus requests

### Variable `response`

```python
response = client.post(url, params=params, json=cucumber_json)
```

Hace un `POST` al endpoint de resultados.

Envia:

- `params`: query string con `projectKey`.
- `json`: body con los resultados Cucumber.
- `headers`: authorization y content type desde el cliente.

### Validacion `response.status_code >= 400`

```python
if response.status_code >= 400:
    self._handle_error(response)
```

Si Xray devuelve error HTTP:

- se clasifica como transitorio o permanente
- si es transitorio, se puede reintentar
- si es permanente, se corta la ejecucion

### Retorno `XrayImportResponse`

```python
return XrayImportResponse(
    success=True,
    payload=response.json() if response.text else {},
)
```

Construye un objeto `XrayImportResponse`.

Campo `success`:

```python
success=True
```

Indica que la importacion fue exitosa desde el punto de vista HTTP.

Campo `payload`:

```python
payload=response.json() if response.text else {}
```

Validacion:

```python
if response.text
```

Si la respuesta tiene texto, intenta parsearlo como JSON.

Si la respuesta no tiene texto, usa diccionario vacio:

```python
{}
```

Nota:

A diferencia de `import_feature_cucumber`, aqui no hay `try/except ValueError` alrededor de `response.json()`. Si Xray devuelve texto no JSON con status exitoso, este metodo podria fallar con una excepcion de parseo.

### Manejo de timeout

```python
except httpx.TimeoutException as e:
    raise TransientError(f"Xray timeout: {e}") from e
```

Convierte timeouts en errores transitorios.

### Manejo de error de red

```python
except httpx.NetworkError as e:
    raise TransientError(f"Xray network error: {e}") from e
```

Convierte fallos de red en errores transitorios.

---

## 11) Flujo completo de autenticacion

Flujo normal:

1. Se instancia `XrayClient`.
2. El constructor carga `base_url`, credenciales y timeout.
3. Se llama `authenticate()`.
4. Se arma `url`.
5. Se arma `payload` con `client_id` y `client_secret`.
6. Se envia `POST`.
7. Si status code es `>= 400`, se llama `_handle_error`.
8. Si la respuesta es correcta, se limpia `response.text`.
9. Se valida que el token no este vacio.
10. Se guarda en `self.xray_token`.
11. Se devuelve el token.

---

## 12) Flujo completo de importacion de feature

Flujo normal:

1. Se llama `import_feature_cucumber`.
2. Se autentica y obtiene token.
3. Se construye la URL `/api/v2/import/feature`.
4. Se agregan query params `projectKey` y `testType`.
5. Se construye header bearer.
6. Se convierte el Gherkin a bytes UTF-8.
7. Se envia como archivo multipart.
8. Se valida status HTTP.
9. Se intenta parsear respuesta JSON.
10. Si no es JSON, se intenta devolver texto plano.
11. Si no hay respuesta util, se lanza `PermanentError`.

---

## 13) Flujo completo de importacion de resultados

Flujo normal:

1. Se llama `import_execution_results`.
2. Se construye URL `/api/v2/import/execution/cucumber`.
3. Se prepara `projectKey` como query param.
4. Se generan headers de autenticacion con `_auth_headers`.
5. Si no habia token, `_auth_headers` autentica.
6. Se envia el Cucumber JSON como body.
7. Se valida status HTTP.
8. Se retorna `XrayImportResponse(success=True, payload=...)`.

---

## 14) Validaciones existentes en el archivo

### Normalizacion de URL base

```python
settings.xray_base_url.rstrip("/")
```

Evita URLs con doble slash al concatenar endpoints.

### Clasificacion de errores transitorios

```python
response.status_code in (429, 500, 502, 503, 504)
```

Permite retry ante rate limit o fallos temporales.

### Clasificacion de errores permanentes

```python
raise PermanentError(...)
```

Evita reintentar errores que probablemente requieren correccion humana, como credenciales invalidas o permisos insuficientes.

### Validacion de status HTTP

```python
if response.status_code >= 400:
```

Detecta cualquier respuesta HTTP fallida.

### Validacion de token vacio

```python
if not token:
```

Impide guardar y usar un token vacio.

### Validacion de token existente

```python
if not self.xray_token:
```

Evita construir headers sin token.

### Codificacion de `test_type_name`

```python
quote(test_type_name)
```

Evita que espacios o caracteres especiales rompan la URL.

### Normalizacion de respuesta JSON en `import_feature_cucumber`

```python
return data if isinstance(data, dict) else {"raw": data}
```

Asegura que el metodo retorne un diccionario.

### Fallback a texto plano en `import_feature_cucumber`

```python
txt = response.text.strip()
if txt:
    return {"raw": txt}
```

Permite conservar respuestas exitosas que no vengan como JSON.

### Respuesta vacia en `import_execution_results`

```python
payload=response.json() if response.text else {}
```

Si Xray responde sin body, se devuelve payload vacio.

---

## 15) Variables principales y significado

| Variable | Donde aparece | Significado |
| --- | --- | --- |
| `log` | modulo | Logger contextual del cliente Xray. |
| `self.base_url` | constructor | URL base de Xray sin slash final. |
| `self.client_id` | constructor | ID de cliente para autenticacion Xray. |
| `self.client_secret` | constructor | Secreto de cliente para autenticacion Xray. |
| `self.timeout` | constructor | Timeout HTTP en segundos. |
| `self.xray_token` | constructor/autenticacion | Bearer token guardado en memoria. |
| `response` | metodos HTTP | Respuesta recibida desde Xray. |
| `url` | metodos HTTP | Endpoint final de Xray. |
| `payload` | `authenticate` | Body JSON con credenciales. |
| `token` | `authenticate`, `import_feature_cucumber` | Bearer token limpio. |
| `headers` | importaciones | Headers HTTP de autorizacion y/o content type. |
| `files` | `import_feature_cucumber` | Archivo `.feature` preparado como multipart. |
| `data` | `import_feature_cucumber` | Respuesta parseada como JSON. |
| `txt` | `import_feature_cucumber` | Respuesta como texto plano cuando no es JSON. |
| `params` | `import_execution_results` | Query params del request. |
| `cucumber_json` | `import_execution_results` | Resultados de pruebas en formato Cucumber JSON. |
| `project_key` | importaciones | Clave de proyecto Jira/Xray. |
| `test_type_name` | `import_feature_cucumber` | Tipo de test configurado en Xray. |
| `file_name` | `import_feature_cucumber` | Nombre del archivo enviado a Xray. |

---

## 16) Errores y reintentos

Los metodos decorados con `@retry_policy()` son:

```python
authenticate
import_feature_cucumber
import_execution_results
```

Estos metodos se reintentan solo si se lanza:

```python
TransientError
```

Casos que generan `TransientError`:

- HTTP `429`
- HTTP `500`
- HTTP `502`
- HTTP `503`
- HTTP `504`
- timeout de `httpx`
- error de red de `httpx`

Casos que generan `PermanentError`:

- HTTP `400`
- HTTP `401`
- HTTP `403`
- HTTP `404`
- token vacio
- respuesta invalida sin JSON ni texto util en importacion de feature

---

## 17) Seguridad del cliente

Buenas practicas presentes:

1. Las credenciales vienen desde `settings`, normalmente cargadas desde `.env`.
2. No se hardcodean secretos en el codigo.
3. No se imprime el `client_secret`.
4. No se imprime el bearer token.
5. El token se mantiene en memoria y no se persiste en archivos.

Puntos a vigilar:

1. `_handle_error` incluye `response.text[:300]` en el mensaje de error. Si la API devolviera informacion sensible, podria aparecer en logs.
2. `import_feature_cucumber` autentica en cada llamada; esto es seguro, pero menos eficiente.
3. `_auth_headers` no comprueba expiracion del token.
4. `import_execution_results` asume que una respuesta exitosa con body siempre sera JSON valido.

---

## 18) Resumen mental rapido

`XrayClient` hace tres cosas principales:

1. `authenticate()` obtiene un token de Xray.
2. `import_feature_cucumber()` sube una feature Gherkin a Xray.
3. `import_execution_results()` sube resultados Cucumber JSON a Xray.

La pieza clave es `_handle_error()`, porque decide si un fallo debe reintentarse o cortarse inmediatamente.

El token vive en:

```python
self.xray_token
```

Las credenciales vienen de:

```python
settings.xray_client_id
settings.xray_client_secret
```

Los errores recuperables se convierten en:

```python
TransientError
```

Los errores no recuperables se convierten en:

```python
PermanentError
```

Y `@retry_policy()` usa esa diferencia para decidir si vuelve a intentar o no.
