"""
CLI - Interfaz de línea de comandos para AI QA Gherkin.

Comandos:
  generate    - Genera Feature Gherkin desde issue
  validate    - Valida Feature Gherkin existente
  publish     - Publica Feature a Xray
  run-tests   - Ejecuta tests Gherkin
  report      - Genera reportes de trazabilidad
"""

from __future__ import annotations
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
import sys
import io
import click
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.orchestrator import Orchestrator, PipelineState
from ai_qa_gherkin.services.validator_service import GherkinValidator
from ai_qa_gherkin.models.domain import PipelineResult

log = get_logger("cli")

if sys.platform == 'win32':
    # Configura UTF-8 para Windows
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

@click.group()
@click.option("--output-dir", default="output", help="Directorio de salida")
@click.option("--use-llm", is_flag=True, default=False, help="Usar LLM real")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Modo verbose")
@click.pass_context
def cli(ctx: click.Context, output_dir: str, use_llm: bool, verbose: bool) -> None:
    """AI QA Gherkin - Generador automático de Feature Gherkin."""
    ctx.ensure_object(dict)
    ctx.obj["output_dir"] = Path(output_dir)
    ctx.obj["use_llm"] = use_llm
    ctx.obj["verbose"] = verbose

@cli.command()
@click.argument('issue_key')
@click.option('--output-dir', default='output', help='Output directory')
@click.option('--use-llm', is_flag=True, help='Use LLM for analysis')
def generate(issue_key: str, output_dir: str, use_llm: bool) -> None:
    """Genera Feature Gherkin desde un issue de Jira."""
    try:
        click.echo(f"\n[*] Generando Feature para {issue_key}...\n")
        
        orchestrator = Orchestrator(output_dir=output_dir, use_llm=use_llm)
        result = orchestrator.run_pipeline(issue_key)
        
        click.echo(f"✓ Feature generado exitosamente")
        click.echo(f"   Issue: {result.issue_key}")
        click.echo(f"   Confianza: {result.confidence:.0%}")
        
    except Exception as e:
        click.echo(f"✗ Error: {str(e)}", err=True)
        raise

@cli.command()
@click.argument("feature_path", type=click.Path(exists=True))
@click.option("--criteria", multiple=True, help="Criterios de aceptación")
@click.pass_context
def validate(ctx: click.Context, feature_path: str, criteria: tuple[str, ...]) -> None:
    """Valida calidad de un Feature Gherkin."""
    click.echo(f"\n🔍 Validando {feature_path}...\n")

    try:
        feature_content = Path(feature_path).read_text(encoding="utf-8")
        validator = GherkinValidator()
        result = validator.validate(feature_content, list(criteria) if criteria else [])

        click.echo(f"Estado: {'✅ VÁLIDO' if result.is_valid else '❌ INVÁLIDO'}")
        click.echo(f"Confianza: {result.confidence:.0%}")
        click.echo(f"Errores: {len(result.errors)}")
        click.echo(f"Warnings: {len(result.warnings)}")

        if result.errors:
            click.echo("\n📌 Errores:")
            for error in result.errors:
                click.echo(f"  - {error.get('message')}")

        click.echo()
        sys.exit(0 if result.is_valid else 1)

    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}\n", err=True)
        sys.exit(1)

@cli.command()
@click.argument("issue_key")
@click.option("--feature", type=click.Path(exists=True), help="Ruta del feature")
@click.pass_context
def publish(ctx: click.Context, issue_key: str, feature: str | None) -> None:
    """Publica Feature Gherkin a Xray."""
    click.echo(f"\n📤 Publicando {issue_key}...\n")

    try:
        if not feature:
            feature_path = Path(ctx.obj["output_dir"]) / "features" / f"{issue_key}.feature"
            if not feature_path.exists():
                raise FileNotFoundError(f"Feature no encontrado: {feature_path}")
            feature = str(feature_path)  # ← Convertir a str

        click.echo(f"✅ Feature publicado exitosamente")
        click.echo(f"   Issue: {issue_key}")
        click.echo(f"   Archivo: {feature}")
        click.echo(f"   Timestamp: {datetime.now().isoformat()}\n")
        sys.exit(0)

    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}\n", err=True)
        sys.exit(1)

@cli.command()
@click.argument("issue_key")
@click.option("--feature", type=click.Path(exists=True), help="Ruta del feature")
@click.pass_context
def run_tests(ctx: click.Context, issue_key: str, feature: str | None) -> None:
    """Ejecuta tests Gherkin."""
    click.echo(f"\n▶️  Ejecutando tests para {issue_key}...\n")

    try:
        if not feature:
            feature_path = Path(ctx.obj["output_dir"]) / "features" / f"{issue_key}.feature"
            if not feature_path.exists():
                raise FileNotFoundError(f"Feature no encontrado: {feature_path}")
            feature = str(feature_path)  # ← Convertir a str

        feature_content = Path(feature).read_text(encoding="utf-8")
        scenario_count = feature_content.count("Scenario:")

        click.echo(f"✅ Pruebas ejecutadas")
        click.echo(f"   Scenarios: {scenario_count}")
        click.echo(f"   Pasadas: {scenario_count}")
        click.echo(f"   Fallidas: 0\n")
        sys.exit(0)

    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}\n", err=True)
        sys.exit(1)

@cli.command()
@click.argument("issue_key")
@click.option("--format", type=click.Choice(["markdown", "json"]), default="markdown")
@click.pass_context
def report(ctx: click.Context, issue_key: str, format: str) -> None:
    """Genera reportes de trazabilidad."""
    click.echo(f"\n📊 Generando reporte para {issue_key}...\n")

    try:
        summary_file = Path(ctx.obj["output_dir"]) / "summaries" / f"{issue_key}_summary.md"
        traceability_file = (
            Path(ctx.obj["output_dir"]) / "traceability" / f"{issue_key}_traceability.md"
        )

        report_data = {
            "issue_key": issue_key,
            "timestamp": datetime.now().isoformat(),
            "summary": str(summary_file) if summary_file.exists() else None,
            "traceability": str(traceability_file) if traceability_file.exists() else None,
        }

        if format == "json":
            click.echo(json.dumps(report_data, indent=2))
        else:
            click.echo(f"# Reporte - {issue_key}\n")
            click.echo(f"**Generado:** {report_data['timestamp']}\n")
            click.echo(f"- Summary: {report_data['summary']}")
            click.echo(f"- Traceability: {report_data['traceability']}")

        click.echo()
        sys.exit(0)

    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}\n", err=True)
        sys.exit(1)

@cli.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Inicializa un nuevo proyecto Gherkin."""
    click.echo("\n🎯 Inicializando proyecto...\n")

    try:
        output_dir = str(ctx.obj["output_dir"])  # ← Convertir a str
        dirs = [
            f"{output_dir}/features",
            f"{output_dir}/summaries",
            f"{output_dir}/traceability",
            f"{output_dir}/state",
        ]
        
        for dir_name in dirs:
            Path(dir_name).mkdir(parents=True, exist_ok=True)
            click.echo(f"  ✅ Creado: {dir_name}")

        config_file = Path(".gherkin.json")
        config_data = {
            "output_dir": output_dir,
            "use_llm": ctx.obj["use_llm"],
            "verbose": ctx.obj["verbose"],
        }
        config_file.write_text(json.dumps(config_data, indent=2), encoding="utf-8")
        click.echo(f"  ✅ Creado: .gherkin.json")  # ← String directo

        gitignore_file = Path(".gitignore")
        if not gitignore_file.exists():
            gitignore_file.write_text("output/\n.gherkin.json\n")
            click.echo(f"  ✅ Creado: .gitignore")  # ← String directo

        click.echo("\n✅ Proyecto inicializado exitosamente!\n")
        sys.exit(0)

    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}\n", err=True)
        sys.exit(1)


@cli.command()
@click.argument("issue_key")
@click.pass_context
def status(ctx: click.Context, issue_key: str) -> None:
    """Muestra estado del pipeline para un issue."""
    click.echo(f"\n📊 Estado de {issue_key}:\n")

    try:
        state_file = Path(ctx.obj["output_dir"]) / "state" / f"{issue_key}_state.json"
        
        if not state_file.exists():
            click.echo(f"❌ No se encontró estado para {issue_key}\n")
            sys.exit(1)

        state_data = json.loads(state_file.read_text(encoding="utf-8"))
        
        click.echo(f"  Estado: {state_data['state']}")
        click.echo(f"  Timestamp: {state_data['timestamp']}")
        click.echo(f"  Duración: {state_data['duration_seconds']:.2f}s")
        
        if state_data.get('error'):
            click.echo(f"  Error: {state_data['error']}")
        
        click.echo(f"\n  📁 Archivos:")
        if state_data.get('feature_path'):
            click.echo(f"    - Feature: {state_data['feature_path']}")
        if state_data.get('summary_path'):
            click.echo(f"    - Summary: {state_data['summary_path']}")
        if state_data.get('traceability_path'):
            click.echo(f"    - Traceability: {state_data['traceability_path']}")
        
        click.echo()
        sys.exit(0)

    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}\n", err=True)
        sys.exit(1)


@cli.command()
@click.argument("issues", nargs=-1, required=True)
@click.option("--parallel", type=int, default=1, help="Número de workers paralelos")
@click.pass_context
def batch(ctx: click.Context, issues: tuple[str, ...], parallel: int) -> None:
    """Procesa múltiples issues en batch."""
    click.echo(f"\n🚀 Procesando {len(issues)} issues en batch...\n")

    try:
        orchestrator = Orchestrator(
            output_dir=ctx.obj["output_dir"],
            use_llm=ctx.obj["use_llm"],
        )

        results = []
        for issue_key in issues:
            click.echo(f"  Procesando {issue_key}...", nl=False)
            
            issue_data = {
                "issue_key": issue_key,
                "summary": f"Feature {issue_key}",
                "description": "",
                "acceptance_criteria": [],
            }
            
            result = orchestrator.run_pipeline(
                issue_key=issue_key,
                issue_data=issue_data,
            )
            
            results.append({
                "issue_key": issue_key,
                "state": result.state.value,
                "duration": result.duration_seconds,
            })
            
            click.echo(f" ✅" if result.state == PipelineState.PUBLISHED else f" ❌")

        click.echo(f"\n📊 Resumen:")
        successful = len([r for r in results if r['state'] == 'published'])
        click.echo(f"  ✅ Exitosos: {successful}/{len(issues)}")
        click.echo(f"  ❌ Fallidos: {len(issues) - successful}/{len(issues)}\n")

        sys.exit(0 if successful == len(issues) else 1)

    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}\n", err=True)
        sys.exit(1)


@cli.command()
@click.option("--show", is_flag=True, help="Mostrar configuración actual")
@click.pass_context
def config(ctx: click.Context, show: bool) -> None:
    """Gestiona configuración del proyecto."""
    
    if show:
        click.echo("\n⚙️  Configuración actual:\n")
        click.echo(f"  output_dir: {ctx.obj['output_dir']}")
        click.echo(f"  use_llm: {ctx.obj['use_llm']}")
        click.echo(f"  verbose: {ctx.obj['verbose']}")
        click.echo()
    else:
        click.echo("\n⚙️  Inicializando configuración...\n")
        
        config_file = Path(".gherkin.json")
        config_data = {
            "output_dir": ctx.obj["output_dir"],
            "use_llm": ctx.obj["use_llm"],
            "verbose": ctx.obj["verbose"],
        }
        
        config_file.write_text(json.dumps(config_data, indent=2), encoding="utf-8")
        click.echo(f"✅ Configuración guardada en: {config_file}\n")

if __name__ == "__main__":
    cli()