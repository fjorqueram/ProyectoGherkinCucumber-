# Explicacion detallada de resources/domain_rules.json

Este documento resume `src/ai_qa_gherkin/resources/domain_rules.json`.

## Objetivo

Configura reglas de dominio usadas por `DomainRules` y `GherkinService`.

Permite ajustar la generacion Gherkin sin cambiar codigo Python.

## `feature_profiles`

Define perfiles de feature.

Ejemplo:

- si el texto contiene `otros archivos`, usa titulo de visualizacion y acciones en otros archivos.
- agrega tags como `@antecedentes` y `@otros-archivos`.

## `rule_mappings`

Mapea palabras clave a nombres de `Regla:`.

Ejemplos:

- permisos -> `Visualizacion segun permisos`
- pagina -> `Paginacion`
- extension/icono -> `Iconos por extension`
- descargar -> `Lectura de archivos`
- eliminar -> `Escritura de archivos`

## `tag_mappings`

Mapea palabras clave a tags.

Ejemplos:

- permisos -> `@permisos`
- paginacion -> `@paginacion`
- configuracion regional -> `@i18n`
- extension/icono -> `@extensiones`
- descargar -> `@lectura`
- eliminar -> `@escritura`

## `text_replacements`

Diccionario para corregir palabras sin acento o normalizar terminos:

- `pestana` -> `pestana` con ene
- `extension` -> `extension` con acento
- `accion` -> `accion` con acento
- `pagina` -> `pagina` con acento

## `phrase_repairs`

Lista de regex para reparar frases cortadas o corruptas.

Ejemplos:

- `ar` -> `archivos complementarios`
- `correspo` -> `correspondiente`
- `sin permisos de visuali` -> `sin permisos de visualizacion`

## `extension_outline`

Define un scenario outline para iconos por extension.

Incluye:

- nombre de regla.
- nombre del esquema.
- headers: extension/icono.
- examples: PDF, JPG, PNG, TXT.

## `checkbox_actions`

Define texto de accion para seleccion multiple.

Tiene default y variante para paginacion.

## `error_mappings`

Mapea errores a escenarios concretos.

Ejemplos:

- descargar sin permisos de lectura.
- eliminar sin permisos de escritura.
- agregar sin permisos suficientes.
- restringir acceso sin permisos de visualizacion.
- rechazar datos invalidos.
- rechazar extension no soportada.
