# utils.py

Utilidades compartidas para los parsers. Funciones para lectura de archivos, manipulacion de AST, extraccion de anotaciones y expresiones regulares.

## Configuracion Tree-sitter

```mermaid
flowchart LR
    A["tree_sitter_java.language()"] --> B["Language()"]
    B --> C["JAVA_LANGUAGE"]
    C --> D["Parser(JAVA_LANGUAGE)"]
    D --> E["PARSER: global"]
```

- `JAVA_LANGUAGE` - Lenguaje Java configurado para Tree-sitter
- `PARSER` - Parser global reutilizado en todos los archivos `.java`

## Directorios ignorados

```python
IGNORED_DIRS = {
    ".git", "target", "build", "out", "node_modules",
    "bin", "test-output", ".gradle", ".idea", ".settings",
}
```

## Funciones de lectura

### read_text(path)

Lee un archivo de texto intentando multiples codificaciones:
1. Intenta `utf-8`
2. Si falla, intenta `latin-1`
3. Si falla, intenta `cp1252`
4. Como fallback, usa `utf-8` con `errors="replace"`

### read_bytes(path)

Convierte texto a bytes UTF-8 (requerido por Tree-sitter).

### should_ignore_path(path)

Verifica si alguna parte de la ruta esta en `IGNORED_DIRS`.

## Funciones de nodos AST

### node_text(node, source)

Extrae el texto crudo de un nodo del AST:
```python
source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
```

### line_number(node)

Retorna el numero de linea (1-based) de un nodo:
```python
node.start_point[0] + 1
```

### children_by_type(node, node_type)

Devuelve los hijos directos de un nodo que tengan el tipo indicado.

### find_child_by_type(node, node_type)

Devuelve el primer hijo directo con el tipo indicado, o `None`.

### find_descendant_by_type(node, node_type)

Busca recursivamente el primer descendiente con el tipo indicado.

## Funciones de repositorio

### repository_name(path, root)

Obtiene el nombre del repositorio a partir de la ruta:
1. Intenta hacer relativa a `root`
2. Si no puede, busca hacia arriba buscando `.git`
3. Como fallback, usa el primer componente de la ruta

## Funciones de anotaciones

### get_annotations(node, source)

Extrae las anotaciones de un nodo (campo, clase, metodo):
1. Busca el nodo `modifiers`
2. Para cada hijo, busca `marker_annotation` o `annotation`
3. Retorna lista de diccionarios: `{name, raw, line, node}`

### extract_annotation_name(raw)

Extrae el nombre simple de una anotacion:
```
@javax.persistence.Entity -> "Entity"
@Table(...)               -> "Table"
```

### find_annotation(annotations, name)

Busca una anotacion por nombre simple en la lista.

## Funciones de argumentos

### annotation_argument(annotation, argument)

Extrae el valor de un argumento con nombre:
```
@Table(name = "CLIENTE")  -> argument="name" -> "CLIENTE"
@Column(length = 100)     -> argument="length" -> "100"
```

Busca:
1. `argument = "valor"` (string)
2. `argument = 123` (numerico)
3. `@Table("CLIENTE")` (posicional, solo para "name")

### annotation_boolean_argument(annotation, argument)

Extrae un valor booleano:
```
@Column(nullable = false) -> False
```

## Funciones de tipos

### JAVA_TYPE_NODES

Conjunto de tipos de nodo AST que representan tipos Java:
- `type_identifier`, `integral_type`, `floating_point_type`
- `boolean_type`, `void_type`, `generic_type`
- `array_type`, `scoped_type_identifier`

### extract_type(node, source)

Extrae el tipo de una declaracion de campo o variable.

### extract_simple_type(node, source)

Extrae el tipo sin generics:
```
List<Pedido> -> "List"
```

## Funciones de generics

### extract_generic_inner_type(type_text)

Extrae el tipo interior de un generic:
```
List<Pedido>        -> "Pedido"
Set<Direccion>      -> "Direccion"
Collection<Linea>   -> "Linea"
Map<String, Object> -> "String"
Pedido              -> None
```

Maneja generics anidados recursivamente.

## Expresiones regulares

```python
RE_ANNOTATION_NAME = r"@\\s*([\\w.$]+)"
RE_STRING_ARG = r'(\\w+)\\s*=\\s*["\\']([^"\\']+)["\\']'
RE_POSITIONAL_STRING = r'@\\w+\\s*\\(\\s*["\\']([^"\\']+)["\\']\\s*\\)'
```

## Dependencias

- `tree_sitter` - Parsing de AST (Language, Node, Parser)
- `tree_sitter_java` - Lenguaje Java
- `re` - Expresiones regulares
- `pathlib.Path` - Manejo de rutas
