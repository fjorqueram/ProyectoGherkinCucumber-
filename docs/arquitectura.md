# Arquitectura técnica — AI QA Gherkin Generator

Este documento describe la arquitectura interna, flujo de datos, contratos funcionales y decisiones técnicas del proyecto.

---

## 1. Objetivo técnico

Construir una tubería reproducible que:
1. recopile contexto funcional/técnico desde múltiples fuentes,
2. normalice señales,
3. genere escenarios Gherkin de calidad,
4. permita trazabilidad hacia Jira/GitHub/Xray.

---

## 2. Arquitectura lógica

```text
                    ┌───────────────────────┐
                    │      CLI / API        │
                    │   (entrada issueKey)  │
                    └───────────┬───────────┘
                                │
                                ▼
                      ┌───────────────────────┐
                      │   Context Builder     │
                      │ (orquesta fuentes)    │
                      └───────┬─────┬─────────┘
                              │     │
          ┌───────────────────┘     └───────────────────┐
          ▼                                             ▼
┌───────────────────────┐                     ┌───────────────────────┐
│      Jira Client      │                     │   Confluence Client   │
│ issue + AC + metadata │                     │ docs + reglas/flows   │
└───────────────────────┘                     └───────────────────────┘
                      ┌───────────────────────┐
                      │     GitHub Client     │
                      │ PR/branches/commits   │
                      └───────────────────────┘
                                │
                                ▼
                      ┌───────────────────────┐
                      │    Prompt Builder     │
                      └───────────────────────┘
                                │
                                ▼
                      ┌───────────────────────┐
                      │   LLM Provider Layer  │
                      │ github/azure/compat   │
                      └───────────────────────┘
                                │
                                ▼
                      ┌───────────────────────┐
                      │  Gherkin Generator    │
                      └───────────┬───────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                 ▼
        [.feature local output]          [Xray Publisher (opt)]
```

---

## 3. Componentes

## 3.1 `clients/jira_client.py`
Responsable de:
- obtener issue por key,
- leer descripción/ADF y criterios de aceptación,
- exponer metadata base para QA.

## 3.2 `clients/confluence_client.py`
Responsable de:
- ubicar documentación asociada,
- extraer contenido útil para reglas y flujos,
- resolver URL final con fallback robusto.

## 3.3 `clients/git_client.py`
Responsable de:
- búsqueda por issue key en PRs, ramas, commits,
- lectura de archivos modificados asociados,
- comparación contra rama base (`GIT_BASE_BRANCH`).

## 3.4 `clients/xray_client.py` (opcional)
Responsable de:
- publicar o sincronizar artefactos de prueba derivados.

## 3.5 `services/context_builder.py`
Responsable de:
- consolidar información de múltiples clientes,
- aplicar priorización de señales,
- generar un objeto `test_context` consistente.

## 3.6 `services/prompt_builder.py`
Responsable de:
- traducir `test_context` a prompt estructurado,
- inyectar reglas de dominio (JSON),
- controlar formato de salida esperado.

## 3.7 `services/gherkin_generator.py`
Responsable de:
- invocar provider LLM,
- validar salida mínima de estructura,
- producir `.feature` utilizable.

## 3.8 `resources/domain_rules.json`
Responsable de:
- tags por dominio,
- agrupación por `Regla:`,
- convenciones de redacción y escenarios especiales.

---

## 4. Contratos de datos sugeridos

## 4.1 `test_context` (conceptual)
```json
{
  "issue_key": "DYF-4275",
  "jira": {
    "summary": "...",
    "description": "...",
    "acceptance_criteria": ["..."]
  },
  "confluence": {
    "sources": ["url1", "url2"],
    "rules": ["..."],
    "flows": ["..."]
  },
  "github": {
    "repos_checked": ["imedcl/cme-cme"],
    "prs": [],
    "branches": [],
    "commits": [],
    "files": []
  },
  "quality_flags": {
    "missing_ac": false,
    "weak_technical_evidence": false
  }
}
```

## 4.2 `gherkin_output` (conceptual)
```json
{
  "feature_title": "Feature: ...",
  "rules": [],
  "scenarios": [],
  "traceability": {
    "issue_key": "DYF-4275",
    "source_count": 3
  }
}
```

---

## 5. Flujo detallado de ejecución

1. Recibe `issue_key`.
2. Consulta Jira.
3. Busca y parsea evidencia en Confluence.
4. Busca evidencia técnica en GitHub.
5. Compone `test_context`.
6. Aplica reglas de dominio.
7. Genera Gherkin con proveedor LLM configurado.
8. Exporta `.feature`.
9. Opcionalmente publica a Xray.

---

## 6. Estrategia de degradación controlada

- Si GitHub no encuentra evidencia: continuar con Jira/Confluence.
- Si un repo falla por permisos: marcar repo degradado y continuar con otros.
- Si `--use-llm` y falla provider: **fallar explícitamente** (sin fallback silencioso).

---

## 7. Configuración y runtime

Variables críticas:
- Jira: `JIRA_*`
- Confluence: `CONFLUENCE_*`
- GitHub: `GIT_*`
- Xray: `XRAY_*`
- LLM: `LLM_PROVIDER` + variables del proveedor.

---

## 8. Seguridad

- Nunca subir `.env`.
- Nunca loggear tokens.
- Aplicar mínimo privilegio en PAT/API keys.
- Rotación periódica de credenciales.

---

## 9. Observabilidad mínima recomendada

Registrar por ejecución:
- issue key,
- proveedor/modelo LLM,
- fuentes consultadas y estado,
- evidencias encontradas por repo,
- resultado final + razón de error (sanitizada).

---

## 10. Testing recomendado

- Unit tests:
  - parseo ADF Jira,
  - fallback URL Confluence,
  - heurística de búsqueda GitHub,
  - composición de prompt.
- Integration tests:
  - smokes por cliente (ya existentes),
  - ruta completa sin publicar.
- E2E:
  - generación `.feature` + validación de estructura.

---

## 11. Decisiones abiertas

- formato definitivo de salida `.feature`,
- estrategia de versionado de `domain_rules.json`,
- contrato de publicación a Xray (granularidad).

---

## 12. Próximos pasos técnicos

1. cerrar `build_test_context(issue_key)`,
2. estabilizar template prompt productivo,
3. agregar validadores de calidad de salida Gherkin,
4. integrar CI con lint/test/smokes controlados.