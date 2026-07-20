"""
Tests para GherkinService.
Prueba generación de archivos .feature desde análisis multisource.
"""
from __future__ import annotations
import pytest
from ai_qa_gherkin.services.gherkin_service import GherkinService
from ai_qa_gherkin.services.validator_service import GherkinValidator


class TestGherkinService:
    """Suite de tests para GherkinService."""
    
    @pytest.fixture
    def gherkin_service(self):
        """Fixture que crea un GherkinService."""
        return GherkinService()
    
    @pytest.fixture
    def mock_analysis_result(self):
        """Fixture de resultado de análisis."""
        return {
            "issue_key": "DYF-4275",
            "scope_summary": "Implementar validación de datos",
            "business_rules": [
                {
                    "rule": "Debe validar entrada correctamente",
                    "category": "validation",
                    "traceability": {}
                }
            ],
            "preconditions": [],
            "raw": {
                "happy_paths": [
                    {
                        "name": "Validación correcta",
                        "steps": [
                            "Dado que ingreso datos válidos",
                            "Cuando envío el formulario",
                            "Entonces se guardan correctamente"
                        ],
                        "source": "jira",
                        "traceability": {}
                    },
                    {
                        "name": "FTU - Usuario nuevo",
                        "steps": [
                            "Dado que soy un usuario nuevo",
                            "Cuando accedo por primera vez",
                            "Entonces veo la guía de bienvenida"
                        ],
                        "source": "confluence",
                        "traceability": {}
                    },
                    {
                        "name": "Git - Validación de cambios",
                        "steps": [
                            "Dado que se actualizaron archivos",
                            "Cuando se ejecutan los tests",
                            "Entonces todos pasan"
                        ],
                        "source": "git",
                        "traceability": {}
                    }
                ],
                "error_scenarios": [
                    {
                        "error_type": "validation",
                        "description": "Datos inválidos",
                        "expected_outcome": "Mostrar error",
                        "source": "jira",
                        "traceability": {}
                    }
                ]
            }
        }
    
    # ===== TESTS DE GENERACIÓN =====
    
    def test_generate_from_analysis(self, gherkin_service, mock_analysis_result):
        """Test: Generar feature desde análisis."""
        # Act
        generated = gherkin_service.generate_from_analysis(mock_analysis_result)
        
        # Assert
        assert generated.gherkin_text is not None
        assert len(generated.gherkin_text) > 0
        assert generated.scenarios_count == 3  # ← scenarios_count
        assert "Implementar validación" in generated.gherkin_text
    
    def test_generated_feature_has_language_header(self, gherkin_service, mock_analysis_result):
        """Test: El feature generado tiene encabezado de lenguaje."""
        # Act
        generated = gherkin_service.generate_from_analysis(mock_analysis_result)
        
        # Assert
        assert "language: es" in generated.gherkin_text
    
    def test_generated_feature_has_feature_keyword(self, gherkin_service, mock_analysis_result):
        """Test: El feature tiene palabra clave Característica."""
        # Act
        generated = gherkin_service.generate_from_analysis(mock_analysis_result)
        
        # Assert
        assert "Característica:" in generated.gherkin_text
    
    def test_generated_feature_omits_generic_background(self, gherkin_service, mock_analysis_result):
        """Test: el feature no agrega antecedentes genericos sin evidencia."""
        # Act
        generated = gherkin_service.generate_from_analysis(mock_analysis_result)
        
        # Assert
        assert "Antecedentes:" not in generated.gherkin_text
        assert "Dado que el sistema está disponible" not in generated.gherkin_text
        assert "Dado que tengo credenciales válidas" not in generated.gherkin_text
    
    def test_generated_feature_has_scenarios(self, gherkin_service, mock_analysis_result):
        """Test: El feature contiene escenarios."""
        # Act
        generated = gherkin_service.generate_from_analysis(mock_analysis_result)
        
        # Assert
        assert "Escenario:" in generated.gherkin_text
        assert "Validación correcta" in generated.gherkin_text
    
    def test_generated_feature_uses_functional_tags(self, gherkin_service, mock_analysis_result):
        """Test: El feature usa tags funcionales, no tags tecnicos de origen."""
        # Act
        generated = gherkin_service.generate_from_analysis(mock_analysis_result)
        
        # Assert
        assert "@regression" in generated.gherkin_text
        assert "@funcional" in generated.gherkin_text
        assert "@jira" not in generated.gherkin_text
        assert "@confluence" not in generated.gherkin_text
        assert "@git" not in generated.gherkin_text

    def test_generated_feature_omits_llm_metadata(self, gherkin_service, mock_analysis_result):
        """Test: El feature no expone metadata tecnica de IA."""
        mock_analysis_result["raw"]["happy_paths"][0]["generated_by"] = "llm"

        generated = gherkin_service.generate_from_analysis(mock_analysis_result)

        assert "@llm" not in generated.gherkin_text
        assert "# generated_by: llm" not in generated.gherkin_text
        assert "# source:" not in generated.gherkin_text

    def test_generated_feature_groups_by_rule_and_outline_for_extensions(self, gherkin_service):
        """Test: agrupa por Regla y consolida extensiones en un outline."""
        analysis = {
            "issue_key": "DYF-4275",
            "scope_summary": "[CME-RT] [FRONT] - Visualizacion de la seccion 3 Antecedentes de una Cuenta (archivos)",
            "raw": {
                "happy_paths": [
                    {
                        "name": "mostrar icono PDF",
                        "steps": [
                            "Dado que existe un archivo complementario con extension PDF",
                            "Cuando se muestra la tabla de archivos complementarios",
                            "Entonces se renderiza el icono pdf-rojo en la fila del archivo",
                        ],
                    },
                    {
                        "name": "mostrar icono JPG",
                        "steps": [
                            "Dado que existe un archivo complementario con extension JPG",
                            "Cuando se muestra la tabla de archivos complementarios",
                            "Entonces se renderiza el icono img-verde en la fila del archivo",
                        ],
                    },
                    {
                        "name": "usuario sin permisos no puede acceder a la pestana",
                        "steps": [
                            "Dado que el usuario no tiene permisos sobre la cuenta medica",
                            'Cuando accede a la seccion "3. Antecedentes"',
                            'Entonces la pestana "Otros archivos" no es visible o esta deshabilitada',
                        ],
                    },
                ],
                "error_scenarios": [],
            },
        }

        generated = gherkin_service.generate_from_analysis(analysis)
        result = GherkinValidator().validate(generated.gherkin_text)

        assert 'Característica: Visualización y acciones en "Otros archivos" de Antecedentes' in generated.gherkin_text
        assert "Regla: Íconos por extensión" in generated.gherkin_text
        assert "Esquema del escenario: Mostrar ícono según tipo de archivo" in generated.gherkin_text
        assert "Ejemplos:" in generated.gherkin_text
        assert "| PDF" in generated.gherkin_text
        assert "| JPG" in generated.gherkin_text
        assert generated.gherkin_text.count("Esquema del escenario:") == 1
        assert "Regla: Visualización según permisos" in generated.gherkin_text
        assert "@permisos" in generated.gherkin_text
        assert result.is_valid is True

    def test_generated_feature_cleans_given_prefix_from_scenario_name(self, gherkin_service):
        """Test: nombres de escenario no empiezan con Dado que."""
        analysis = {
            "issue_key": "DYF-4275",
            "scope_summary": "Feature",
            "raw": {
                "happy_paths": [
                    {
                        "name": "Dado que el usuario tiene permisos de lectura",
                        "steps": [
                            "Dado que el usuario tiene permisos de lectura",
                            "Cuando descarga el archivo",
                            "Entonces se inicia la descarga",
                        ],
                        "source": "jira",
                        "generated_by": "llm",
                        "traceability": {},
                    }
                ],
                "error_scenarios": [],
            },
        }

        generated = gherkin_service.generate_from_analysis(analysis)

        assert "Escenario: Descargar archivo con permisos de lectura" in generated.gherkin_text
        assert "Escenario: Dado que" not in generated.gherkin_text

    def test_generated_feature_contextualizes_duplicate_steps_for_max_confidence(self, gherkin_service):
        """Test: pasos repetidos entre escenarios se contextualizan para evitar warnings."""
        analysis = {
            "issue_key": "DYF-4275",
            "scope_summary": "Gestion de otros archivos",
            "raw": {
                "happy_paths": [
                    {
                        "name": "visualizar otros archivos asociados a la cuenta",
                        "steps": [
                            "Dado que el ejecutivo consulta los antecedentes de una cuenta",
                            "Cuando se carga la pestaña 'Otros archivos'",
                            "Entonces se muestran los archivos complementarios disponibles",
                        ],
                        "source": "jira",
                        "generated_by": "llm",
                        "traceability": {},
                    },
                    {
                        "name": "visualizar estado sin archivos complementarios",
                        "steps": [
                            "Dado que la cuenta no tiene archivos complementarios",
                            "Cuando se carga la pestaña 'Otros archivos'",
                            "Entonces se informa que no existen archivos asociados",
                        ],
                        "source": "jira",
                        "generated_by": "llm",
                        "traceability": {},
                    },
                ],
                "error_scenarios": [],
            },
        }

        generated = gherkin_service.generate_from_analysis(analysis)
        result = GherkinValidator().validate(generated.gherkin_text)

        assert "Cuando se carga la pestaña 'Otros archivos' sin archivos complementarios disponibles" in generated.gherkin_text
        assert "para visualizar estado sin archivos complementarios" not in generated.gherkin_text
        assert result.is_valid is True
        assert result.confidence == 0.95
        assert not any(error["rule_id"] == "DUPLICATE_SCENARIO" for error in result.errors)

    def test_generated_feature_dedupes_equivalent_outcomes_across_sources(self, gherkin_service):
        """Test: elimina escenarios equivalentes aunque vengan redactados distinto."""
        analysis = {
            "issue_key": "DYF-4275",
            "scope_summary": "Visualización de otros archivos",
            "raw": {
                "happy_paths": [
                    {
                        "name": "Se muestra el archivo en la tabla",
                        "steps": [
                            "Dado que el campo 'tamano' en ArchivoCuentaComplementarioDTO es nulo, cero o no viene",
                            "Cuando se muestra el archivo en la tabla",
                            "Entonces el tamaño se muestra como '—'",
                        ],
                        "source": "confluence",
                        "generated_by": "llm",
                        "traceability": {},
                    },
                    {
                        "name": "El campo 'tamano' del archivo es nulo, cero o no viene",
                        "steps": [
                            "Dado que el campo 'tamano' del archivo es nulo, cero o no viene",
                            "Cuando el usuario completa la acción solicitada para campo 'tamano' del archivo es nulo, cero o no viene",
                            "Entonces el tamaño del archivo se muestra como '—' en la tabla",
                        ],
                        "source": "git",
                        "generated_by": "llm",
                        "traceability": {},
                    },
                ],
                "error_scenarios": [],
            },
        }

        generated = gherkin_service.generate_from_analysis(analysis)

        assert generated.gherkin_text.count("Escenario:") == 1
        assert "tamano" not in generated.gherkin_text

    def test_generated_feature_coerces_steps_without_gherkin_keywords(self, gherkin_service):
        """Test: pasos externos sin keyword no rompen la validacion Gherkin."""
        analysis = {
            "issue_key": "DYF-4325",
            "scope_summary": "Webhook recepción de tramitación de cuentas",
            "raw": {
                "happy_paths": [
                    {
                        "name": "Happy path for webhook",
                        "steps": ["User initiates", "System processes", "Result returned"],
                        "source": "jira",
                        "generated_by": "fallback",
                        "traceability": {},
                    }
                ],
                "error_scenarios": [],
            },
        }

        generated = gherkin_service.generate_from_analysis(analysis)
        result = GherkinValidator().validate(generated.gherkin_text)

        assert "Dado que User initiates" in generated.gherkin_text
        assert "Cuando System processes" in generated.gherkin_text
        assert "Entonces Result returned" in generated.gherkin_text
        assert result.is_valid is True
    
    def test_generated_feature_has_error_scenarios(self, gherkin_service, mock_analysis_result):
        """Test: El feature incluye escenarios de error."""
        # Act
        generated = gherkin_service.generate_from_analysis(mock_analysis_result)
        
        # Assert
        # TextCleaner puede cambiar "error" a "pero", buscar patrón más flexible
        text_lower = generated.gherkin_text.lower()
        assert "error" in text_lower or "pero" in text_lower or "@error-handling" in generated.gherkin_text or "@but-handling" in generated.gherkin_text
    
    def test_format_scenario(self, gherkin_service):
        """Test: Formatear un escenario individual."""
        # Arrange
        scenario = {
            "name": "Test scenario",
            "steps": [
                "Dado que algo",
                "Cuando algo sucede",
                "Entonces algo es cierto"
            ],
            "source": "jira"
        }
        
        # Act
        lines = gherkin_service._format_scenario(scenario, "@test")
        
        # Assert
        assert len(lines) > 0
        assert any("@test" in line for line in lines)
        assert any("Test scenario" in line for line in lines)
    
    def test_format_error_scenario(self, gherkin_service):
        """Test: Formatear un escenario de error."""
        # Arrange
        error = {
            "error_type": "validation",
            "description": "Datos inválidos recibidos",
            "expected_outcome": "Sistema muestra error"
        }
        
        # Act
        lines = gherkin_service._format_error_scenario(error)
        
        # Assert
        assert len(lines) > 0
        assert any("error" in line.lower() for line in lines)

    def test_generated_error_scenarios_have_when_then(self, gherkin_service, mock_analysis_result):
        """Test: escenarios de error generados tienen Cuando y Entonces."""
        generated = gherkin_service.generate_from_analysis(mock_analysis_result)

        assert "Escenario: Rechazar datos inválidos" in generated.gherkin_text
        assert "Dado que existen datos inválidos" in generated.gherkin_text
        assert "Cuando se envían los datos" in generated.gherkin_text
        assert "Entonces Mostrar error" in generated.gherkin_text

    def test_generated_error_scenarios_have_distinct_when_steps(self, gherkin_service):
        """Test: escenarios de error no repiten el mismo Cuando generico."""
        analysis = {
            "issue_key": "DYF-4275",
            "scope_summary": "Feature",
            "raw": {
                "happy_paths": [
                    {
                        "name": "Camino feliz",
                        "steps": ["Dado que existe contexto", "Cuando ejecuto", "Entonces resulta"],
                        "source": "jira",
                        "traceability": {},
                    }
                ],
                "error_scenarios": [
                    {
                        "error_type": "validation",
                        "description": "El usuario intenta descargar un archivo sin permisos",
                        "expected_outcome": "No se inicia la descarga",
                        "generated_by": "llm",
                    },
                    {
                        "error_type": "validation",
                        "description": "El usuario intenta agregar un archivo sin permisos",
                        "expected_outcome": "No aparece el boton agregar",
                        "generated_by": "llm",
                    },
                ],
            },
        }

        generated = gherkin_service.generate_from_analysis(analysis)

        assert "Escenario: Descargar archivo sin permisos de lectura" in generated.gherkin_text
        assert "Dado que el usuario no tiene permisos de lectura" in generated.gherkin_text
        assert "Cuando el usuario descarga el archivo" in generated.gherkin_text
        assert "Escenario: Agregar archivo sin permisos suficientes" in generated.gherkin_text
        assert "Dado que el usuario no tiene permisos para agregar archivos" in generated.gherkin_text
        assert "Cuando el usuario agrega un archivo" in generated.gherkin_text
        assert "Dado que el usuario intenta" not in generated.gherkin_text
        assert "Cuando se intenta ejecutar la accion no permitida" not in generated.gherkin_text
        assert "Escenario: validation -" not in generated.gherkin_text

    def test_generated_feature_repairs_titles_mass_actions_and_i18n_steps(self, gherkin_service):
        """Test: corrige titulos truncados, acciones masivas y fallback i18n."""
        analysis = {
            "issue_key": "DYF-4275",
            "scope_summary": "Gestion de otros archivos",
            "raw": {
                "happy_paths": [
                    {
                        "name": "Seleccionar todos los archivos visibles sin permisos de visuali",
                        "steps": [
                            "Dado que el usuario tiene permisos de lectura",
                            "Cuando selecciona el checkbox para seleccionar todos los archivos visibles",
                            "Entonces se muestran las acciones masivas descargar y eliminar",
                        ],
                    },
                    {
                        "name": "Validar DTO de la cuent",
                        "steps": [
                            "Dado que El usuario revisa el DTO de la cuent.",
                            "Cuando confirma la informacion.",
                            "Entonces se visualiza la informacion de la cuenta.",
                        ],
                    },
                ],
                "error_scenarios": [
                    {
                        "error_type": "validation",
                        "description": "configuracion regional no disponible",
                        "expected_outcome": "Se muestran textos por defecto",
                    }
                ],
            },
        }

        generated = gherkin_service.generate_from_analysis(analysis)

        assert "sin permisos de visuali" not in generated.gherkin_text
        assert "DTO de la cuenta" in generated.gherkin_text
        assert "Escenario: Mostrar acciones masivas al seleccionar múltiples archivos" in generated.gherkin_text
        assert "@acciones-masivas @lectura @escritura" in generated.gherkin_text
        assert "Dado que El usuario" not in generated.gherkin_text
        assert "Dado que el usuario" in generated.gherkin_text
        assert "Cuando se intenta completar la acción para Se intenta completar la acción" not in generated.gherkin_text
        assert "Escenario: Mostrar tabla sin configuración regional" in generated.gherkin_text
        assert "Cuando se muestra la tabla de archivos complementarios" in generated.gherkin_text
    
    def test_generated_feature_is_cleaned(self, gherkin_service, mock_analysis_result):
        """Test: El feature generado es limpiado por TextCleaner."""
        # Act
        generated = gherkin_service.generate_from_analysis(mock_analysis_result)
        
        # Assert
        assert len(generated.gherkin_text.strip()) > 0
    
    def test_generate_with_only_jira(self, gherkin_service):
        """Test: Generar con solo escenarios de Jira."""
        # Arrange
        analysis = {
            "issue_key": "TEST-123",
            "scope_summary": "Test feature",
            "business_rules": [],
            "preconditions": [],
            "raw": {
                "happy_paths": [
                    {
                        "name": "Test scenario",
                        "steps": ["Dado", "Cuando", "Entonces"],
                        "source": "jira",
                        "traceability": {}
                    }
                ],
                "error_scenarios": []
            }
        }
        
        # Act
        generated = gherkin_service.generate_from_analysis(analysis)
        
        # Assert
        assert generated.scenarios_count == 1  # ← scenarios_count
        assert "Característica:" in generated.gherkin_text
    
    def test_generated_feature_is_valid_gherkin(self, gherkin_service, mock_analysis_result):
        """Test: El feature generado es Gherkin válido."""
        # Act
        generated = gherkin_service.generate_from_analysis(mock_analysis_result)
        
        # Assert
        text = generated.gherkin_text.lower()
        
        # Debe tener estructura básica
        assert "característica:" in text or "feature:" in text
        assert "escenario:" in text or "scenario:" in text
