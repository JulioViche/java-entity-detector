#!/usr/bin/env python3
"""
detect_entities - Herramienta de deteccion de entidades de persistencia Java.

Analiza repositorios Java para extraer entidades de base de datos
a partir de anotaciones JPA y mapeos Hibernate XML.

Uso:
    python -m scripts.detect_entities -r /repositorios -o resultado.json
    python detect_entities.py -r ./repositories -o output.json
    python detect_entities.py -r ./repositories  # imprime en stdout

Este script NO compila ni ejecuta los proyectos Java.
Solo analiza el codigo fuente de forma estatica usando Tree-sitter.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Permitir ejecucion tanto como modulo como script independiente
try:
    from entity_detector.scanner import scan_all
except ImportError:
    # Ejecucion directa: ajustar path
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
    from entity_detector.scanner import scan_all


# ============================================================
# CLI
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos de linea de comandos."""

    parser = argparse.ArgumentParser(
        prog="detect_entities",
        description=(
            "Detecta entidades de base de datos en repositorios Java "
            "analizando anotaciones JPA y mapeos Hibernate XML."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  python detect_entities.py -r ./repositories\n"
            "  python detect_entities.py -r ./repositories -o out.json\n"
            "  python detect_entities.py -r repo1 repo2 -o out.json\n"
        ),
    )

    parser.add_argument(
        "-r", "--repos",
        nargs="+",
        required=True,
        type=Path,
        help=(
            "Directorio(s) que contienen repositorios Java. "
            "Cada subdirectorio se trata como un repositorio."
        ),
    )

    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help=(
            "Archivo de salida JSON. Si no se especifica, "
            "se imprime en stdout."
        ),
    )

    parser.add_argument(
        "--pretty",
        action="store_true",
        default=True,
        help="Indentar el JSON de salida (por defecto: True).",
    )

    parser.add_argument(
        "--compact",
        action="store_true",
        default=False,
        help="JSON compacto sin indentacion.",
    )

    return parser


# ============================================================
# MAIN
# ============================================================

def main(argv: list | None = None) -> None:
    """Punto de entrada principal."""

    parser = build_parser()
    args = parser.parse_args(argv)

    # Validar que los directorios existen
    for repo_path in args.repos:
        if not repo_path.exists():
            print(
                f"[ERROR] El directorio no existe: {repo_path}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Escanear
    all_entities = []
    all_embeddables = []
    all_mapped = []
    repositories = []

    for repo_root in args.repos:
        result = scan_all(repo_root)
        all_entities.extend(result.entities)
        all_embeddables.extend(result.embeddables)
        all_mapped.extend(result.mapped_superclasses)
        repositories.extend(result.repositories)

    # Construir resultado final
    output = {
        "version": "1.0",
        "scan_date": datetime.now(timezone.utc).isoformat(),
        "repositories": sorted(set(repositories)),
        "summary": {
            "entities": len(all_entities),
            "embeddables": len(all_embeddables),
            "mapped_superclasses": len(all_mapped),
        },
        "entities": [e.to_dict() for e in all_entities],
        "embeddables": [e.to_dict() for e in all_embeddables],
        "mapped_superclasses": [
            m.to_dict() for m in all_mapped
        ],
    }

    # Serializar
    indent = None if args.compact else 2
    json_str = json.dumps(
        output, indent=indent, ensure_ascii=False
    )

    if args.output:
        args.output.write_text(json_str, encoding="utf-8")
        print(f"Resultado escrito en: {args.output.resolve()}")
    else:
        print(json_str)

    # Resumen
    print(
        f"\n[OK] {len(all_entities)} entidades, "
        f"{len(all_embeddables)} embeddables, "
        f"{len(all_mapped)} mapped superclasses "
        f"en {len(set(repositories))} repositorios."
    )


if __name__ == "__main__":
    main()
