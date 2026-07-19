from ai_qa_gherkin.services.domain_rules import DomainRules
from ai_qa_gherkin.services.gherkin_service import GherkinService


def test_gherkin_service_uses_external_domain_rules():
    service = GherkinService(
        domain_rules=DomainRules(
            {
                "feature_profiles": [
                    {
                        "name": "login",
                        "match_any": ["login"],
                        "title": "Autenticación de usuarios",
                        "tags": ["@login", "@web"],
                    }
                ],
                "rule_mappings": [
                    {"name": "Autenticación", "match_any": ["credenciales"]}
                ],
                "tag_mappings": [
                    {"tag": "@autenticacion", "match_any": ["credenciales"]}
                ],
            }
        )
    )

    generated = service.generate_from_analysis(
        {
            "issue_key": "AUTH-1",
            "scope_summary": "Login de clientes",
            "raw": {
                "happy_paths": [
                    {
                        "name": "usuario ingresa credenciales validas",
                        "steps": [
                            "Dado que el usuario tiene credenciales validas",
                            "Cuando inicia sesion",
                            "Entonces accede al sistema",
                        ],
                    }
                ],
                "error_scenarios": [],
            },
        }
    )

    assert "Característica: Autenticación de usuarios" in generated.gherkin_text
    assert "@regression @login @web @autenticacion" in generated.gherkin_text
    assert "Regla: Autenticación" in generated.gherkin_text
