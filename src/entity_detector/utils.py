"""
Utilidades compartidas para los parsers.

Contiene funciones para lectura de archivos, manipulacion de nodos AST,
extraccion de anotaciones Java y expresiones regulares reutilizables.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from tree_sitter import Language, Node, Parser
import tree_sitter_java


# ============================================================
# TREE-SITTER: configuracion global
# ============================================================

JAVA_LANGUAGE = Language(tree_sitter_java.language())
PARSER = Parser(JAVA_LANGUAGE)


# ============================================================
# LECTURA DE ARCHIVOS
# ============================================================

# Directorios que se ignoran al escanear repositorios.
IGNORED_DIRS = frozenset({
    ".git", "target", "build", "out", "node_modules",
    "bin", "test-output", ".gradle", ".idea", ".settings",
})


def read_text(path: Path) -> str:
    """
    Lee un archivo de texto intentando multiples codificaciones.
    Util para repositorios legacy que pueden usar latin-1 o cp1252.
    """
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue

    return path.read_text(encoding="utf-8", errors="replace")


def read_bytes(path: Path) -> bytes:
    """Lee un archivo y lo devuelve como bytes UTF-8."""
    return read_text(path).encode("utf-8")


# ============================================================
# UTILIDADES DE NODOS AST
# ============================================================

def node_text(node: Node, source: bytes) -> str:
    """Extrae el texto crudo de un nodo del AST."""
    return source[node.start_byte:node.end_byte].decode(
        "utf-8", errors="replace"
    )


def line_number(node: Node) -> int:
    """Numero de linea (1-based) de un nodo."""
    return node.start_point[0] + 1


def children_by_type(node: Node, node_type: str) -> List[Node]:
    """Devuelve los hijos directos de un nodo que tengan el tipo indicado."""
    return [child for child in node.children if child.type == node_type]


def find_child_by_type(node: Node, node_type: str) -> Optional[Node]:
    """Devuelve el primer hijo directo con el tipo indicado, o None."""
    for child in node.children:
        if child.type == node_type:
            return child
    return None


def find_descendant_by_type(node: Node, node_type: str) -> Optional[Node]:
    """Busca recursivamente el primer descendiente con el tipo indicado."""
    if node.type == node_type:
        return node
    for child in node.children:
        result = find_descendant_by_type(child, node_type)
        if result is not None:
            return result
    return None


# ============================================================
# REPOSITORIO
# ============================================================

def repository_name(path: Path, root: Path) -> str:
    """
    Obtiene el nombre del repositorio a partir de la ruta.

    Intenta hacer relativa a 'root'. Si no puede, usa el primer
    componente de la ruta.
    """
    try:
        relative = path.relative_to(root)
        return relative.parts[0]
    except ValueError:
        pass

    # Buscar hacia arriba hasta encontrar un directorio que
    # contenga .git como indicador de raiz de repositorio.
    current = path
    while current != current.parent:
        if (current / ".git").exists():
            return current.name
        current = current.parent

    return path.parts[0] if path.parts else "unknown"


# ============================================================
# ANOTACIONES JAVA
# ============================================================

# Expresiones regulares para parsing de anotaciones.
RE_ANNOTATION_NAME = re.compile(r"@\s*([\w.$]+)")
RE_STRING_ARG = re.compile(r'(\w+)\s*=\s*["\']([^"\']+)["\']')
RE_POSITIONAL_STRING = re.compile(r'@\w+\s*\(\s*["\']([^"\']+)["\']\s*\)')


def get_annotations(node: Node, source: bytes) -> List[Dict[str, Any]]:
    """
    Extrae las anotaciones de un nodo (campo, clase, metodo).

    Busca dentro del nodo 'modifiers' las anotaciones
    marker_annotation y annotation.
    """
    annotations = []

    modifiers = find_child_by_type(node, "modifiers")
    if not modifiers:
        return annotations

    for child in modifiers.children:
        if child.type not in ("marker_annotation", "annotation"):
            continue

        raw = node_text(child, source).strip()
        name = extract_annotation_name(raw)

        annotations.append({
            "name": name,
            "raw": raw,
            "line": line_number(child),
            "node": child,
        })

    return annotations


def extract_annotation_name(raw: str) -> str:
    """
    Extrae el nombre simple de una anotacion.

    Ejemplos:
        @Entity          -> "Entity"
        @Table(...)      -> "Table"
        @javax.persistence.Entity -> "Entity"
    """
    match = RE_ANNOTATION_NAME.match(raw)
    if not match:
        return raw
    fqn = match.group(1)
    return fqn.split(".")[-1]


def find_annotation(
    annotations: List[Dict[str, Any]], name: str
) -> Optional[Dict[str, Any]]:
    """
    Busca una anotacion por nombre simple en la lista.
    Tambien busca por nombre cualificado (e.g. "Entity" matchea
    "javax.persistence.Entity").
    """
    for ann in annotations:
        if ann["name"] == name:
            return ann
    return None


# ============================================================
# ARGUMENTOS DE ANOTACIONES
# ============================================================

def annotation_argument(
    annotation: Optional[Dict[str, Any]], argument: str
) -> Optional[str]:
    """
    Extrae el valor de un argumento con nombre de una anotacion.

    Ejemplos:
        @Table(name = "CLIENTE")  -> argument="name" -> "CLIENTE"
        @Column(length = 100)     -> argument="length" -> "100"
    """
    if not annotation:
        return None

    raw = annotation["raw"]

    # Buscar argumento con nombre: argument = "valor"
    pattern = rf"\b{re.escape(argument)}\s*=\s*[\"']([^\"']+)[\"']"
    match = re.search(pattern, raw)
    if match:
        return match.group(1)

    # Buscar argumento numerico: argument = 100
    pattern_num = rf"\b{re.escape(argument)}\s*=\s*(\d+)"
    match_num = re.search(pattern_num, raw)
    if match_num:
        return match_num.group(1)

    # Para @Table("CLIENTE") sin nombre de argumento
    if argument == "name":
        match = RE_POSITIONAL_STRING.search(raw)
        if match:
            return match.group(1)

    return None


def annotation_boolean_argument(
    annotation: Optional[Dict[str, Any]], argument: str
) -> Optional[bool]:
    """
    Extrae un valor booleano de un argumento de anotacion.

    Ejemplo: @Column(nullable = false) -> False
    """
    if not annotation:
        return None

    raw = annotation["raw"]
    pattern = rf"\b{re.escape(argument)}\s*=\s*(true|false)"
    match = re.search(pattern, raw, re.IGNORECASE)

    if match:
        return match.group(1).lower() == "true"

    return None


# ============================================================
# TIPOS JAVA
# ============================================================

# Tipos de nodo AST que representan tipos Java.
JAVA_TYPE_NODES = frozenset({
    "type_identifier",
    "integral_type",
    "floating_point_type",
    "boolean_type",
    "void_type",
    "generic_type",
    "array_type",
    "scoped_type_identifier",
})


def extract_type(node: Node, source: bytes) -> Optional[str]:
    """
    Extrae el tipo de una declaracion de campo o variable.
    """
    for child in node.children:
        if child.type in JAVA_TYPE_NODES:
            return node_text(child, source)
    return None


def extract_simple_type(node: Node, source: bytes) -> Optional[str]:
    """
    Extrae el tipo simple (sin generics) de una declaracion.
    Para List<Pedido> devuelve "List".
    """
    for child in node.children:
        if child.type in JAVA_TYPE_NODES:
            raw = node_text(child, source)
            # Quitar generic: List<Pedido> -> List
            idx = raw.find("<")
            if idx > 0:
                return raw[:idx].strip()
            return raw
    return None


# ============================================================
# RESOLUCION DE GENERICS
# ============================================================

def extract_generic_inner_type(type_text: str) -> Optional[str]:
    """
    Extrae el tipo interior de un generic.

    Ejemplos:
        List<Pedido>        -> "Pedido"
        Set<Direccion>      -> "Direccion"
        Collection<Linea>   -> "Linea"
        Map<String, Object> -> "String" (primer tipo)
        Pedido              -> None
    """
    match = re.search(r"<([^<>]+)>", type_text)
    if not match:
        return None

    inner = match.group(1).strip()

    # Si hay coma, tomar el primer tipo (el valor del Map)
    if "," in inner:
        inner = inner.split(",")[0].strip()

    # Si es un generic anidado, extraer el nombre simple
    if "<" in inner:
        inner = extract_generic_inner_type(inner) or inner

    return inner


# ============================================================
# DIRECTORIOS IGNORADOS
# ============================================================

def should_ignore_path(path: Path) -> bool:
    """Determina si una ruta debe ser ignorada por el scanner."""
    return any(part in IGNORED_DIRS for part in path.parts)
