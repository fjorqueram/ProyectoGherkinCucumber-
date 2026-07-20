# Auditoria de cobertura de resumenes

Esta auditoria compara archivos reales del proyecto contra documentos en `resumen`.

## Cubiertos individualmente

- `pyproject.toml` -> `resumen/pyproject_explicado.md`
- `requirements.txt` -> `resumen/requirements_explicado.md`
- `templates/feature.template.j2` -> `resumen/templates_feature_template_explicado.md`
- `src/ai_qa_gherkin/config.py` -> `resumen/ai_qa_gherkin/config_explicado.md`
- `src/ai_qa_gherkin/logger.py` -> `resumen/ai_qa_gherkin/logger_explicado.md`
- `src/ai_qa_gherkin/error.py` -> `resumen/ai_qa_gherkin/error_explicado.md`
- `src/ai_qa_gherkin/retry.py` -> `resumen/ai_qa_gherkin/retry_explicado.md`
- `src/ai_qa_gherkin/cli.py` -> `resumen/ai_qa_gherkin/cli_explicado.md`
- `src/ai_qa_gherkin/orchestrator.py` -> `resumen/ai_qa_gherkin/orchestrator_explicado.md`
- `src/ai_qa_gherkin/models/domain.py` -> `resumen/ai_qa_gherkin/models/domain_explicado.md`
- `src/ai_qa_gherkin/models/__init__.py` -> `resumen/ai_qa_gherkin/models/__init___explicado.md`
- `src/ai_qa_gherkin/clients/*.py` -> carpeta `resumen/ai_qa_gherkin/clients`
- `src/ai_qa_gherkin/services/*.py` -> carpeta `resumen/ai_qa_gherkin/services`
- `src/ai_qa_gherkin/prompts/gherkin_prompt.txt` -> `resumen/ai_qa_gherkin/prompts/gherkin_prompt_explicado.md`
- `src/ai_qa_gherkin/resources/domain_rules.json` -> `resumen/ai_qa_gherkin/resources/domain_rules_json_explicado.md`

## Cubiertos agrupados

- `src/ai_qa_gherkin/__init__.py`, `__main__.py`, `prompts/system_prompt.txt`, `resources/__init__.py` -> `resumen/ai_qa_gherkin/package_entrypoints_explicado.md`
- `src/ai_qa_gherkin/utils/*` -> `resumen/ai_qa_gherkin/utils/utilidades_explicado.md`
- `scripts/*` -> `resumen/scripts/scripts_resumen.md`
- `tests/*` -> `resumen/tests/tests_resumen.md`

## Archivos vacios documentados

- `Makefile`: existe pero esta vacio.
- `src/ai_qa_gherkin/__init__.py`: vacio.
- `src/ai_qa_gherkin/prompts/system_prompt.txt`: vacio.
- `src/ai_qa_gherkin/services/execution_service.py`: vacio.
- `src/ai_qa_gherkin/services/publish_service.py`: vacio.
- `src/ai_qa_gherkin/utils/traceability.py`: vacio.
- `src/ai_qa_gherkin/utils/text_utils.py`: vacio.

## Documentacion y configuracion de soporte

- `README.md` -> `resumen/readme_explicado.md`
- `AGENTS.md` -> `resumen/agents_explicado.md`
- `.env.example` -> `resumen/env_example_explicado.md`
- `comandos.txt` -> `resumen/comandos_explicado.md`
- `Makefile` -> `resumen/makefile_explicado.md`

## Pendientes conocidos

No quedan archivos de codigo, tests, scripts, prompts, recursos o soporte sin resumen identificado en esta auditoria.
