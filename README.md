# java-entity-detector

Herramienta automatizada para detectar entidades de base de datos en repositorios Java legacy. Analiza anotaciones JPA y mapeos Hibernate XML sin compilar ni ejecutar el codigo fuente.

## Que hace

Recorre repositorios Java y extrae información de persistencia para generar diccionarios de datos y diagramas entidad-relacion (ER):

| Que detecta | Mecanismo |
|-------------|-----------|
| `@Entity`, `@Table` | Entidades JPA y sus tablas |
| `@Embeddable` | Tipos embebidos (composicion) |
| `@MappedSuperclass` | Superclases mapeadas (herencia) |
| `@Column` | Nombre de columna, tipo, restricciones |
| `@Id`, `@EmbeddedId` | Claves primarias |
| `@JoinColumn`, `@JoinTable` | Claves foraneas y tablas intermedias |
| `@OneToOne`, `@OneToMany`, `@ManyToOne`, `@ManyToMany` | Relaciones con cardinalidad |
| `@Inheritance` | Estrategia de herencia |
| `<class>`, `<id>`, `<property>` | Mapeos Hibernate XML |
| `<many-to-one>`, `<one-to-many>`, `<many-to-many>` | Relaciones en Hibernate XML |

## Requisitos

- Python 3.10+
- No requiere compilar ni instalar nada en los repositorios analizados

## Instalacion

```bash
git clone https://github.com/tu-usuario/java-entity-detector.git
cd java-entity-detector
pip install -r requirements.txt
```

## Uso

### Basico

```bash
python detect_entities.py -r ./repositories
```

Esto escanea todos los subdirectorios de `./repositories` e imprime el JSON resultante en pantalla.

### Guardar en archivo

```bash
python detect_entities.py -r ./repositories -o resultado.json
```

### Multiples repositorios

```bash
python detect_entities.py -r ./repo-a ./repo-b -o resultado.json
```

### JSON compacto

```bash
python detect_entities.py -r ./repositories --compact -o resultado.json
```

## Estructura de repositorios esperada

```
/repositories/
  ├── repo-legacy-1/
  │   └── src/main/java/com/empresa/model/
  │       ├── Cliente.java          (con @Entity)
  │       ├── Pedido.java           (con @Entity)
  │       └── mappings.hbm.xml      (Hibernate XML)
  ├── repo-legacy-2/
  │   └── src/main/java/...
  └── repo-spring/
      └── src/main/java/...
```

Cada subdirectorio dentro de `repositories/` se trata como un repositorio independiente. Se ignoran automaticamente los directorios: `.git`, `target`, `build`, `out`, `node_modules`, `bin`, `.gradle`, `.idea`, `.settings`.

## Formato de salida JSON

```json
{
  "version": "1.0",
  "scan_date": "2026-08-18T12:00:00+00:00",
  "repositories": ["repo-legacy-1", "repo-legacy-2"],
  "summary": {
    "entities": 15,
    "embeddables": 3,
    "mapped_superclasses": 2
  },
  "entities": [
    {
      "name": "Cliente",
      "table": "CLIENTES",
      "type": "JPA_ENTITY",
      "fully_qualified_name": "com.empresa.model.Cliente",
      "package": "com.empresa.model",
      "fields": [
        {
          "name": "id",
          "type": "Long",
          "column": "ID_CLIENTE",
          "primary_key": true,
          "nullable": false,
          "source": {
            "repository": "repo-legacy-1",
            "file": "src/main/java/com/empresa/model/Cliente.java",
            "line": 12
          }
        }
      ],
      "relations": [
        {
          "field": "pedidos",
          "target_type": "Pedido",
          "target_entity": "Pedido",
          "cardinality": "1:N",
          "mapped_by": "cliente",
          "source": {
            "repository": "repo-legacy-1",
            "file": "src/main/java/com/empresa/model/Cliente.java",
            "line": 25
          }
        }
      ],
      "annotations": ["@Entity", "@Table(name = \"CLIENTES\")"],
      "inheritance": null,
      "source": {
        "repository": "repo-legacy-1",
        "file": "src/main/java/com/empresa/model/Cliente.java",
        "line": 8
      },
      "evidence": {
        "kind": "jpa_annotation",
        "entity": "@Entity",
        "table": "@Table(name = \"CLIENTES\")"
      }
    }
  ],
  "embeddables": [
    {
      "name": "Direccion",
      "fully_qualified_name": "com.empresa.model.Direccion",
      "package": "com.empresa.model",
      "fields": [...]
    }
  ],
  "mapped_superclasses": [
    {
      "name": "BaseEntity",
      "fully_qualified_name": "com.empresa.model.BaseEntity",
      "fields": [...]
    }
  ]
}
```

### Campos de la entidad

| Campo | Descripcion |
|-------|-------------|
| `name` | Nombre simple de la clase Java |
| `table` | Nombre de la tabla en BD (de `@Table` o `<class table=...>`) |
| `type` | Tipo de mapeo: `JPA_ENTITY` o `HIBERNATE_XML` |
| `fully_qualified_name` | Nombre calificado completo (paquete + clase) |
| `package` | Paquete Java |
| `fields` | Lista de campos/columnas |
| `relations` | Relaciones con otras entidades |
| `inheritance` | Estrategia de herencia: `SINGLE_TABLE`, `JOINED`, `TABLE_PER_CLASS` |
| `evidence` | Evidencia cruda utilizada para la deteccion |

### Campos de un field

| Campo | Descripcion |
|-------|-------------|
| `name` | Nombre del atributo Java |
| `type` | Tipo Java del atributo |
| `column` | Nombre de la columna en BD |
| `primary_key` | `true` si es clave primaria |
| `nullable` | `true`/`false` si se especifico en `@Column` |
| `length` | Longitud maxima (si se especifico) |
| `precision`, `scale` | Para campos numericos |
| `unique` | Si tiene restriccion de unicidad |

### Campos de una relacion

| Campo | Descripcion |
|-------|-------------|
| `field` | Nombre del atributo Java |
| `target_type` | Tipo Java del destino (puede ser generic: `List<Pedido>`) |
| `target_entity` | Nombre simple de la entidad destino |
| `cardinality` | `1:1`, `1:N`, `N:1`, `N:M` |
| `join_column` | Columna FK (de `@JoinColumn`) |
| `join_table` | Tabla intermedia (de `@JoinTable`) |
| `mapped_by` | Campo inverso (de `mappedBy`) |

## Ejecutar tests

```bash
python tests/test_parsers.py
```

Los tests usan archivos fixture en `tests/fixtures/` que simulan diferentes escenarios de entidades JPA y Hibernate XML.

## Arquitectura

```
detect_entities.py              # Punto de entrada CLI
src/entity_detector/
  ├── models.py                 # Modelo de datos (dataclasses)
  ├── utils.py                  # Utilidades: AST, anotaciones, regex
  ├── java_jpa_parser.py        # Parser JPA (Tree-sitter)
  ├── hibernate_xml_parser.py   # Parser Hibernate XML
  └── scanner.py                # Scanner de repositorios
tests/
  ├── test_parsers.py           # Tests unitarios
  └── fixtures/                 # Archivos Java y XML de prueba
```

### Flujo de ejecucion

```mermaid
flowchart TD
    subgraph CLI["CLI - detect_entities.py"]
        A1["python detect_entities.py -r ./repos -o out.json"] --> A2["build_parser: parsea argumentos"]
        A2 --> A3{"Directorios existen?"}
        A3 -->|"No"| A4["ERROR: sys.exit 1"]
        A3 -->|"Si"| A5["Para cada repo_root en args.repos"]
    end

    subgraph SCAN["Scanner - scanner.py"]
        A5 --> B1["scan_all: busca subdirectorios como repos"]
        B1 --> B2["Para cada repo, llama scan_repository"]
        B2 --> B3["rglob *.java"]
        B2 --> B4["rglob *.hbm.xml"]
    end

    subgraph JAVA["Java JPA Parser - java_jpa_parser.py"]
        B3 --> C1["parse_java_file: lee y parsea con Tree-sitter"]
        C1 --> C2["Extrae package e imports"]
        C2 --> C3["Busca class_declaration en AST"]
        C3 --> C4{"Clasifica anotaciones"}
        C4 -->|"@Entity"| C5["build entity"]
        C4 -->|"@Embeddable"| C6["build embeddable"]
        C4 -->|"@MappedSuperclass"| C7["build mapped superclass"]
        C4 -->|"Otra clase"| C8["Ignora"]
        C5 --> C9["Extrae campos con extract_fields"]
        C5 --> C10["Extrae relaciones con extract_relations"]
        C5 --> C11["Extrae herencia con extract_inheritance"]
        C9 --> C12["Para cada field_declaration"]
        C12 --> C13["get_annotations: extrae @Column, @Id"]
        C13 --> C14["annotation_argument: extrae nombre, length, nullable"]
        C10 --> C15["Para cada field_declaration"]
        C15 --> C16["Busca @OneToOne/@OneToMany/@ManyToOne/@ManyToMany"]
        C16 --> C17["resolve_relation_target: extrae tipo destino"]
        C17 --> C18["Extrae @JoinColumn/@JoinTable"]
    end

    subgraph HIBERNATE["Hibernate XML Parser - hibernate_xml_parser.py"]
        B4 --> D1["parse_hibernate_xml: parsea con ElementTree"]
        D1 --> D2["Busca elementos class/subclass"]
        D2 --> D3["Para cada class: parse_hibernate_class"]
        D3 --> D4["Extrae name y table"]
        D4 --> D5{"Elementos hijos"}
        D5 -->|"id"| D6["parse_id_element: campo PK"]
        D5 -->|"property"| D7["parse_property_element: campo normal"]
        D5 -->|"many-to-one"| D8["parse_many_to_one: relacion N:1"]
        D5 -->|"one-to-many"| D9["parse_one_to_many: relacion 1:N"]
        D5 -->|"many-to-many"| D10["parse_many_to_many: relacion N:M"]
        D5 -->|"one-to-one"| D11["parse_one_to_one: relacion 1:1"]
        D5 -->|"join"| D12["Parsea campos adicionales de join"]
    end

    subgraph MODELS["Models - models.py"]
        C18 --> E1["Entity"]
        C6 --> E2["Embeddable"]
        C7 --> E3["MappedSuperclass"]
        C14 --> E4["Field"]
        C18 --> E5["Relation"]
        D3 --> E1
        D6 --> E4
        D7 --> E4
        D8 --> E5
        D9 --> E5
        D10 --> E5
        D11 --> E5
    end

    subgraph UTILS["Utils - utils.py"]
        C1 --> F1["PARSER: Tree-sitter global"]
        C1 --> F2["read_bytes: lee archivo"]
        C13 --> F3["get_annotations: extrae del AST"]
        F3 --> F4["extract_annotation_name: limpia FQN"]
        C14 --> F5["annotation_argument: regex para valores"]
        C17 --> F6["extract_generic_inner_type: resuelve generics"]
        C9 --> F7["extract_type: tipo del campo"]
    end

    subgraph OUTPUT["Salida - detect_entities.py"]
        E1 --> G1["Acumula en listas"]
        E2 --> G1
        E3 --> G1
        G1 --> G2["Construye dict output con summary"]
        G2 --> G3{"args.output?"}
        G3 -->|"Si"| G4["write_text: escribe JSON a archivo"]
        G3 -->|"No"| G5["print: imprime en stdout"]
        G4 --> G6["Resumen: X entidades, Y embeddables, Z mapped"]
        G5 --> G6
    end

    subgraph DATA["Estructuras de Datos"]
        E1 --> H1["Entity: name, table, type, FQN, fields, relations"]
        E4 --> H2["Field: name, type, column, PK, nullable, length"]
        E5 --> H3["Relation: field, target, cardinality, join_column"]
        E2 --> H4["Embeddable: name, FQN, fields"]
        E3 --> H5["MappedSuperclass: name, FQN, fields"]
    end

    style CLI fill:#e1f5fe,stroke:#0288d1
    style SCAN fill:#f3e5f5,stroke:#7b1fa2
    style JAVA fill:#e8f5e9,stroke:#388e3c
    style HIBERNATE fill:#fff3e0,stroke:#f57c00
    style MODELS fill:#fce4ec,stroke:#c62828
    style UTILS fill:#f5f5f5,stroke:#616161
    style OUTPUT fill:#e0f7fa,stroke:#00838f
    style DATA fill:#fff9c4,stroke:#f9a825
```

### Por que Tree-sitter?

- Analiza sin compilar: no necesita JDK, Maven ni Gradle
- Tolerante a errores de sintaxis: no falla si el codigo tiene problemas
- AST preciso: extrae anotaciones, tipos y generic correctamente
- Rápido: procesa miles de archivos por segundo

## Limitaciones conocidas

- No resuelve anotaciones personalizadas fuera de JPA/Hibernate
- No analiza clases que usan XML persistence.xml (solo .hbm.xml)
- No detecta queries JPQL ni SQL nativo
- No maneja anotaciones dinamicas (generadas por frameworks)
- Los tipos resueltos son strings, no tipos completos de Java

## Roadmap

- [ ] Soporte para `persistence.xml`
- [ ] Soporte para MyBatis mappers
- [ ] Analisis de queries SQL nativas
- [ ] Exportar a Mermaid/PlantUML para diagramas ER
- [ ] Exportar a CSV para diccionarios de datos
- [ ] Soporte para `@Lob`, `@Temporal`, `@Enumerated`
- [ ] Deteccion de indexes y unique constraints
