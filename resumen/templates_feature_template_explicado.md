# Explicacion detallada de templates/feature.template.j2

Este documento explica `templates/feature.template.j2`.

## 1) Objetivo

Es un template Jinja2 para renderizar una feature Gherkin.

Recibe variables como:

- `language`
- `tags`
- `feature_name`
- `description`
- `background`
- `scenarios`

## 2) Header de idioma

```jinja2
{% if language == 'es' %}
# language: es
{% else %}
# language: en
{% endif %}
```

Si `language` es `es`, genera header espanol.

En cualquier otro caso, genera ingles.

## 3) Tags de feature

```jinja2
{% for tag in tags %}
@{{ tag }}
{% endfor %}
```

Renderiza cada tag en una linea separada.

## 4) Feature

```jinja2
Caracteristica: {{ feature_name }}
  {{ description }}
```

Renderiza el nombre y descripcion de la feature.

Nota:

El template esta orientado a espanol; aunque el header pueda ser ingles, las keywords principales siguen en espanol.

## 5) Background

Si existe `background`, renderiza:

- `Antecedentes:`
- pasos `Dado`
- pasos `Cuando`
- pasos `Entonces`

Usa:

- `background.given`
- `background.when`
- `background.then`

## 6) Scenarios

Por cada scenario:

1. Renderiza sus tags.
2. Renderiza `Escenario: {{ scenario.name }}`.
3. Renderiza given con `Dado` para el primero y `Y` para los siguientes.
4. Renderiza when con `Cuando` para el primero y `Y` para los siguientes.
5. Renderiza then con `Entonces` para el primero y `Y` para los siguientes.

## 7) Relacion con el codigo actual

Actualmente `GherkinService` no usa este template.

El servicio genera Gherkin manualmente mediante concatenacion de strings en:

- `GherkinScenario.to_gherkin`
- `GherkinFeature.to_gherkin`

Este template parece preparado para una futura integracion con Jinja2.
