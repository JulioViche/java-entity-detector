"""
Scanner de repositorios Java.

Recorre directorios en busca de archivos .java y .hbm.xml,
delegando el parseo a los parsers correspondientes.

Soporta:
    - Multiples repositorios en un directorio raiz
    - Archivos .java con anotaciones JPA
    - Archivos .hbm.xml de Hibernate
    - Exclusion de directorios generados (target, build, etc.)
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from .hibernate_xml_parser import parse_hibernate_xml
from .java_jpa_parser import parse_java_file
from .models import Embeddable, Entity, MappedSuperclass, ScanResult
from .utils import should_ignore_path


# ============================================================
# ESCANEO DE UN REPOSITORIO
# ============================================================

def scan_repository(repository_path: Path) -> tuple:
    """
    Escanea un repositorio individual.

    Busca archivos .java y .hbm.xml, excluyendo directorios
    generados y de dependencias.

    Devuelve: (entities, embeddables, mapped_superclasses)
    """
    repo_name = repository_path.name
    print(f"[INFO] Analizando repositorio: {repo_name}")

    all_entities: List[Entity] = []
    all_embeddables: List[Embeddable] = []
    all_mapped: List[MappedSuperclass] = []

    # --- Java JPA ---
    java_files = list(repository_path.rglob("*.java"))
    java_count = 0

    for java_file in java_files:
        if should_ignore_path(java_file):
            continue

        try:
            entities, embeddables, mapped = parse_java_file(
                java_file, repository_path
            )
            all_entities.extend(entities)
            all_embeddables.extend(embeddables)
            all_mapped.extend(mapped)
            if entities or embeddables or mapped:
                java_count += 1
        except Exception as exc:
            print(f"[WARN] Error analizando {java_file}: {exc}")

    # --- Hibernate XML ---
    xml_files = list(repository_path.rglob("*.hbm.xml"))
    xml_count = 0

    for xml_file in xml_files:
        if should_ignore_path(xml_file):
            continue

        try:
            entities = parse_hibernate_xml(xml_file, repository_path)
            all_entities.extend(entities)
            if entities:
                xml_count += 1
        except Exception as exc:
            print(f"[WARN] Error analizando {xml_file}: {exc}")

    print(
        f"  -> {java_count} archivos Java con entidades, "
        f"{xml_count} archivos Hibernate XML"
    )

    return all_entities, all_embeddables, all_mapped


# ============================================================
# ESCANEO MULTIPLE
# ============================================================

def scan_all(repositories_root: Path) -> ScanResult:
    """
    Escanea todos los repositorios dentro de un directorio raiz.

    Cada subdirectorio se considera un repositorio independiente.
    """
    if not repositories_root.exists():
        raise SystemExit(
            f"El directorio no existe: {repositories_root}"
        )

    # Buscar subdirectorios que sean repositorios
    repos = [
        p for p in repositories_root.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    ]

    if not repos:
        print(
            f"[WARN] No se encontraron repositorios "
            f"en {repositories_root}"
        )

    result = ScanResult()

    for repo in sorted(repos):
        repo_name = repo.name
        if repo_name not in result.repositories:
            result.repositories.append(repo_name)

        entities, embeddables, mapped = scan_repository(repo)

        result.entities.extend(entities)
        result.embeddables.extend(embeddables)
        result.mapped_superclasses.extend(mapped)

    return result
