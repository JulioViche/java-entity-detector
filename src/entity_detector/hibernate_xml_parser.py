"""
Parser de mapeos Hibernate XML (*.hbm.xml).

Analiza archivos de mapeo Hibernate para detectar:
    - <class>               -> Entidad mapeada
    - <id>                  -> Clave primaria
    - <property>            -> Campo/propiedad
    - <many-to-one>         -> Relacion N:1
    - <one-to-many>         -> Relacion 1:N
    - <many-to-many>        -> Relacion N:M
    - <one-to-one>          -> Relacion 1:1
    - <join>                -> Tabla de join
    - <key>                 -> Clave foranea
    - <composite-id>        -> Clave compuesta
    - <discriminator>       -> Discriminador (herencia)
    - <subclass> / <joined-subclass> -> Subclases

Soporta namespaces XML comunes de Hibernate 3.x y 4.x.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import Entity, Evidence, Field, Relation, SourceLocation
from .utils import repository_name


# ============================================================
# UTILIDADES XML
# ============================================================

def _strip_ns(tag: str) -> str:
    """Elimina el namespace de un tag XML.

    Ejemplo: {http://www.hibernate.org/hbm/3.0}class -> class
    """
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _get(element: ET.Element, attr: str) -> Optional[str]:
    """Obtiene un atributo de un elemento XML, o None."""
    return element.attrib.get(attr) or None


def _local_attribs(element: ET.Element) -> Dict[str, str]:
    """Obtiene todos los atributos de un elemento sin namespace."""
    return {
        _strip_ns(k): v
        for k, v in element.attrib.items()
    }


# ============================================================
# PARSING DE CAMPOS
# ============================================================

def _parse_id_element(
    element: ET.Element,
) -> Optional[Field]:
    """Parsea un elemento <id> y devuelve un Field."""
    name = _get(element, "name")
    if not name:
        return None

    column = _get(element, "column")
    type_attr = _get(element, "type")
    length_str = _get(element, "length")
    length = int(length_str) if length_str else None

    # Buscar <column> hijo para obtener nombre de columna
    if not column:
        for child in element:
            child_tag = _strip_ns(child.tag)
            if child_tag == "column":
                column = _get(child, "name")
                if not column:
                    column = child.text.strip() if child.text else None
                break

    return Field(
        name=name,
        type=type_attr or "unknown",
        column=column or name.upper(),
        primary_key=True,
        nullable=False,
        length=length,
    )


def _parse_composite_id_element(
    element: ET.Element,
) -> List[Field]:
    """Parsea un elemento <composite-id> y devuelve una lista de Fields."""
    fields = []

    key_class = _get(element, "class")

    for child in element:
        child_tag = _strip_ns(child.tag)

        if child_tag == "key-property":
            name = _get(child, "name")
            if not name:
                continue

            column = _get(child, "column")
            type_attr = _get(child, "type")
            length_str = _get(child, "length")
            length = int(length_str) if length_str else None

            fields.append(Field(
                name=name,
                type=type_attr or "unknown",
                column=column or name.upper(),
                primary_key=True,
                nullable=False,
                length=length,
            ))

    return fields


def _parse_property_element(
    element: ET.Element,
) -> Optional[Field]:
    """Parsea un elemento <property> y devuelve un Field."""
    name = _get(element, "name")
    if not name:
        return None

    column = _get(element, "column")
    type_attr = _get(element, "type")
    not_null = _get(element, "not-null")
    unique = _get(element, "unique")
    length_str = _get(element, "length")
    length = int(length_str) if length_str else None

    # Buscar <column> hijo
    if not column:
        for child in element:
            child_tag = _strip_ns(child.tag)
            if child_tag == "column":
                column = _get(child, "name")
                if not column:
                    column = child.text.strip() if child.text else None
                break

    nullable = None
    if not_null is not None:
        nullable = not_null.lower() == "false"

    return Field(
        name=name,
        type=type_attr or "unknown",
        column=column or name.upper(),
        primary_key=False,
        nullable=nullable,
        unique=unique.lower() == "true" if unique else False,
        length=length,
    )


# ============================================================
# PARSING DE RELACIONES
# ============================================================

def _parse_many_to_one(
    element: ET.Element,
) -> Optional[Relation]:
    """Parsea un elemento <many-to-one> y devuelve una Relation."""
    name = _get(element, "name")
    if not name:
        return None

    class_ref = _get(element, "class")
    column = _get(element, "column")
    not_null = _get(element, "not-null")

    nullable = None
    if not_null is not None:
        nullable = not_null.lower() == "false"

    target_entity = None
    if class_ref:
        target_entity = class_ref.split(".")[-1]

    return Relation(
        field=name,
        target_type=class_ref or "unknown",
        target_entity=target_entity,
        cardinality="N:1",
        join_column=column,
        source=None,
    )


def _parse_one_to_many(
    element: ET.Element,
) -> Optional[Relation]:
    """Parsea un elemento <one-to-many> y devuelve una Relation."""
    name = _get(element, "name") or ""
    class_ref = _get(element, "class")
    column = _get(element, "column")

    target_entity = None
    if class_ref:
        target_entity = class_ref.split(".")[-1]

    return Relation(
        field=name,
        target_type=class_ref or "unknown",
        target_entity=target_entity,
        cardinality="1:N",
        join_column=column,
        source=None,
    )


def _parse_many_to_many(
    element: ET.Element,
) -> Optional[Relation]:
    """Parsea un elemento <many-to-many> y devuelve una Relation."""
    name = _get(element, "name")
    if not name:
        return None

    class_ref = _get(element, "class")
    table = _get(element, "table")
    column = _get(element, "column")

    target_entity = None
    if class_ref:
        target_entity = class_ref.split(".")[-1]

    return Relation(
        field=name,
        target_type=class_ref or "unknown",
        target_entity=target_entity,
        cardinality="N:M",
        join_column=column,
        join_table=table,
        source=None,
    )


def _parse_one_to_one(
    element: ET.Element,
) -> Optional[Relation]:
    """Parsea un elemento <one-to-one> y devuelve una Relation."""
    name = _get(element, "name")
    if not name:
        return None

    class_ref = _get(element, "class")
    column = _get(element, "column")
    constrained = _get(element, "constrained")

    target_entity = None
    if class_ref:
        target_entity = class_ref.split(".")[-1]

    return Relation(
        field=name,
        target_type=class_ref or "unknown",
        target_entity=target_entity,
        cardinality="1:1",
        join_column=column,
        source=None,
    )


# ============================================================
# PROCESAMIENTO DE CLASE HIBERNATE
# ============================================================

def _parse_hibernate_class(
    class_element: ET.Element,
    repository: str,
    file_path: str,
) -> Optional[Entity]:
    """
    Parsea un elemento <class> de Hibernate XML y devuelve
    un objeto Entity.
    """
    class_name = _get(class_element, "name")
    table_name = _get(class_element, "table")

    if not class_name:
        return None

    simple_name = class_name.split(".")[-1]
    package = (
        ".".join(class_name.split(".")[:-1])
        if "." in class_name
        else None
    )

    fields: List[Field] = []
    relations: List[Relation] = []

    # <meta> tag optional
    # <discriminator-value>

    for child in class_element:
        child_tag = _strip_ns(child.tag)

        if child_tag == "id":
            f = _parse_id_element(child)
            if f:
                fields.append(f)

        elif child_tag == "composite-id":
            fields.extend(_parse_composite_id_element(child))

        elif child_tag == "property":
            f = _parse_property_element(child)
            if f:
                fields.append(f)

        elif child_tag == "many-to-one":
            r = _parse_many_to_one(child)
            if r:
                relations.append(r)

        elif child_tag == "one-to-many":
            r = _parse_one_to_many(child)
            if r:
                relations.append(r)

        elif child_tag == "many-to-many":
            r = _parse_many_to_many(child)
            if r:
                relations.append(r)

        elif child_tag == "one-to-one":
            r = _parse_one_to_one(child)
            if r:
                relations.append(r)

        elif child_tag == "join":
            # <join table="..."> puede contener mas campos
            join_table = _get(child, "table")
            for join_child in child:
                jct = _strip_ns(join_child.tag)
                if jct == "key":
                    pass
                elif jct == "property":
                    f = _parse_property_element(join_child)
                    if f:
                        fields.append(f)
                elif jct == "many-to-one":
                    r = _parse_many_to_one(join_child)
                    if r:
                        if join_table:
                            r.join_table = join_table
                        relations.append(r)

    return Entity(
        name=simple_name,
        table=table_name or simple_name.upper(),
        entity_type="HIBERNATE_XML",
        fully_qualified_name=class_name,
        package=package,
        fields=fields,
        relations=relations,
        annotations=[],
        source=SourceLocation(
            repository=repository,
            file=file_path,
            line=0,
        ),
        evidence=Evidence(
            kind="hibernate_xml",
            entity_raw=f'<class name="{class_name}"',
            table_raw=(
                f'<class ... table="{table_name}"'
                if table_name
                else None
            ),
        ),
    )


# ============================================================
# ENTRADA PRINCIPAL
# ============================================================

def parse_hibernate_xml(
    path: Path,
    root_path: Path,
) -> List[Entity]:
    """
    Analiza un archivo .hbm.xml y extrae las entidades mapeadas.

    Soporta multiples elementos <class> en un solo archivo.
    """
    entities = []

    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as exc:
        print(f"[WARN] Error parseando XML {path}: {exc}")
        return entities
    except Exception as exc:
        print(f"[WARN] Error leyendo XML {path}: {exc}")
        return entities

    repo = repository_name(path, root_path)
    file_path = str(path.relative_to(root_path))

    for element in root.iter():
        tag = _strip_ns(element.tag)

        if tag == "class":
            entity = _parse_hibernate_class(element, repo, file_path)
            if entity:
                entities.append(entity)

        elif tag in ("subclass", "joined-subclass"):
            # Subclases de herencia: crear entidad separada
            subclass_name = _get(element, "name")
            if not subclass_name:
                continue

            entity = _parse_hibernate_class(element, repo, file_path)
            if entity:
                # Marcar como subclase
                parent_name = _get(element, "extends")
                if parent_name:
                    entity.annotations = [
                        f'extends="{parent_name}"'
                    ]
                entities.append(entity)

    return entities
