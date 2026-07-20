# Resumen de scripts

Este documento resume los archivos de `scripts`.

## `smoke_git_client.py`

Script CLI con `argparse` para probar `GitClient`.

Argumentos:

- `--owner`
- `--repo`
- `--issue-key`
- `--limit`

Busca commits por issue key y PRs relacionados, luego imprime SHA, mensaje, estado y URL.

## `smoke_confluence_client.py`

Script smoke para `ConfluenceClient`.

Uso:

```powershell
python scripts/smoke_confluence_client.py "DYF-4325" 5
```

Busca paginas por texto, imprime id, titulo, URL, largo de contenido y preview.

## `smoke_config.py`

Inicializa logger y verifica que `settings` carga.

Imprime ambiente y mensaje `Config + logger OK`.

## `debug_jira_fields.py`

Obtiene raw fields de una issue Jira hardcodeada (`DYF-4325`) y los imprime como JSON.

Punto de cuidado:

- Tiene issue fija; conviene parametrizar para evitar editar codigo.
- Imprime muchos campos raw, por lo que hay que cuidar datos sensibles.

## `smoke_xray_client.py`

Prueba importacion de feature a Xray.

Argumentos:

- `--project-key`
- `--test-type-name`
- `--feature-file`

Valida que el archivo exista, lee el `.feature` y llama `XrayClient.import_feature_cucumber`.

## `smoke_jira_client.py`

Prueba `JiraClient`.

Recibe issue key por argumento, imprime issue normalizada, preview de acceptance criteria y campos raw principales.

## `ssss.py`

Script directo con `requests` para probar token GitHub.

Lee:

```text
GIT_TOKEN
```

Consulta `/user`, repo y commits.

Punto de cuidado:

- Usa `requests` directo y no el cliente del proyecto.
- Imprime fragmentos de respuesta raw.
- Debe tratarse como script temporal/debug.
