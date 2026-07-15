from __future__ import annotations

import argparse
from pathlib import Path

from ai_qa_gherkin.clients.xray_client import XrayClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test for XrayClient")
    parser.add_argument(
        "--project-key",
        required=True,
        help="Project key Jira/Xray, ej: QA o DYF",
    )
    parser.add_argument(
        "--test-type-name",
        required=True,
        help='Nombre del issue type para Test en el proyecto, ej: "Casos de Prueba"',
    )
    parser.add_argument(
        "--feature-file",
        required=True,
        help="Ruta al .feature, ej: tests/smoke.feature",
    )
    args = parser.parse_args()

    feature_path = Path(args.feature_file)
    if not feature_path.exists():
        print(f"❌ No existe archivo: {feature_path}")
        return 1

    feature_text = feature_path.read_text(encoding="utf-8")

    client = XrayClient()

    print("\n=== XRAY SMOKE ===")
    print(f"Project      : {args.project_key}")
    print(f"TestTypeName : {args.test_type_name}")
    print(f"Feature file : {feature_path} ({len(feature_text)} chars)")

    result = client.import_feature_cucumber(
        project_key=args.project_key,
        feature_text=feature_text,
        test_type_name=args.test_type_name,
        file_name=feature_path.name,
    )

    print("\n✅ Import ejecutado correctamente")
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())