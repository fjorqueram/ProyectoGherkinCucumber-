Feature: DYF-4307 Smoke Xray import
  Scenario: Importación mínima DYF-4307
    Given existe la historia DYF-4307
    When se importa el feature en Xray
    Then la importación debería completarse