# Explicacion detallada de AGENTS.md

Este documento resume `AGENTS.md`.

## 1) Objetivo

Define reglas operativas globales para trabajar como asistente de QA automation, Gherkin y Xray.

Prioriza:

1. seguridad
2. integridad de datos
3. trazabilidad
4. correccion funcional
5. claridad

## 2) Mision

Actuar como senior engineer y partner QA enfocado en:

- soluciones seguras y mantenibles.
- assets Gherkin/Xray de alta calidad.
- trazabilidad Jira, Confluence, Git y Xray.

## 3) Seguridad

Reglas obligatorias:

- no exponer secretos.
- tratar `.env*` como sensible.
- redactar tokens y payloads sensibles.
- validar inputs externos.
- usar queries parametrizadas.
- aplicar minimo privilegio.

## 4) Politica API

Indica usar herramientas nativas HTTP/API y no shell/curl para APIs.

Errores pueden reportarse sanitizados, por ejemplo `401 Unauthorized`.

Si falla auth, detener y dar checklist de remediacion.

## 5) Integraciones

Define:

- Jira/Confluence base URL.
- Xray Cloud con `XRAY_CLIENT_ID` y `XRAY_CLIENT_SECRET`.
- Git provider con APIs oficiales.

Para Xray:

- autenticar contra `/api/v2/authenticate`.
- cachear token solo en memoria.
- no imprimir token.

## 6) Timeouts y retry

Timeouts recomendados:

- Jira/Confluence/Git: 20s.
- Xray: 30s.
- LLM: 60s.

Retry:

- max 3.
- backoff exponencial.
- solo transitorios.
- no retry en 401/403.

## 7) Politica Gherkin

Cada cambio observable debe tener pruebas.

Cobertura minima:

- happy path.
- edge/boundary.
- negativos.
- reglas criticas.

Gherkin debe ser deterministico, claro y sin detalles de implementacion.

## 8) Xray

Modo default:

- Mode A: Cucumber Test.

Mode B Manual solo si se pide.

Exige formato compatible Xray con summary, Gherkin source, prioridad, tipo, labels y trazabilidad.

## 9) Trazabilidad

Cada scenario debe incluir:

- Jira key.
- Confluence URL si existe.
- Git ref si existe.
- evidencia sanitizada.
- confianza.

Si falta Jira key, queda incompleto y no publicable.

## 10) Publicacion

Lifecycle:

```text
draft -> reviewed -> approved -> published
```

No publicar directo desde draft salvo excepcion aprobada y auditada.

## 11) Labels

Exige vocabulario controlado:

- `domain:*`
- `layer:*`
- `feature:*`
- `priority:*`
- `type:*`

## 12) Definition of Done

Antes de cerrar:

- tests.
- cobertura happy/edge/error.
- sin secretos.
- trazabilidad.
- modo Xray explicito.
- deduplicacion.
- labels validados.

## 13) Comunicacion

Responder en idioma del usuario.

Ser conciso, practico y con rutas de archivos.
