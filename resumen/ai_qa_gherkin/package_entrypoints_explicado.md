# Explicacion de entrypoints y archivos vacios del paquete

Este documento resume archivos base del paquete `src/ai_qa_gherkin`.

## `src/ai_qa_gherkin/__init__.py`

Archivo vacio.

Marca `ai_qa_gherkin` como paquete Python.

## `src/ai_qa_gherkin/__main__.py`

Permite ejecutar el paquete como modulo:

```powershell
python -m ai_qa_gherkin
```

Importa:

```python
from ai_qa_gherkin.cli import cli
```

Y ejecuta `cli()` si el archivo corre como programa principal.

## `src/ai_qa_gherkin/prompts/system_prompt.txt`

Archivo vacio actualmente.

Parece reservado para un prompt de sistema futuro.

## `src/ai_qa_gherkin/resources/__init__.py`

Contiene solo docstring:

```python
"""Recursos versionables del paquete."""
```

Marca la carpeta `resources` como paquete importable por `importlib.resources`.

Esto es necesario para que `DomainRules` pueda cargar:

```python
files("ai_qa_gherkin.resources").joinpath("domain_rules.json")
```
