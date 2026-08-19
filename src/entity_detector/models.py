"""
Modelo de datos normalizado para entidades de persistencia.

Define las estructuras de datos que representan entidades, campos,
relaciones y metadatos extraidos de repositorios Java. Este modelo
es independiente del parser utilizado y es serializable a JSON.

Estructura principal:
    ScanResult          -> Resultado completo del escaneo
    Entity              -> Una entidad de base de datos (tabla)
    Embeddable          -> Tipo embebido (composicion)
    MappedSuperclass    -> Superclase mapeada (herencia)
    Field               -> Campo/columna de una entidad
    Relation            -> Relacion entre dos entidades
    SourceLocation      -> Ubicacion en el codigo fuente
    Evidence            -> Evidencia utilizada para detectar cada elemento
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ============================================================
# UBICACION FUENTE
# ============================================================

@dataclass
class SourceLocation:
    """Ubicacion de un elemento en el codigo fuente."""

    repository: str
    file: str
    line: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository": self.repository,
            "file": self.file,
            "line": self.line,
        }


# ============================================================
# EVIDENCIA
# ============================================================

@dataclass
class Evidence:
    """
    Evidencia cruda que el parser utilizo para identificar
    un elemento. Permite trazabilidad y revision manual.
    """

    kind: str
    entity_raw: Optional[str] = None
    table_raw: Optional[str] = None
    join_column_raw: Optional[str] = None
    join_table_raw: Optional[str] = None
    inheritance_raw: Optional[str] = None
    extra: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {"kind": self.kind}
        if self.entity_raw:
            result["entity"] = self.entity_raw
        if self.table_raw:
            result["table"] = self.table_raw
        if self.join_column_raw:
            result["join_column"] = self.join_column_raw
        if self.join_table_raw:
            result["join_table"] = self.join_table_raw
        if self.inheritance_raw:
            result["inheritance"] = self.inheritance_raw
        if self.extra:
            result["extra"] = self.extra
        return result


# ============================================================
# CAMPO
# ============================================================

@dataclass
class Field:
    """
    Campo de una entidad, mapeado a una columna de base de datos.
    """

    name: str
    type: str
    column: str
    primary_key: bool = False
    nullable: Optional[bool] = None
    length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    insertable: Optional[bool] = None
    updatable: Optional[bool] = None
    unique: Optional[bool] = False
    source: Optional[SourceLocation] = None
    raw_annotations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "name": self.name,
            "type": self.type,
            "column": self.column,
            "primary_key": self.primary_key,
        }
        if self.nullable is not None:
            result["nullable"] = self.nullable
        if self.length is not None:
            result["length"] = self.length
        if self.precision is not None:
            result["precision"] = self.precision
        if self.scale is not None:
            result["scale"] = self.scale
        if self.insertable is not None:
            result["insertable"] = self.insertable
        if self.updatable is not None:
            result["updatable"] = self.updatable
        if self.unique:
            result["unique"] = self.unique
        if self.source:
            result["source"] = self.source.to_dict()
        if self.raw_annotations:
            result["raw_annotations"] = self.raw_annotations
        return result


# ============================================================
# RELACION
# ============================================================

@dataclass
class Relation:
    """
    Relacion entre dos entidades.

    cardiadity puede ser: "1:1", "1:N", "N:1", "N:M".
    """

    field: str
    target_type: str
    target_entity: Optional[str]
    cardinality: str
    join_column: Optional[str] = None
    join_table: Optional[str] = None
    inverse_join_column: Optional[str] = None
    mapped_by: Optional[str] = None
    cascade: Optional[str] = None
    fetch: Optional[str] = None
    orphan_removal: Optional[bool] = None
    source: Optional[SourceLocation] = None
    raw_annotation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "field": self.field,
            "target_type": self.target_type,
            "cardinality": self.cardinality,
        }
        if self.target_entity:
            result["target_entity"] = self.target_entity
        if self.join_column:
            result["join_column"] = self.join_column
        if self.join_table:
            result["join_table"] = self.join_table
        if self.inverse_join_column:
            result["inverse_join_column"] = self.inverse_join_column
        if self.mapped_by:
            result["mapped_by"] = self.mapped_by
        if self.cascade:
            result["cascade"] = self.cascade
        if self.fetch:
            result["fetch"] = self.fetch
        if self.orphan_removal is not None:
            result["orphan_removal"] = self.orphan_removal
        if self.source:
            result["source"] = self.source.to_dict()
        if self.raw_annotation:
            result["raw_annotation"] = self.raw_annotation
        return result


# ============================================================
# ENTIDAD
# ============================================================

@dataclass
class Entity:
    """
    Entidad de base de datos detectada en el codigo Java.

    Puede provenir de una anotacion @Entity, una clase Hibernate XML
    mapeada, o cualquier otro mecanismo de persistencia.
    """

    name: str
    table: str
    entity_type: str
    fully_qualified_name: Optional[str] = None
    package: Optional[str] = None
    fields: List[Field] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)
    annotations: List[str] = field(default_factory=list)
    inheritance: Optional[str] = None
    source: Optional[SourceLocation] = None
    evidence: Optional[Evidence] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "name": self.name,
            "table": self.table,
            "type": self.entity_type,
        }
        if self.fully_qualified_name:
            result["fully_qualified_name"] = self.fully_qualified_name
        if self.package:
            result["package"] = self.package
        if self.fields:
            result["fields"] = [f.to_dict() for f in self.fields]
        if self.relations:
            result["relations"] = [r.to_dict() for r in self.relations]
        if self.annotations:
            result["annotations"] = self.annotations
        if self.inheritance:
            result["inheritance"] = self.inheritance
        if self.source:
            result["source"] = self.source.to_dict()
        if self.evidence:
            result["evidence"] = self.evidence.to_dict()
        return result


# ============================================================
# EMBEDDABLE
# ============================================================

@dataclass
class Embeddable:
    """Tipo embebido (composicion) detectado via @Embeddable."""

    name: str
    fully_qualified_name: Optional[str] = None
    package: Optional[str] = None
    fields: List[Field] = field(default_factory=list)
    source: Optional[SourceLocation] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {"name": self.name}
        if self.fully_qualified_name:
            result["fully_qualified_name"] = self.fully_qualified_name
        if self.package:
            result["package"] = self.package
        if self.fields:
            result["fields"] = [f.to_dict() for f in self.fields]
        if self.source:
            result["source"] = self.source.to_dict()
        return result


# ============================================================
# MAPPED SUPERCLASS
# ============================================================

@dataclass
class MappedSuperclass:
    """Superclase mapeada detectada via @MappedSuperclass."""

    name: str
    fully_qualified_name: Optional[str] = None
    package: Optional[str] = None
    fields: List[Field] = field(default_factory=list)
    source: Optional[SourceLocation] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {"name": self.name}
        if self.fully_qualified_name:
            result["fully_qualified_name"] = self.fully_qualified_name
        if self.package:
            result["package"] = self.package
        if self.fields:
            result["fields"] = [f.to_dict() for f in self.fields]
        if self.source:
            result["source"] = self.source.to_dict()
        return result


# ============================================================
# RESULTADO DEL ESCANEO
# ============================================================

@dataclass
class ScanResult:
    """Resultado completo de un escaneo de repositorios."""

    repositories: List[str] = field(default_factory=list)
    entities: List[Entity] = field(default_factory=list)
    embeddables: List[Embeddable] = field(default_factory=list)
    mapped_superclasses: List[MappedSuperclass] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": "1.0",
            "scan_date": datetime.now(timezone.utc).isoformat(),
            "repositories": self.repositories,
            "summary": {
                "entities": len(self.entities),
                "embeddables": len(self.embeddables),
                "mapped_superclasses": len(self.mapped_superclasses),
            },
            "entities": [e.to_dict() for e in self.entities],
            "embeddables": [e.to_dict() for e in self.embeddables],
            "mapped_superclasses": [
                m.to_dict() for m in self.mapped_superclasses
            ],
        }
