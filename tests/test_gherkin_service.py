import os
import tempfile

import pytest

from ai_qa_gherkin.services.gherkin_service import (
    GherkinFeature,
    GherkinScenario,
    GherkinService,
)


class TestGherkinScenario:
    def test_create_scenario(self):
        scenario = GherkinScenario(
            name="Test scenario",
            given=["User is logged in"],
            when=["User clicks button"],
            then=["Action is executed"],
        )
        assert scenario.name == "Test scenario"
        assert len(scenario.given) == 1

    def test_scenario_to_gherkin(self):
        scenario = GherkinScenario(
            name="Simple test",
            given=["precondition"],
            when=["action"],
            then=["result"],
            tags=["smoke"],
            language="en",  # ← especificar idioma
        )
        gherkin = scenario.to_gherkin()
        assert "Scenario: Simple test" in gherkin
        assert "Given precondition" in gherkin
        assert "When action" in gherkin
        assert "Then result" in gherkin
        assert "@smoke" in gherkin


class TestGherkinFeature:
    def test_create_feature(self):
        feature = GherkinFeature(
            feature_name="Login feature",
            description="User authentication",
            language="es",
        )
        assert feature.feature_name == "Login feature"
        assert feature.language == "es"

    def test_add_scenario(self):
        feature = GherkinFeature("Test")
        scenario = GherkinScenario(
            name="Test",
            given=["a"],
            when=["b"],
            then=["c"],
        )
        feature.add_scenario(scenario)
        assert len(feature.scenarios) == 1

    def test_set_background(self):
        feature = GherkinFeature("Test")
        feature.set_background(
            given=["User is on home page"],
        )
        assert feature.background_steps["given"] == ["User is on home page"]

    def test_feature_to_gherkin_es(self):
        feature = GherkinFeature(
            feature_name="Autenticación",
            description="Login de usuarios",
            language="es",
            tags=["smoke"],
        )
        feature.set_background(given=["Sistema disponible"])
        scenario = GherkinScenario(
            name="Login exitoso",
            given=["Usuario con credenciales válidas"],
            when=["Inicia sesión"],
            then=["Se autentica correctamente"],
        )
        feature.add_scenario(scenario)

        gherkin = feature.to_gherkin()
        assert "language: es" in gherkin
        assert "Característica: Autenticación" in gherkin
        assert "Antecedentes:" in gherkin
        assert "Escenario: Login exitoso" in gherkin
        assert "@smoke" in gherkin


class TestGherkinService:
    def test_generate_from_analysis(self):
        analysis = {
            "issue_key": "DYF-4307",
            "scope_summary": "Feature Xray",
            "business_rules": ["Must be valid", "Must import"],
            "raw": {
                "preconditions": [],
                "happy_paths": [],
                "error_scenarios": [],
            },
        }

        service = GherkinService()
        generated = service.generate_from_analysis(analysis)

        assert generated.feature_name == "Feature Xray"
        assert generated.source_issue_key == "DYF-4307"
        assert generated.language == "es"
        assert len(generated.gherkin_text) > 0
        assert generated.scenarios_count > 0

    def test_validate_gherkin_valid(self):
        gherkin = """# language: es
Característica: Test
  Escenario: Happy path
    Dado precondición
    Cuando acción
    Entonces resultado
"""
        service = GherkinService()
        valid, errors = service.validate_gherkin(gherkin)
        assert valid is True
        assert len(errors) == 0

    def test_validate_gherkin_invalid(self):
        gherkin = """Escenario: Sin Feature"""
        service = GherkinService()
        valid, errors = service.validate_gherkin(gherkin)
        assert valid is False
        assert len(errors) > 0

    def test_validate_gherkin_missing_keywords(self):
        gherkin = """Característica: Test
  Escenario: Test
    invalid step without keyword
"""
        service = GherkinService()
        valid, errors = service.validate_gherkin(gherkin)
        assert valid is False

    def test_save_feature_file(self):
        from ai_qa_gherkin.models import GeneratedFeature

        with tempfile.TemporaryDirectory() as tmpdir:
            service = GherkinService(output_dir=tmpdir)
            feature = GeneratedFeature(
                feature_name="Test",
                gherkin_text="# Test\nCaracterística: Test",
                source_issue_key="DYF-123",
            )

            filepath = service.save_feature_file(feature)

            assert os.path.exists(filepath)
            assert "DYF-123.feature" in filepath
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                assert "Característica: Test" in content

    def test_get_prompt_for_llm(self):
        analysis = {
            "issue_key": "DYF-123",
            "business_rules": ["Rule 1", "Rule 2"],
            "raw": {
                "preconditions": [{"precondition": "Precond 1"}],
                "happy_paths": [{"name": "Happy path 1"}],
                "error_scenarios": [{"description": "Error 1"}],
            },
        }

        service = GherkinService()
        prompt = service.get_prompt_for_llm(analysis)

        assert "Rule 1" in prompt
        assert "Precond 1" in prompt
        assert "Happy path 1" in prompt
        assert "Error 1" in prompt