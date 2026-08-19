"""
Parser de entidades JPA basado en Tree-sitter.

Analiza archivos .java para detectar:
    - @Entity               -> Entidad JPA (tabla)
    - @Embeddable           -> Tipo embebido (composicion)
    - @MappedSuperclass     -> Superclase mapeada (herencia)
    - @Table                -> Nombre de tabla
    - @Column               -> Mapeo de columna
    - @Id                   -> Clave primaria
    - @GeneratedValue       -> Estrategia de generacion
    - @JoinColumn           -> Columna FK en relaciones
    - @JoinTable            -> Tabla intermedia en N:M
    - @OneToOne / @OneToMany / @ManyToOne / @ManyToMany
    - @Embedded / @EmbeddedId -> Campos embebidos
    - @Inheritance           -> Estrategia de herencia

Este parser NO compila ni ejecuta el codigo. Solo analiza la
estructura del AST para extraer metadatos de persistencia.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from tree_sitter import Node

from .models import (
    Embeddable,
    Entity,
    Evidence,
    Field,
    MappedSuperclass,
    Relation,
    SourceLocation,
)
from .utils import (
    PARSER,
    annotation_argument,
    annotation_boolean_argument,
    extract_annotation_name,
    extract_generic_inner_type,
    extract_simple_type,
    extract_type,
    find_annotation,
    find_child_by_type,
    find_descendant_by_type,
    get_annotations,
    line_number,
    node_text,
    read_bytes,
    repository_name,
)


# ============================================================
# MAPA DE ANOTACIONES DE RELACION
# ============================================================

RELATION_CARDINALITY = {
    "OneToOne": "1:1",
    "OneToMany": "1:N",
    "ManyToOne": "N:1",
    "ManyToMany": "N:M",
}

RELATION_ANNOTATIONS = frozenset(RELATION_CARDINALITY.keys())


# ============================================================
# CLASIFICACION DE CLASE
# ============================================================

def _classify_class(
    annotations: List[Dict[str, Any]],
) -> Optional[str]:
    """
    Clasifica una clase segun sus anotaciones de persistencia.

    Devuelve:
        "entity"              si tiene @Entity
        "embeddable"          si tiene @Embeddable
        "mapped_superclass"   si tiene @MappedSuperclass
        None                  si no es una clase de persistencia
    """
    if find_annotation(annotations, "Entity"):
        return "entity"
    if find_annotation(annotations, "Embeddable"):
        return "embeddable"
    if find_annotation(annotations, "MappedSuperclass"):
        return "mapped_superclass"
    return None


# ============================================================
# NOMBRE DE CLASE Y FQN
# ============================================================

def _extract_class_name(class_node: Node, source: bytes) -> Optional[str]:
    """Extrae el nombre simple de una declaracion de clase."""
    for child in class_node.children:
        if child.type == "identifier":
            return node_text(child, source)
    return None


def _extract_fqn(
    class_node: Node, source: bytes, package: Optional[str]
) -> str:
    """Construye el nombre calificado completo (FQN) de una clase."""
    simple_name = _extract_class_name(class_node, source) or "Unknown"
    if package:
        return f"{package}.{simple_name}"
    return simple_name


# ============================================================
# PAQUETE E IMPORTS
# ============================================================

RE_PACKAGE = re.compile(r"package\s+([\w.]+)")
RE_IMPORT = re.compile(r"import\s+([\w.$*]+)")


def _extract_package(root: Node, source: bytes) -> Optional[str]:
    """Extrae el paquete del archivo Java."""
    for child in root.children:
        if child.type == "package_declaration":
            text = node_text(child, source)
            match = RE_PACKAGE.search(text)
            if match:
                return match.group(1)
    return None


def _extract_imports(root: Node, source: bytes) -> Set[str]:
    """Extrae todos los imports del archivo Java."""
    imports = set()
    for child in root.children:
        if child.type == "import_declaration":
            text = node_text(child, source)
            match = RE_IMPORT.search(text)
            if match:
                imports.add(match.group(1))
    return imports


# ============================================================
# CAMPOS
# ============================================================

def _extract_fields(
    class_node: Node,
    source: bytes,
    repository: str,
    file_path: str,
) -> List[Field]:
    """
    Extrae todos los campos de una clase Java y los mapea
    a columnas de base de datos.
    """
    fields = []

    body = find_child_by_type(class_node, "class_body")
    if not body:
        return fields

    for child in body.children:
        if child.type != "field_declaration":
            continue

        field_obj = _parse_field(child, source, repository, file_path)
        if field_obj:
            fields.append(field_obj)

    return fields


def _parse_field(
    field_node: Node,
    source: bytes,
    repository: str,
    file_path: str,
) -> Optional[Field]:
    """Parsea un nodo field_declaration y devuelve un objeto Field."""
    annotations = get_annotations(field_node, source)
    field_type = extract_type(field_node, source)

    if not field_type:
        return None

    declarator = find_descendant_by_type(field_node, "variable_declarator")
    if not declarator:
        return None

    identifier = find_child_by_type(declarator, "identifier")
    if not identifier:
        return None

    field_name = node_text(identifier, source)

    # Columna
    col_annotation = find_annotation(annotations, "Column")
    column_name = annotation_argument(col_annotation, "name")
    if not column_name:
        column_name = field_name.upper()

    # Clave primaria
    id_annotation = find_annotation(annotations, "Id")
    embedded_id = find_annotation(annotations, "EmbeddedId")

    # Atributos de @Column
    nullable = annotation_boolean_argument(col_annotation, "nullable")
    length_str = annotation_argument(col_annotation, "length")
    length = int(length_str) if length_str else None
    precision_str = annotation_argument(col_annotation, "precision")
    precision = int(precision_str) if precision_str else None
    scale_str = annotation_argument(col_annotation, "scale")
    scale = int(scale_str) if scale_str else None
    insertable = annotation_boolean_argument(col_annotation, "insertable")
    updatable = annotation_boolean_argument(col_annotation, "updatable")
    unique = annotation_boolean_argument(col_annotation, "unique")

    raw_anns = [a["raw"] for a in annotations]

    return Field(
        name=field_name,
        type=field_type,
        column=column_name,
        primary_key=id_annotation is not None or embedded_id is not None,
        nullable=nullable,
        length=length,
        precision=precision,
        scale=scale,
        insertable=insertable,
        updatable=updatable,
        unique=unique or False,
        source=SourceLocation(
            repository=repository,
            file=file_path,
            line=line_number(field_node),
        ),
        raw_annotations=raw_anns,
    )


# ============================================================
# RELACIONES
# ============================================================

def _extract_relations(
    class_node: Node,
    source: bytes,
    repository: str,
    file_path: str,
    imports: Set[str],
) -> List[Relation]:
    """Extrae las relaciones entre entidades."""
    relations = []

    body = find_child_by_type(class_node, "class_body")
    if not body:
        return relations

    for child in body.children:
        if child.type != "field_declaration":
            continue

        rel = _parse_relation_field(
            child, source, repository, file_path, imports
        )
        if rel:
            relations.append(rel)

    return relations


def _parse_relation_field(
    field_node: Node,
    source: bytes,
    repository: str,
    file_path: str,
    imports: Set[str],
) -> Optional[Relation]:
    """Parsea un campo que contiene una anotacion de relacion."""
    annotations = get_annotations(field_node, source)

    rel_annotation = None
    cardinality = None

    for ann in annotations:
        if ann["name"] in RELATION_ANNOTATIONS:
            rel_annotation = ann
            cardinality = RELATION_CARDINALITY[ann["name"]]
            break

    if not cardinality:
        return None

    field_type = extract_type(field_node, source) or ""

    declarator = find_descendant_by_type(field_node, "variable_declarator")
    field_name = ""
    if declarator:
        identifier = find_child_by_type(declarator, "identifier")
        if identifier:
            field_name = node_text(identifier, source)

    target_type, target_entity = _resolve_relation_target(
        field_type, rel_annotation["name"], imports
    )

    # @JoinColumn
    join_col_annotation = find_annotation(annotations, "JoinColumn")
    join_column = annotation_argument(join_col_annotation, "name")

    # @JoinTable
    join_tab_annotation = find_annotation(annotations, "JoinTable")
    join_table = annotation_argument(join_tab_annotation, "name")
    inverse_join_column = None

    if join_tab_annotation:
        raw = join_tab_annotation["raw"]

        # joinColumns = @JoinColumn(name = "...")
        if not join_column:
            jc_match = re.search(
                r'joinColumns\s*=\s*@JoinColumn\s*\(\s*name\s*=\s*["\']'
                r'([^"\']+)["\']',
                raw,
            )
            if jc_match:
                join_column = jc_match.group(1)

        # inverseJoinColumns = @JoinColumn(name = "...")
        inv_match = re.search(
            r'inverseJoinColumns\s*=\s*@JoinColumn\s*\(\s*name\s*=\s*["\']'
            r'([^"\']+)["\']',
            raw,
        )
        if inv_match:
            inverse_join_column = inv_match.group(1)

    mapped_by = annotation_argument(rel_annotation, "mappedBy")
    cascade_raw = annotation_argument(rel_annotation, "cascade")
    fetch_raw = annotation_argument(rel_annotation, "fetch")
    orphan_removal = annotation_boolean_argument(
        rel_annotation, "orphanRemoval"
    )

    return Relation(
        field=field_name,
        target_type=field_type,
        target_entity=target_entity,
        cardinality=cardinality,
        join_column=join_column,
        join_table=join_table,
        inverse_join_column=inverse_join_column,
        mapped_by=mapped_by,
        cascade=cascade_raw,
        fetch=fetch_raw,
        orphan_removal=orphan_removal,
        source=SourceLocation(
            repository=repository,
            file=file_path,
            line=line_number(field_node),
        ),
        raw_annotation=rel_annotation["raw"],
    )


def _resolve_relation_target(
    field_type: str,
    annotation_name: str,
    imports: Set[str],
) -> tuple:
    """
    Resuelve el tipo destino de una relacion.

    Para colecciones (List<Pedido>), extrae el tipo interior.
    Devuelve (target_type_raw, target_entity_name).
    """
    inner_type = extract_generic_inner_type(field_type)

    if inner_type:
        raw_type = inner_type
    else:
        raw_type = field_type

    target_entity = raw_type.split(".")[-1] if raw_type else None

    return raw_type, target_entity


# ============================================================
# INHERITANCE
# ============================================================

def _extract_inheritance(
    class_node: Node, source: bytes
) -> Optional[str]:
    """
    Extrae la estrategia de herencia de @Inheritance.
    Devuelve SINGLE_TABLE, JOINED, TABLE_PER_CLASS o None.
    """
    annotations = get_annotations(class_node, source)
    inheritance_ann = find_annotation(annotations, "Inheritance")

    if not inheritance_ann:
        return None

    strategy = annotation_argument(inheritance_ann, "strategy")

    if strategy:
        return strategy.split(".")[-1]

    return "SINGLE_TABLE"


# ============================================================
# CONSTRUCTORES DE OBJETOS DE MODELO
# ============================================================

def _build_entity(
    class_node: Node,
    source: bytes,
    package: Optional[str],
    repository: str,
    file_path: str,
    imports: Set[str],
) -> Entity:
    """Construye un objeto Entity desde un nodo de clase Java."""
    annotations = get_annotations(class_node, source)
    class_name = _extract_class_name(class_node, source) or "Unknown"
    fqn = _extract_fqn(class_node, source, package)

    table_annotation = find_annotation(annotations, "Table")
    table_name = annotation_argument(table_annotation, "name")
    if not table_name:
        table_name = class_name.upper()

    inheritance = _extract_inheritance(class_node, source)

    fields = _extract_fields(class_node, source, repository, file_path)
    relations = _extract_relations(
        class_node, source, repository, file_path, imports
    )

    entity_annotation = find_annotation(annotations, "Entity")
    all_raw = [a["raw"] for a in annotations]

    return Entity(
        name=class_name,
        table=table_name,
        entity_type="JPA_ENTITY",
        fully_qualified_name=fqn,
        package=package,
        fields=fields,
        relations=relations,
        annotations=all_raw,
        inheritance=inheritance,
        source=SourceLocation(
            repository=repository,
            file=file_path,
            line=line_number(class_node),
        ),
        evidence=Evidence(
            kind="jpa_annotation",
            entity_raw=(
                entity_annotation["raw"] if entity_annotation else None
            ),
            table_raw=(
                table_annotation["raw"] if table_annotation else None
            ),
        ),
    )


def _build_embeddable(
    class_node: Node,
    source: bytes,
    package: Optional[str],
    repository: str,
    file_path: str,
) -> Embeddable:
    """Construye un objeto Embeddable desde un nodo de clase Java."""
    class_name = _extract_class_name(class_node, source) or "Unknown"
    fqn = _extract_fqn(class_node, source, package)

    fields = _extract_fields(class_node, source, repository, file_path)

    return Embeddable(
        name=class_name,
        fully_qualified_name=fqn,
        package=package,
        fields=fields,
        source=SourceLocation(
            repository=repository,
            file=file_path,
            line=line_number(class_node),
        ),
    )


def _build_mapped_superclass(
    class_node: Node,
    source: bytes,
    package: Optional[str],
    repository: str,
    file_path: str,
) -> MappedSuperclass:
    """Construye un objeto MappedSuperclass desde un nodo de clase Java."""
    class_name = _extract_class_name(class_node, source) or "Unknown"
    fqn = _extract_fqn(class_node, source, package)

    fields = _extract_fields(class_node, source, repository, file_path)

    return MappedSuperclass(
        name=class_name,
        fully_qualified_name=fqn,
        package=package,
        fields=fields,
        source=SourceLocation(
            repository=repository,
            file=file_path,
            line=line_number(class_node),
        ),
    )


# ============================================================
# ENTRADA PRINCIPAL: PARSEO DE ARCHIVO JAVA
# ============================================================

def parse_java_file(
    path: Path,
    root_path: Path,
) -> tuple:
    """
    Analiza un archivo .java y extrae entidades, embeddables
    y mapped superclasses.

    Devuelve: (entities, embeddables, mapped_superclasses)
    """
    source = read_bytes(path)
    tree = PARSER.parse(source)
    root = tree.root_node

    package = _extract_package(root, source)
    imports = _extract_imports(root, source)

    repo = repository_name(path, root_path)
    file_path = str(path.relative_to(root_path))

    entities = []
    embeddables = []
    mapped_superclasses = []

    for class_node in find_descendants_by_type(root, "class_declaration"):
        annotations = get_annotations(class_node, source)
        kind = _classify_class(annotations)

        if kind == "entity":
            entity = _build_entity(
                class_node, source, package,
                repo, file_path, imports,
            )
            entities.append(entity)

        elif kind == "embeddable":
            emb = _build_embeddable(
                class_node, source, package,
                repo, file_path,
            )
            embeddables.append(emb)

        elif kind == "mapped_superclass":
            ms = _build_mapped_superclass(
                class_node, source, package,
                repo, file_path,
            )
            mapped_superclasses.append(ms)

    return entities, embeddables, mapped_superclasses


def find_descendants_by_type(node: Node, node_type: str) -> List[Node]:
    """Busca recursivamente todos los descendientes con el tipo indicado."""
    results = []
    if node.type == node_type:
        results.append(node)
    for child in node.children:
        results.extend(find_descendants_by_type(child, node_type))
    return results
