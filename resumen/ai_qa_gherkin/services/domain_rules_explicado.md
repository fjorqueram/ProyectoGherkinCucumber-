# Explicacion detallada de domain_rules.py

Este documento resume `src/ai_qa_gherkin/services/domain_rules.py`.

## Objetivo

`DomainRules` carga reglas configurables para que `GherkinService` renderice features con nombres, tags, reglas y reparaciones de texto acordes al dominio.

## Carga de datos

Constructor:

```python
def __init__(self, data: dict[str, Any] | None = None)
```

Si recibe `data`, la usa directamente.

Si no recibe, llama `_load_default()`.

## `_load_default`

Primero revisa la variable:

```text
GHERKIN_DOMAIN_RULES_FILE
```

Si existe, carga JSON desde ese path.

Si no, carga recurso empaquetado:

```text
ai_qa_gherkin.resources/domain_rules.json
```

## `feature_title`

Limpia `scope_summary`, normaliza acentos/minusculas y busca `feature_profiles`.

Si un perfil calza, retorna su `title`.

Si no, retorna el resumen limpio o un titulo por defecto.

## `feature_tags`

Parte con:

```python
["@regression"]
```

Agrega tags de perfiles y tags de escenarios.

Deduplica conservando orden con `dict.fromkeys`.

## `rule_for`

Busca en `rule_mappings`.

Si calza, retorna el nombre de regla.

Si no, retorna:

```text
Visualizacion de archivos complementarios
```

## `tags_for`

Siempre parte con `@funcional`.

Agrega tags segun `tag_mappings`.

## Reparaciones

- `text_replacements()`: mapa palabra -> reemplazo.
- `phrase_repairs()`: lista de regex/reemplazo.

## Extension outline

- `extension_rule_name()`: nombre de regla de extensiones.
- `extension_outline()`: headers y examples para scenario outline de iconos.

## `checkbox_action`

Devuelve accion especifica para checkbox.

Si detecta paginacion, retorna accion de seleccionar visibles en pagina.

Si no, retorna accion masiva default.

## `error_mapping`

Mapea textos de error a:

- contexto
- accion
- nombre del scenario

## `_matches`

Evalua dos listas:

- `match_any`: basta una coincidencia.
- `match_all`: deben estar todas.

Si no existen listas, se consideran cumplidas.
