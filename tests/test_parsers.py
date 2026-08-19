"""
Tests unitarios para los parsers de entidades.

Valida que los parsers JPA y Hibernate XML extraen correctamente
la informacion de entidades a partir de los fixtures de prueba.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ajustar path para importar desde src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from entity_detector.java_jpa_parser import parse_java_file
from entity_detector.hibernate_xml_parser import parse_hibernate_xml
from entity_detector.scanner import scan_repository


# ============================================================
# PATHS
# ============================================================

FIXTURES = Path(__file__).resolve().parent / "fixtures"
JAVA_FIXTURES = FIXTURES / "java"
HIBERNATE_FIXTURES = FIXTURES / "hibernate"
JPA_DIR = JAVA_FIXTURES / "jpa"
NON_ENTITY_DIR = JAVA_FIXTURES / "non_entity"


# ============================================================
# TESTS: JPA
# ============================================================

def test_jpa_entity_detection():
    """Detecta @Entity en clases simples."""
    path = JPA_DIR / "Cliente.java"
    entities, embeddables, mapped = parse_java_file(path, JAVA_FIXTURES)

    assert len(entities) == 1, f"Esperaba 1 entidad, encontro {len(entities)}"
    e = entities[0]
    assert e.name == "Cliente"
    assert e.table == "CLIENTES"
    assert e.entity_type == "JPA_ENTITY"
    assert e.package == "com.ejemplo.model"
    print("[PASS] test_jpa_entity_detection")


def test_jpa_fields():
    """Extrae campos con tipos, columnas y atributos."""
    path = JPA_DIR / "Cliente.java"
    entities, _, _ = parse_java_file(path, JAVA_FIXTURES)
    e = entities[0]

    assert len(e.fields) == 6, f"Esperaba 6 campos, encontro {len(e.fields)}"

    # Campo PK
    id_field = next(f for f in e.fields if f.name == "id")
    assert id_field.primary_key is True
    assert id_field.column == "ID_CLIENTE"

    # Campo con length y nullable
    nombre = next(f for f in e.fields if f.name == "nombre")
    assert nombre.column == "NOMBRE"
    assert nombre.length == 100
    assert nombre.nullable is False

    # Campo unique
    email = next(f for f in e.fields if f.name == "email")
    assert email.unique is True

    print("[PASS] test_jpa_fields")


def test_jpa_relations():
    """Extrae relaciones @OneToMany, @ManyToOne."""
    path = JPA_DIR / "Cliente.java"
    entities, _, _ = parse_java_file(path, JAVA_FIXTURES)
    e = entities[0]

    assert len(e.relations) == 2, f"Esperaba 2 relaciones, encontro {len(e.relations)}"

    # @OneToMany
    one_to_many = next(r for r in e.relations if r.cardinality == "1:N")
    assert one_to_many.field == "pedidos"
    assert one_to_many.target_entity == "Pedido"
    assert one_to_many.mapped_by == "cliente"

    # @ManyToOne
    many_to_one = next(r for r in e.relations if r.cardinality == "N:1")
    assert many_to_one.field == "zona"
    assert many_to_one.target_entity == "Zona"
    assert many_to_one.join_column == "ID_ZONA"

    print("[PASS] test_jpa_relations")


def test_jpa_join_table():
    """Extrae @JoinTable en relaciones N:M."""
    path = JPA_DIR / "Pedido.java"
    entities, _, _ = parse_java_file(path, JAVA_FIXTURES)
    e = entities[0]

    many_to_many = next(
        (r for r in e.relations if r.cardinality == "N:M"), None
    )
    assert many_to_many is not None, "No encontro relacion N:M"
    assert many_to_many.join_table == "PEDIDO_PRODUCTOS"
    assert many_to_many.join_column == "ID_PEDIDO"
    assert many_to_many.inverse_join_column == "ID_PRODUCTO"

    print("[PASS] test_jpa_join_table")


def test_jpa_one_to_one():
    """Extrae @OneToOne."""
    path = JPA_DIR / "Producto.java"
    entities, _, _ = parse_java_file(path, JAVA_FIXTURES)
    e = entities[0]

    one_to_one = next(
        (r for r in e.relations if r.cardinality == "1:1"), None
    )
    assert one_to_one is not None, "No encontro relacion 1:1"
    assert one_to_one.target_entity == "Categoria"
    assert one_to_one.join_column == "ID_CATEGORIA"

    print("[PASS] test_jpa_one_to_one")


def test_jpa_mapped_superclass():
    """Detecta @MappedSuperclass."""
    path = JPA_DIR / "BaseEntity.java"
    _, embeddables, mapped = parse_java_file(path, JAVA_FIXTURES)

    assert len(mapped) == 1, f"Esperaba 1 mapped superclass, encontro {len(mapped)}"
    ms = mapped[0]
    assert ms.name == "BaseEntity"
    assert len(ms.fields) == 3

    print("[PASS] test_jpa_mapped_superclass")


def test_jpa_embeddable():
    """Detecta @Embeddable."""
    path = JPA_DIR / "Direccion.java"
    _, embeddables, _ = parse_java_file(path, JAVA_FIXTURES)

    assert len(embeddables) == 1, f"Esperaba 1 embeddable, encontro {len(embeddables)}"
    emb = embeddables[0]
    assert emb.name == "Direccion"
    assert len(emb.fields) == 4

    print("[PASS] test_jpa_embeddable")


def test_jpa_inheritance():
    """Detecta @Inheritance."""
    path = JPA_DIR / "Zona.java"
    entities, _, _ = parse_java_file(path, JAVA_FIXTURES)
    e = entities[0]

    assert e.inheritance == "SINGLE_TABLE"

    print("[PASS] test_jpa_inheritance")


def test_non_entity_ignored():
    """Clases sin @Entity son ignoradas."""
    path = NON_ENTITY_DIR / "ClienteService.java"
    entities, embeddables, mapped = parse_java_file(path, JAVA_FIXTURES)

    assert len(entities) == 0
    assert len(embeddables) == 0
    assert len(mapped) == 0

    print("[PASS] test_non_entity_ignored")


def test_generated_values():
    """Detecta @GeneratedValue."""
    path = JPA_DIR / "Pedido.java"
    entities, _, _ = parse_java_file(path, JAVA_FIXTURES)
    e = entities[0]

    id_field = next(f for f in e.fields if f.name == "id")
    assert id_field.primary_key is True

    print("[PASS] test_generated_values")


def test_column_default_naming():
    """Sin @Column, la columna se deriva del nombre del campo en mayusculas."""
    path = JPA_DIR / "Pedido.java"
    entities, _, _ = parse_java_file(path, JAVA_FIXTURES)
    e = entities[0]

    fecha = next(f for f in e.fields if f.name == "fecha")
    assert fecha.column == "FECHA"

    print("[PASS] test_column_default_naming")


# ============================================================
# TESTS: HIBERNATE XML
# ============================================================

def test_hibernate_entity_detection():
    """Detecta entidades en archivos .hbm.xml."""
    path = HIBERNATE_FIXTURES / "mapping.hbm.xml"
    entities = parse_hibernate_xml(path, HIBERNATE_FIXTURES)

    assert len(entities) == 3, f"Esperaba 3 entidades, encontro {len(entities)}"

    names = {e.name for e in entities}
    assert "ClienteHibernate" in names
    assert "PedidoHibernate" in names
    assert "ProductoHibernate" in names

    print("[PASS] test_hibernate_entity_detection")


def test_hibernate_fields():
    """Extrae campos de entidades Hibernate XML."""
    path = HIBERNATE_FIXTURES / "mapping.hbm.xml"
    entities = parse_hibernate_xml(path, HIBERNATE_FIXTURES)

    cliente = next(e for e in entities if e.name == "ClienteHibernate")
    assert len(cliente.fields) >= 3

    id_field = next(f for f in cliente.fields if f.name == "id")
    assert id_field.primary_key is True
    assert id_field.column == "ID_CLIENTE"

    nombre = next(f for f in cliente.fields if f.name == "nombre")
    assert nombre.column == "NOMBRE"
    assert nombre.nullable is False

    print("[PASS] test_hibernate_fields")


def test_hibernate_relations():
    """Extrae relaciones de entidades Hibernate XML."""
    path = HIBERNATE_FIXTURES / "mapping.hbm.xml"
    entities = parse_hibernate_xml(path, HIBERNATE_FIXTURES)

    cliente = next(e for e in entities if e.name == "ClienteHibernate")
    rels = cliente.relations

    many_to_one = next(
        (r for r in rels if r.cardinality == "N:1"), None
    )
    assert many_to_one is not None, "No encontro N:1"
    assert many_to_one.field == "zona"
    assert many_to_one.join_column == "ID_ZONA"

    one_to_many = next(
        (r for r in rels if r.cardinality == "1:N"), None
    )
    assert one_to_many is not None, "No encontro 1:N"
    assert one_to_many.target_entity == "PedidoHibernate"

    print("[PASS] test_hibernate_relations")


def test_hibernate_many_to_many():
    """Extrae many-to-many de Hibernate XML."""
    path = HIBERNATE_FIXTURES / "mapping.hbm.xml"
    entities = parse_hibernate_xml(path, HIBERNATE_FIXTURES)

    pedido = next(e for e in entities if e.name == "PedidoHibernate")
    rels = pedido.relations

    many_to_many = next(
        (r for r in rels if r.cardinality == "N:M"), None
    )
    assert many_to_many is not None, "No encontro N:M"
    assert many_to_many.join_table == "PEDIDO_PRODUCTOS_HIB"

    print("[PASS] test_hibernate_many_to_many")


# ============================================================
# TESTS: SCANNER
# ============================================================

def test_scanner_full():
    """Escanea el directorio completo de fixtures Java JPA."""
    result = scan_repository(JAVA_FIXTURES)

    entities, embeddables, mapped = result

    assert len(entities) >= 5, f"Esperaba >=5 entidades, encontro {len(entities)}"
    assert len(embeddables) >= 1, f"Esperaba >=1 embeddable, encontro {len(embeddables)}"
    assert len(mapped) >= 1, f"Esperaba >=1 mapped, encontro {len(mapped)}"

    print("[PASS] test_scanner_full")


# ============================================================
# TESTS: MODELOS (serializacion JSON)
# ============================================================

def test_entity_serialization():
    """Las entidades se serializan correctamente a JSON."""
    path = JPA_DIR / "Cliente.java"
    entities, _, _ = parse_java_file(path, JAVA_FIXTURES)
    e = entities[0]

    d = e.to_dict()
    assert isinstance(d, dict)
    assert d["name"] == "Cliente"
    assert d["table"] == "CLIENTES"
    assert "fields" in d
    assert "relations" in d
    assert "source" in d
    assert "evidence" in d

    # Verificar que es serializable a JSON
    json_str = json.dumps(d, ensure_ascii=False)
    assert isinstance(json_str, str)

    print("[PASS] test_entity_serialization")


# ============================================================
# RUNNER
# ============================================================

ALL_TESTS = [
    test_jpa_entity_detection,
    test_jpa_fields,
    test_jpa_relations,
    test_jpa_join_table,
    test_jpa_one_to_one,
    test_jpa_mapped_superclass,
    test_jpa_embeddable,
    test_jpa_inheritance,
    test_non_entity_ignored,
    test_generated_values,
    test_column_default_naming,
    test_hibernate_entity_detection,
    test_hibernate_fields,
    test_hibernate_relations,
    test_hibernate_many_to_many,
    test_scanner_full,
    test_entity_serialization,
]


def run_all():
    """Ejecuta todos los tests."""
    passed = 0
    failed = 0
    errors = []

    for test_fn in ALL_TESTS:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            failed += 1
            errors.append((test_fn.__name__, str(e)))
            print(f"[FAIL] {test_fn.__name__}: {e}")
        except Exception as e:
            failed += 1
            errors.append((test_fn.__name__, str(e)))
            print(f"[ERROR] {test_fn.__name__}: {e}")

    print()
    print("=" * 60)
    print(f"Tests: {passed} pasaron, {failed} fallaron de {len(ALL_TESTS)}")

    if errors:
        print()
        for name, msg in errors:
            print(f"  FALLO: {name} -> {msg}")

    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
