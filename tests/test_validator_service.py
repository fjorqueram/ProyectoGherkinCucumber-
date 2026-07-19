import pytest

from ai_qa_gherkin.services.validator_service import (
    GherkinValidator,
    SeverityLevel,
    ValidationError,
    ValidationRule,
)


class TestValidationRule:
    def test_create_rule(self):
        rule = ValidationRule(
            rule_id="TEST_RULE",
            name="Test Rule",
            severity=SeverityLevel.ERROR,
            description="Test description",
        )
        assert rule.rule_id == "TEST_RULE"
        assert rule.severity == SeverityLevel.ERROR

    def test_rule_to_dict(self):
        rule = ValidationRule(
            rule_id="TEST",
            name="Test",
            severity=SeverityLevel.WARNING,
            description="Desc",
        )
        data = rule.to_dict()
        assert data["severity"] == "warning"


class TestValidationError:
    def test_create_error(self):
        rule = ValidationRule("ID", "Name", SeverityLevel.CRITICAL, "Desc")
        error = ValidationError(
            rule=rule,
            line_number=10,
            message="Error message",
            suggestion="Fix it",
        )
        assert error.line_number == 10
        assert error.message == "Error message"

    def test_error_to_dict(self):
        rule = ValidationRule("ID", "Name", SeverityLevel.ERROR, "Desc")
        error = ValidationError(rule, line_number=5, message="Test")
        data = error.to_dict()
        assert data["rule_id"] == "ID"
        assert data["severity"] == "error"
        assert data["line"] == 5


class TestGherkinValidator:
    def test_valid_gherkin(self):
        gherkin = """# language: es
Característica: Login
  Escenario: Login exitoso
    Dado que el usuario está en login
    Cuando ingresa credenciales válidas
    Entonces accede al sistema
"""
        validator = GherkinValidator()
        result = validator.validate(gherkin)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_missing_feature(self):
        gherkin = """
  Escenario: Test
    Dado precondición
    Cuando acción
    Entonces resultado
"""
        validator = GherkinValidator()
        result = validator.validate(gherkin)

        assert result.is_valid is False
        assert any(e["rule_id"] == "FEATURE_REQUIRED" for e in result.errors)

    def test_missing_scenario(self):
        gherkin = """Característica: Test Feature"""
        validator = GherkinValidator()
        result = validator.validate(gherkin)

        assert result.is_valid is False
        assert any(e["rule_id"] == "SCENARIO_REQUIRED" for e in result.errors)

    def test_missing_when_then(self):
        gherkin = """Característica: Test
  Escenario: Test Scenario
    Dado precondición
"""
        validator = GherkinValidator()
        result = validator.validate(gherkin)

        assert result.is_valid is False
        assert any(e["rule_id"] == "WHEN_THEN_REQUIRED" for e in result.errors)

    def test_ambiguous_step(self):
        gherkin = """Característica: Test
  Escenario: Test
    Dado test
    Cuando algo
    Entonces data
"""
        validator = GherkinValidator()
        result = validator.validate(gherkin)

        assert result.is_valid is False
        assert any(e["rule_id"] == "AMBIGUOUS_STEP" for e in result.errors)

    def test_unclear_scenario_name(self):
        gherkin = """Característica: Test
  Escenario: A
    Dado precondición
    Cuando acción
    Entonces resultado
"""
        validator = GherkinValidator()
        result = validator.validate(gherkin)

        # Nombre muy corto
        assert any(e["rule_id"] == "UNCLEAR_NAME" for e in result.errors)

    def test_outline_without_examples(self):
        gherkin = """Característica: Test
  Escenario Esquema: Template
    Dado usuario <nombre>
    Cuando intenta acceder
    Entonces ve resultado <estado>
"""
        validator = GherkinValidator()
        result = validator.validate(gherkin)

        assert result.is_valid is False
        assert any(e["rule_id"] == "MISSING_EXAMPLES" for e in result.errors)

    def test_outline_with_examples(self):
        gherkin = """Característica: Test
  Escenario Esquema: Template
    Dado usuario <nombre>
    Cuando intenta acceder
    Entonces ve resultado <estado>

  Ejemplos:
    | nombre | estado |
    | Juan   | OK     |
    | Maria  | OK     |
"""
        validator = GherkinValidator()
        result = validator.validate(gherkin)

        # No debería fallar por Examples
        assert not any(e["rule_id"] == "MISSING_EXAMPLES" for e in result.errors)

    def test_spanish_outline_alias_with_examples(self):
        gherkin = """Característica: Archivos
  Regla: Iconos por extensión
    Esquema del escenario: Mostrar icono segun tipo de archivo
      Dado que existe un archivo complementario con extensión "<extensión>"
      Cuando se muestra la tabla de archivos complementarios
      Entonces se renderiza el icono "<icono>" en la fila del archivo

      Ejemplos:
        | extensión | icono    |
        | PDF       | pdf-rojo |
"""
        validator = GherkinValidator()
        result = validator.validate(gherkin)

        assert result.is_valid is True
        assert not any(e["rule_id"] == "MISSING_EXAMPLES" for e in result.errors)

    def test_duplicate_steps(self):
        gherkin = """Característica: Test
  Escenario: Test
    Dado el usuario está autenticado
    Cuando ejecuta la acción
    Entonces obtiene resultado
    Y el usuario está autenticado
"""
        validator = GherkinValidator()
        result = validator.validate(gherkin)

        # Detecta duplicado
        assert any(e["rule_id"] == "DUPLICATE_SCENARIO" for e in result.errors)

    def test_coverage_validation(self):
        gherkin = """Característica: Login
  Escenario: Login
    Dado credenciales
    Cuando intenta
    Entonces accede
"""
        acceptance_criteria = [
            "Usuario debe poder autenticarse",
            "Debe validar contraseña",
            "Debe registrar intentos",
            "Debe bloquear tras 3 fallos",
        ]

        validator = GherkinValidator()
        result = validator.validate(gherkin, acceptance_criteria)

        # Cobertura baja
        assert any(e["rule_id"] == "INCOMPLETE_COVERAGE" for e in result.errors)

    def test_full_coverage(self):
        gherkin = """Característica: Login
  Escenario: Autenticación exitosa
    Dado usuario con credenciales válidas
    Cuando intenta autenticarse
    Entonces valida contraseña
    Y registra intento
    Y accede al sistema

  Escenario: Bloqueo tras fallos
    Dado usuario tras 3 intentos fallidos
    Cuando intenta nuevamente
    Entonces bloquea acceso
"""
        acceptance_criteria = [
            "Usuario debe poder autenticarse",
            "Debe validar contraseña",
            "Debe registrar intentos",
            "Debe bloquear tras 3 fallos",
        ]

        validator = GherkinValidator()
        result = validator.validate(gherkin, acceptance_criteria)

        # Cobertura alta
        assert not any(e["rule_id"] == "INCOMPLETE_COVERAGE" for e in result.errors)

    def test_summary_output(self):
        gherkin = """Característica: Test
  Escenario: Test Scenario
    Dado precondición
    Cuando acción
    Entonces resultado
"""
        validator = GherkinValidator()
        validator.validate(gherkin)
        summary = validator.get_summary()

        assert "Validation Summary" in summary
        assert "Total issues" in summary
        assert "Status" in summary
