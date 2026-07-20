# Explicacion de la carpeta utils

Este documento resume los archivos en `src/ai_qa_gherkin/utils`.

## `__init__.py`

Archivo vacio.

Sirve para marcar `utils` como paquete Python.

## `traceability.py`

Archivo vacio actualmente.

Parece reservado para futuras utilidades de trazabilidad.

## `text_utils.py`

Archivo vacio actualmente.

Parece reservado para futuras utilidades generales de texto.

## `text_cleaner.py`

Define `TextCleaner`.

Objetivo:

- reparar mojibake/Unicode con `ftfy`.
- normalizar Unicode a NFC.
- preservar saltos de linea utiles para Gherkin.
- limpiar espacios raros como NBSP, zero-width y BOM.
- convertir tabs de indentacion a 4 espacios.
- reducir espacios repetidos sin romper indentacion.
- limitar saltos multiples a maximo dos.

Metodo principal:

```python
TextCleaner.clean(text: str, auto_learn: bool = False) -> str
```

`auto_learn` existe por compatibilidad, pero no se usa.

## `gherkin_text.py`

Define `GherkinText`, helpers compartidos para Gherkin.

Constantes:

- `STEP_KEYWORD_PATTERN`: detecta keywords de pasos.
- `STEP_PREFIXES`: prefijos validos.
- `SOURCE_TAGS`: mapea fuente a tag.
- `FALLBACK_STEPS`: pasos genericos.
- `DEDUPE_STOPWORDS`: palabras ignoradas para deduplicacion.
- `GENERIC_DEDUPE_STEPS`: pasos genericos que no ayudan a comparar.

Metodos principales:

- `source_tag`: fuente -> tag.
- `fallback_steps`: copia de pasos fallback.
- `strip_step_keyword`: quita keyword Gherkin.
- `is_step_line`: detecta si una linea es paso.
- `normalize_step`: normaliza paso para comparar.
- `normalize_scenario_name`: limpia nombre de scenario.
- `extract_steps`: extrae pasos desde texto.
- `scenario_tokens`: tokeniza scenario para similitud.
- `core_step_for_dedupe`: obtiene paso clave para deduplicar.
- `fold_accents`: remueve acentos.
- `normalize_spaces`: compacta espacios.
