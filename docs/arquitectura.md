# Arquitectura técnica detallada — AI QA Gherkin Generator

> Documento de referencia de diseño: cómo está construido el sistema, cómo fluye la información y qué decisiones garantizan trazabilidad y calidad en escenarios Gherkin.

---

## 1) Objetivo de arquitectura

Diseñar un pipeline que transforme una `issue key` (ej. `DYF-4275`) en un artefacto `.feature` confiable, usando evidencia real y auditable de:

- Jira (negocio y criterios),
- Confluence (reglas y flujos),
- GitHub (evidencia de implementación),
- Xray (opcional, publicación).

### Requisitos no funcionales clave

1. **Trazabilidad**: cada escenario debe poder justificarse con fuentes.
2. **Degradación controlada**: si una fuente falla, continuar cuando sea seguro.
3. **Determinismo parcial**: mismas entradas → estructura equivalente.
4. **Seguridad**: credenciales fuera de código, no exposición de secretos.
5. **Extensibilidad**: poder cambiar proveedor LLM sin romper la lógica central.

---

## 2) Vista de capas (Layered Architecture)

```text
┌─────────────────────────────────────────────────────────────────────┐
│                          INTERFAZ DE ENTRADA                        │
│  CLI / command handler (issue_key, flags, provider, output mode)   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      CAPA DE ORQUESTACIÓN                           │
│  PipelineCoordinator / UseCase: generate_feature(issue_key)         │
│  - ordena pasos                                                     │
│  - controla errores/degradaciones                                   │
│  - consolida resultado final                                        │
└─────────────────────────────────────────────────────────────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
│ CAPA DE INGESTA      │ │ CAPA DE NORMALIZACIÓN│ │ CAPA DE REGLAS       │
│ clients/*            │ │ context_builder      │ │ domain_rules engine   │
│ Jira/Conf/Git/Xray   │ │ merge + scoring      │ │ tags/reglas/outlines  │
└──────────────────────┘ └──────────────────────┘ └──────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CAPA DE GENERACIÓN                               │
│ prompt_builder + llm_provider_adapter + gherkin_generator          │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     CAPA DE SALIDA                                  │
│ .feature local + reporte de trazabilidad + (opcional) Xray publish  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3) Módulos y responsabilidades (explícito)

## 3.1 `clients/jira_client.py`
**Responsabilidad:** leer el requerimiento funcional primario.

### Entradas
- `issue_key`
- credenciales `JIRA_*`

### Salidas
- summary
- description (ADF/texto)
- acceptance criteria extraídos
- metadatos útiles (tipo, labels, etc.)

### Reglas
- si el issue no existe: error bloqueante.
- si AC no está claro: marcar `quality_flag.missing_ac=true`.

---

## 3.2 `clients/confluence_client.py`
**Responsabilidad:** traer documentación secundaria funcional/técnica.

### Estrategia
1. buscar links directos relacionados al issue,
2. buscar por título/key en espacios definidos,
3. parsear contenido útil (flujos, reglas, restricciones).

### Fallback de URL
1. `_links.base + _links.webui`
2. `CONFLUENCE_BASE_URL + webui`
3. `viewpage.action?pageId=<id>`

### Reglas
- si no encuentra docs: no bloquea; marca degradación informativa.

---

## 3.3 `clients/git_client.py`
**Responsabilidad:** recuperar evidencia de implementación real.

### Búsqueda por `issue_key`
- PRs con key en título/cuerpo
- ramas con key en nombre
- commits con key en mensaje
- archivos modificados de PRs detectados
- compare branch vs `GIT_BASE_BRANCH`

### Soporte multirepo
- `GIT_REPO` puede tener lista separada por coma.
- cada repo se evalúa de forma independiente.
- fallos por repo no rompen el total si hay evidencia parcial.

### Reglas
- 401/403 → error de configuración (token/permisos/SSO).
- 404 repo específico → degradación de ese repo.

---

## 3.4 `services/context_builder.py`
**Responsabilidad:** unificar señales heterogéneas en un `test_context` consistente.

### Funciones clave
- normalización de campos (texto limpio, listas, deduplicación),
- scoring de evidencia (qué fuente aporta qué),
- resolución de contradicciones (Jira vs Confluence vs GitHub),
- flags de calidad (falta AC, evidencia técnica débil, etc.).

### Principio
**Jira define el objetivo funcional**, GitHub y Confluence lo complementan.

---

## 3.5 `resources/domain_rules.json` + Rule Engine
**Responsabilidad:** codificar la política de redacción QA.

Ejemplos:
- cuándo usar `Regla:`,
- tags funcionales por dominio,
- patrones de escenarios de permisos/i18n/negativos,
- sugerencias de `Scenario Outline` para combinatorias.

### Beneficio
Permite ajustar comportamiento sin modificar Python.

---

## 3.6 `services/prompt_builder.py`
**Responsabilidad:** convertir `test_context` + reglas en prompt estructurado.

### Debe incluir
- objetivo de negocio,
- criterios de aceptación explícitos,
- restricciones técnicas,
- formato de salida estricto (Gherkin válido),
- política de no inventar campos ausentes.

---

## 3.7 `providers/*` (LLM Provider Adapter)
**Responsabilidad:** desacoplar proveedor del dominio.

### Contrato
- entrada: `PromptRequest`
- salida: `GenerationResult`
- manejo uniforme de errores/timeouts

### Proveedores esperados
- `github_models`
- `azure_openai`
- `openai_compatible`
- `ollama`

### Regla
Si `--use-llm` está activo y falla proveedor: **fallar explícitamente**.

---

## 3.8 `services/gherkin_generator.py`
**Responsabilidad:** generar y validar salida `.feature`.

### Validaciones mínimas
- existencia de `Feature:`
- escenarios no vacíos
- coherencia Given/When/Then
- estructura compatible con parser Gherkin

### Opcionales recomendadas
- lint de estilo,
- detección de duplicados semánticos.

---

## 3.9 `clients/xray_client.py` (opcional)
**Responsabilidad:** publicar resultado en Xray.

### Alcance
- crear/actualizar artefactos de test
- asociar con requirement Jira

### Regla
No bloquear generación local si Xray falla (dependiendo de modo de ejecución).

---

## 4) Secuencia operacional detallada (runtime)

```text
Usuario
  │
  │ gherkin generate DYF-4275 --use-llm
  ▼
CLI / Coordinator
  │
  ├─► JiraClient.get_issue(DYF-4275)
  │      └─► issue_data
  │
  ├─► ConfluenceClient.find_docs(DYF-4275, issue_data.summary)
  │      └─► docs_data (puede venir vacío)
  │
  ├─► GitClient.collect_evidence(DYF-4275, repos, base_branch)
  │      └─► gh_data (puede ser parcial por repo)
  │
  ├─► ContextBuilder.build(issue_data, docs_data, gh_data)
  │      └─► test_context + quality_flags
  │
  ├─► PromptBuilder.compose(test_context, domain_rules)
  │      └─► prompt_request
  │
  ├─► LLMProvider.generate(prompt_request)
  │      └─► gherkin_text
  │
  ├─► GherkinGenerator.validate_and_write(gherkin_text)
  │      └─► output.feature
  │
  └─► (opcional) XrayClient.publish(output.feature, issue_key)
         └─► publish_report
```

---

## 5) Contratos de datos (esquema conceptual)

## 5.1 `TestContext`
```json
{
  "issue_key": "DYF-4275",
  "business_goal": "string",
  "acceptance_criteria": ["string"],
  "functional_rules": ["string"],
  "technical_evidence": {
    "repos_checked": ["imedcl/cme-cme"],
    "prs": [{"id": 123, "title": "..."}],
    "branches": ["feature/DYF-4275"],
    "commits": [{"sha": "abc", "message": "..."}],
    "files": ["src/module/file.py"]
  },
  "risk_notes": ["string"],
  "quality_flags": {
    "missing_ac": false,
    "weak_technical_evidence": false,
    "confluence_not_found": false
  },
  "traceability": {
    "jira_issue_url": "https://...",
    "confluence_urls": ["https://..."],
    "github_urls": ["https://..."]
  }
}
```

## 5.2 `GenerationResult`
```json
{
  "feature_text": "Feature: ...",
  "scenario_count": 7,
  "warnings": [],
  "provider": "github_models",
  "model": "openai/gpt-4.1"
}
```

---

## 6) Política de errores y degradación

## Errores bloqueantes
- Jira inaccesible para `issue_key` objetivo.
- `--use-llm` activo y proveedor no responde.
- salida Gherkin inválida estructuralmente.

## Errores no bloqueantes (degradación)
- Confluence sin resultados.
- Un repo GitHub sin acceso cuando hay otros repos válidos.
- Xray opcional caído (si modo no estricto de publicación).

## Reporte recomendado
Siempre devolver:
- qué fuentes se consultaron,
- cuáles degradaron,
- impacto de cada degradación en cobertura.

---

## 7) Decisiones de diseño (ADR simplificadas)

1. **Multifuente antes de IA**: evita escenarios “alucinados”.
2. **Reglas de dominio externas (JSON)**: reduce costo de mantenimiento.
3. **Adapter de LLM**: portabilidad entre proveedores.
4. **Degradación controlada**: disponibilidad sin perder transparencia.
5. **Trazabilidad como output de primera clase**: auditoría QA.

---

## 8) Seguridad y cumplimiento

- Secretos solo en `.env` o secret manager.
- PAT con scopes mínimos.
- No loggear tokens ni payloads sensibles.
- Sanitizar errores antes de mostrarlos.
- Rotación periódica de credenciales.

---

## 9) Rendimiento y escalabilidad

- timeout configurable por cliente (`*_TIMEOUT_SECONDS`),
- ejecución concurrente de fuentes donde aplique,
- paginación en búsquedas GitHub,
- cache temporal de consultas repetidas por `issue_key` (opcional futuro).

---

## 10) Testing strategy

## Unit tests
- parsing ADF Jira,
- fallback URL Confluence,
- heurísticas de correlación GitHub por key,
- composición de prompt y aplicación de reglas.

## Integration tests
- smokes de clientes (`scripts/smoke_*`),
- test de `context_builder` con fixtures reales.

## E2E
- generación completa desde `issue_key` a `.feature`,
- verificación estructural Gherkin + trazabilidad.

---

## 11) Métricas de calidad sugeridas

- `% escenarios trazables` (con fuente explícita),
- `% AC cubiertos`,
- tasa de duplicados de escenarios,
- tiempo medio de generación por issue,
- tasa de ejecución exitosa por proveedor LLM.

---

## 12) Próximos pasos de arquitectura

1. cerrar `build_test_context(issue_key)` con contrato estable,
2. formalizar `schemas/` JSON para entradas/salidas,
3. agregar validador de Gherkin (lint + semántica),
4. definir modo estricto de publicación Xray,
5. exponer reporte de trazabilidad como artefacto separado (`trace.json`).