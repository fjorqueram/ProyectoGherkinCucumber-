"""
Tests para AnalysisService.
Prueba análisis multisource de Jira, Confluence y Git.
"""
from __future__ import annotations
import pytest
from unittest.mock import Mock, patch
from ai_qa_gherkin.services.analysis_service import AnalysisService
from ai_qa_gherkin.models.domain import TraceabilityLink


class TestAnalysisService:
    """Suite de tests para AnalysisService."""
    
    @pytest.fixture
    def analysis_service(self):
        """Fixture que crea un AnalysisService."""
        return AnalysisService(use_llm=False)
    
    @pytest.fixture
    def mock_context_jira_only(self):
        """Fixture de contexto solo con Jira."""
        return {
            "issue": {
                "key": "DYF-4275",
                "issue_key": "DYF-4275",
                "summary": "Implementar validación de datos",
                "description": "Se necesita validar entrada y salida",
                "acceptance_criteria": """
                Escenario 1: Validación correcta
                Dado que ingreso datos válidos
                Cuando envío el formulario
                Entonces se guardan correctamente
                
                Escenario 2: Validación de errores
                Dado que ingreso datos inválidos
                Cuando envío el formulario
                Entonces veo mensaje de error
                """,
                "links": ["DYF-123"],
                "raw": {}
            },
            "confluence": {},
            "git": {}
        }
    
    @pytest.fixture
    def mock_context_multisource(self):
        """Fixture de contexto con múltiples fuentes."""
        return {
            "issue": {
                "key": "DYF-4275",
                "issue_key": "DYF-4275",
                "summary": "Implementar validación de datos",
                "description": "Se necesita validar entrada y salida",
                "acceptance_criteria": """
                Escenario 1: Validación correcta
                Dado que ingreso datos válidos
                Cuando envío el formulario
                Entonces se guardan correctamente
                """,
                "links": [],
                "raw": {}
            },
            "confluence": {
                "page_id": "123456",
                "page_title": "First Time User Guide",
                "page_url": "https://confluence.example.com/wiki/pages/123456",
                "content": "Guía de usuario nuevo",
                "user_steps": [
                    "Crear una cuenta",
                    "Validar correo",
                    "Completar perfil"
                ],
                "step_count": 3,
            },
            "git": {
                "owner": "fjorqueram",
                "repo": "ProyectoGherkinCucumber",
                "commits": [
                    {
                        "sha": "abc1234",
                        "message": "fix(DYF-4275): Bug in validation",
                        "url": "https://github.com/owner/repo/commit/abc1234"
                    }
                ],
                "commit_count": 1,
                "prs": [],
                "pr_count": 0,
                "changed_files": ["src/validation.ts"],
                "test_scenarios": ["Ejecutar tests"]
            }
        }
    
    # ===== TESTS DE ANÁLISIS JIRA =====
    
    def test_analyze_jira_only(self, analysis_service, mock_context_jira_only):
        """Test: Analizar solo contexto de Jira."""
        # Act
        result = analysis_service.analyze(mock_context_jira_only)
        
        # Assert
        assert result["issue_key"] == "DYF-4275"
        assert "Implementar validación" in result["scope_summary"]
        assert len(result["business_rules"]) > 0
        assert len(result["raw"]["happy_paths"]) > 0
        assert len(result["raw"]["happy_paths"]) >= 2  # 2 escenarios
    
    def test_extract_scenarios_from_jira(self, analysis_service, mock_context_jira_only):
        """Test: Extraer escenarios desde Jira."""
        # Arrange
        analysis_service._extract_from_jira(
            mock_context_jira_only["issue"],
            TraceabilityLink(
                source_type="jira",
                source_id="DYF-4275",
                source_name="Test"
            )
        )
        
        # Assert
        assert len(analysis_service.happy_paths) >= 2
        for hp in analysis_service.happy_paths:
            assert hp.source == "jira"
            assert len(hp.steps) >= 2
            assert any(step.lower().startswith(kw) for step in hp.steps 
                      for kw in ["dado", "cuando", "entonces"])
    
    def test_extract_gherkin_steps(self, analysis_service):
        """Test: Extraer pasos Gherkin de texto."""
        # Arrange
        text = """
        Validación correcta
        Dado que ingreso datos válidos
        Cuando envío el formulario
        Entonces se guardan correctamente
        """
        
        # Act
        steps = analysis_service._extract_gherkin_steps(text)
        
        # Assert
        assert len(steps) >= 3
        assert any("Dado" in s for s in steps)
        assert any("Cuando" in s for s in steps)
        assert any("Entonces" in s for s in steps)
    
    # ===== TESTS DE ANÁLISIS CONFLUENCE =====
    
    def test_extract_from_confluence(self, analysis_service, mock_context_multisource):
        """Test: Extraer escenarios desde Confluence."""
        # Arrange
        analysis_service._extract_from_confluence(
            mock_context_multisource["confluence"],
            "DYF-4275"
        )
        
        # Assert
        assert len(analysis_service.happy_paths) > 0
        # Debe haber escenario de Onboarding
        onboarding_found = any(
            "onboarding" in hp.name.lower() 
            for hp in analysis_service.happy_paths
        )
        assert onboarding_found
        # Todos deben ser de Confluence
        assert all(hp.source == "confluence" for hp in analysis_service.happy_paths)
    
    # ===== TESTS DE ANÁLISIS GIT =====
    
    def test_extract_from_git(self, analysis_service, mock_context_multisource):
        """Test: Extraer escenarios desde Git."""
        # Arrange
        analysis_service._extract_from_git(
            mock_context_multisource["git"],
            "DYF-4275"
        )
        
        # Assert
        assert len(analysis_service.happy_paths) > 0
        # Todos deben ser de Git
        assert all(hp.source == "git" for hp in analysis_service.happy_paths)
        # Debe haber escenarios de regresión o validación
        assert len(analysis_service.error_scenarios) >= 0
    
    # ===== TESTS INTEGRALES =====
    
    def test_analyze_multisource_complete(self, analysis_service, mock_context_multisource):
        """Test: Análisis completo multisource."""
        # Act
        result = analysis_service.analyze(mock_context_multisource)
        
        # Assert
        assert result["issue_key"] == "DYF-4275"
        
        # Verificar que hay escenarios de todas las fuentes
        happy_paths = result["raw"]["happy_paths"]
        assert len(happy_paths) > 0
        
        sources = set(hp.get("source") for hp in happy_paths)
        assert "jira" in sources
        assert "confluence" in sources
        assert "git" in sources
    
    def test_count_by_source(self, analysis_service, mock_context_multisource):
        """Test: Contar escenarios por fuente."""
        # Arrange
        analysis_service.analyze(mock_context_multisource)
        
        # Act
        jira_count = analysis_service._count_by_source("jira")
        confluence_count = analysis_service._count_by_source("confluence")
        git_count = analysis_service._count_by_source("git")
        
        # Assert
        assert jira_count > 0
        assert confluence_count > 0
        assert git_count >= 0
        assert jira_count + confluence_count + git_count == len(analysis_service.happy_paths)
    
    def test_calculate_confidence(self, analysis_service):
        """Test: Calcular nivel de confianza."""
        # Arrange
        from ai_qa_gherkin.models.domain import BusinessRule, HappyPath, TraceabilityLink
        
        trace = TraceabilityLink(
            source_type="jira",
            source_id="TEST",
            source_name="Test"
        )
        
        # Agregar elementos con categoría VÁLIDA
        analysis_service.business_rules = [
            BusinessRule(rule="Rule 1", category="general", traceability=trace),  # ← "general"
            BusinessRule(rule="Rule 2", category="validation", traceability=trace),  # ← "validation"
        ]
        analysis_service.happy_paths = [
            HappyPath(name="Path 1", steps=["Dado", "Cuando", "Entonces"], traceability=trace),
            HappyPath(name="Path 2", steps=["Dado", "Cuando", "Entonces"], traceability=trace),
        ]
        
        # Act
        confidence = analysis_service._calculate_confidence()
        
        # Assert
        assert 0.5 <= confidence <= 1.0
        assert isinstance(confidence, float)

    def test_extract_assumptions(self, analysis_service):
        """Test: Extraer supuestos."""
        # Act
        assumptions = analysis_service._extract_assumptions({})
        
        # Assert
        assert len(assumptions) > 0
        assert all(isinstance(a, str) for a in assumptions)
        assert any("Issue" in a for a in assumptions)
    
    def test_extract_risks(self, analysis_service):
        """Test: Extraer riesgos."""
        # Act
        risks = analysis_service._extract_risks({"git": {"changed_files": ["a.ts"]}})
        
        # Assert
        assert len(risks) > 0
        assert all(isinstance(r, str) for r in risks)
        assert any("regresión" in r.lower() for r in risks)
    
    # ===== TESTS DE SALIDA =====
    
    def test_analyze_output_structure(self, analysis_service, mock_context_multisource):
        """Test: Estructura de salida del análisis."""
        # Act
        result = analysis_service.analyze(mock_context_multisource)
        
        # Assert
        assert "issue_key" in result
        assert "scope_summary" in result
        assert "business_rules" in result
        assert "preconditions" in result
        assert "raw" in result
        assert "happy_paths" in result["raw"]
        assert "error_scenarios" in result["raw"]
        
        # Verificar estructura de happy_path
        if result["raw"]["happy_paths"]:
            hp = result["raw"]["happy_paths"][0]
            assert "name" in hp
            assert "steps" in hp
            assert "source" in hp
            assert "traceability" in hp

    def test_use_llm_calls_client_and_marks_metadata(self, mock_context_jira_only):
        """Test: --use-llm llama al cliente y marca escenarios derivados por IA."""
        llm_payload = {
            "business_rules": [{"description": "Regla IA", "category": "validation"}],
            "preconditions": ["Precondicion IA"],
            "happy_paths": [
                {
                    "name": "Given usuario valido When visualiza archivos Then ve acciones",
                    "steps": [
                        "Dado que el usuario tiene permisos validos",
                        "Cuando visualiza la pestana Otros archivos",
                        "Entonces ve las acciones disponibles",
                    ],
                    "source": "jira",
                    "source_id": "DYF-4275",
                    "source_name": "Implementar validacion de datos",
                    "source_url": "",
                }
            ],
            "error_scenarios": [],
        }

        with patch("ai_qa_gherkin.services.analysis_service.LLMClient") as client_cls:
            client = Mock()
            client.provider = "openai"
            client.model = "test-model"
            client.extract_business_rules.return_value = llm_payload
            client_cls.return_value = client

            service = AnalysisService(use_llm=True)
            result = service.analyze(mock_context_jira_only)

        client.extract_business_rules.assert_called_once()
        metadata = service.get_llm_metadata()
        assert metadata["llm_requested"] is True
        assert metadata["llm_used"] is True
        assert metadata["llm_provider"] == "openai"
        assert metadata["llm_model"] == "test-model"
        assert metadata["llm_scenarios_count"] == 1
        assert any(
            path.get("generated_by") == "llm"
            for path in result["raw"]["happy_paths"]
        )

    def test_use_llm_init_failure_is_not_silent(self):
        """Test: si se pide IA y no inicializa, falla sin fallback silencioso."""
        with patch(
            "ai_qa_gherkin.services.analysis_service.LLMClient",
            side_effect=ValueError("OPENAI_API_KEY not configured in .env"),
        ):
            with pytest.raises(ValueError, match="--use-llm was requested"):
                AnalysisService(use_llm=True)

    def test_use_llm_empty_result_fails(self, mock_context_jira_only):
        """Test: si la IA no aporta escenarios validos, falla."""
        with patch("ai_qa_gherkin.services.analysis_service.LLMClient") as client_cls:
            client = Mock()
            client.provider = "openai"
            client.model = "test-model"
            client.extract_business_rules.return_value = {
                "business_rules": [],
                "preconditions": [],
                "happy_paths": [],
                "error_scenarios": [],
            }
            client_cls.return_value = client

            service = AnalysisService(use_llm=True)

            with pytest.raises(ValueError, match="returned no valid scenarios"):
                service.analyze(mock_context_jira_only)

    def test_use_llm_deduplicates_equivalent_local_scenarios(self, mock_context_jira_only):
        """Test: escenarios IA equivalentes reemplazan duplicados locales."""
        llm_payload = {
            "business_rules": [],
            "preconditions": [],
            "happy_paths": [
                {
                    "name": "Visualizacion exitosa de la pestana Otros archivos",
                    "steps": [
                        "Dado que el usuario tiene permisos de visualizacion sobre la cuenta medica",
                        "Cuando accede a la seccion 3 Antecedentes y selecciona Otros archivos",
                        "Entonces se muestra la tabla Archivos complementarios",
                    ],
                    "source": "jira",
                    "source_id": "DYF-4275",
                    "source_name": "Implementar validacion de datos",
                    "source_url": "",
                }
            ],
            "error_scenarios": [],
        }

        with patch("ai_qa_gherkin.services.analysis_service.LLMClient") as client_cls:
            client = Mock()
            client.provider = "github_models"
            client.model = "openai/gpt-4.1"
            client.extract_business_rules.return_value = llm_payload
            client_cls.return_value = client

            service = AnalysisService(use_llm=True)
            result = service.analyze(mock_context_jira_only)

        matching_paths = [
            path for path in result["raw"]["happy_paths"]
            if "Visualizaci" in path["name"] or "visualizacion" in path["name"].lower()
        ]
        assert len(matching_paths) == 1
        assert matching_paths[0]["generated_by"] == "llm"

    def test_use_llm_removes_local_duplicate_with_shared_core_steps(self, mock_context_jira_only):
        """Test: dedupe elimina Jira local cuando IA cubre los mismos pasos clave."""
        llm_payload = {
            "business_rules": [],
            "preconditions": [],
            "happy_paths": [
                {
                    "name": "Estado vacio sin archivos complementarios",
                    "steps": [
                        "Dado que no existen archivos complementarios asociados a la cuenta",
                        "Cuando se carga la pestaña 'Otros archivos'",
                        "Entonces se muestra un mensaje indicando que no hay archivos disponibles",
                    ],
                    "source": "jira",
                    "source_id": "DYF-4275",
                    "source_name": "Implementar validacion de datos",
                    "source_url": "",
                }
            ],
            "error_scenarios": [],
        }

        with patch("ai_qa_gherkin.services.analysis_service.LLMClient") as client_cls:
            client = Mock()
            client.provider = "github_models"
            client.model = "openai/gpt-4.1"
            client.extract_business_rules.return_value = llm_payload
            client_cls.return_value = client

            service = AnalysisService(use_llm=True)
            result = service.analyze(mock_context_jira_only)

        empty_state_paths = [
            path for path in result["raw"]["happy_paths"]
            if any("no hay archivos disponibles" in step.lower() for step in path["steps"])
        ]
        assert len(empty_state_paths) == 1
        assert empty_state_paths[0]["generated_by"] == "llm"

    def test_use_llm_drops_local_confluence_when_llm_covers_confluence(self, mock_context_multisource):
        """Test: descarta escenarios heurísticos Confluence si IA cubre Confluence."""
        llm_payload = {
            "business_rules": [],
            "preconditions": [],
            "happy_paths": [
                {
                    "name": "Usuario nuevo completa onboarding desde Confluence",
                    "steps": [
                        "Dado que el usuario nuevo tiene acceso a la cuenta",
                        "Cuando completa el flujo documentado en Confluence",
                        "Entonces visualiza la guía de bienvenida",
                    ],
                    "source": "confluence",
                    "source_id": "123456",
                    "source_name": "First Time User Guide",
                    "source_url": "https://confluence.example.com/wiki/pages/123456",
                }
            ],
            "error_scenarios": [],
        }

        with patch("ai_qa_gherkin.services.analysis_service.LLMClient") as client_cls:
            client = Mock()
            client.provider = "github_models"
            client.model = "openai/gpt-4.1"
            client.extract_business_rules.return_value = llm_payload
            client_cls.return_value = client

            service = AnalysisService(use_llm=True)
            result = service.analyze(mock_context_multisource)

        confluence_paths = [
            path for path in result["raw"]["happy_paths"]
            if path["source"] == "confluence"
        ]
        assert len(confluence_paths) == 1
        assert confluence_paths[0]["generated_by"] == "llm"
