# scanner.py

Escanea repositorios Java buscando archivos .java y .hbm.xml.

## Flujo detallado

```mermaid
flowchart TD
    A["scan_all(repositories_root)"] --> B{"Directorio existe?"}
    B -->|"No"| C["raise SystemExit"]
    B -->|"Si"| D["Busca subdirectorios como repos"]
    D --> E{"Hay repos?"}
    E -->|"No"| F["Imprime warning"]
    E -->|"Si"| G["Crea ScanResult vacio"]
    G --> H["Para cada repo ordenado"]
    H --> I["scan_repository(repo)"]
    I --> J["Obtiene repo.name"]
    J --> K["rglob *.java"]
    K --> L["Para cada .java"]
    L --> M{"should_ignore_path?"}
    M -->|"Si"| N["Skip"]
    M -->|"No"| O["parse_java_file(java_file)"]
    O --> P{"Entregó resultados?"}
    P -->|"Si"| Q["Incrementa java_count"]
    P -->|"No"| R["Continua"]
    O -->|"Excepcion"| S["Print warning"]
    Q --> T["Agrega a listas"]
    R --> T
    S --> T
    T --> U["rglob *.hbm.xml"]
    U --> V["Para cada .hbm.xml"]
    V --> W{"should_ignore_path?"}
    W -->|"Si"| X["Skip"]
    W -->|"No"| Y["parse_hibernate_xml(xml_file)"]
    Y --> Z{"Entregó resultados?"}
    Z -->|"Si"| AA["Incrementa xml_count"]
    Z -->|"No"| AB["Continua"]
    Y -->|"Excepcion"| AC["Print warning"]
    AA --> AD["Agrega a entidades"]
    AB --> AD
    AC --> AD
    AD --> AE["Imprime resumen del repo"]
    AE --> AF["Retorna: entities, embeddables, mapped"]

    style A fill:#f3e5f5,stroke:#7b1fa2
    style I fill:#e8f5e9,stroke:#388e3c
    style Y fill:#fff3e0,stroke:#f57c00
```

## Funciones

### scan_all(repositories_root)

Funcion principal que:
1. Valida que el directorio exista
2. Busca subdirectorios que no empiecen con `.`
3. Para cada subdirectorio, llama a `scan_repository()`
4. Acumula resultados en un `ScanResult`
5. Retorna el `ScanResult` completo

### scan_repository(repository_path)

Escanea un repositorio individual:
1. Busca todos los `*.java` recursivamente
2. Para cada `.java`, verifica que no este en directorios ignorados
3. Llama a `parse_java_file()` y acumula resultados
4. Busca todos los `*.hbm.xml` recursivamente
5. Para cada `.hbm.xml`, verifica que no este en directorios ignorados
6. Llama a `parse_hibernate_xml()` y acumula resultados
7. Retorna tupla `(entities, embeddables, mapped_superclasses)`

## Directorios ignorados

Definidos en `utils.py`:
- `.git`, `target`, `build`, `out`, `node_modules`
- `bin`, `test-output`, `.gradle`, `.idea`, `.settings`

## Dependencias

- `java_jpa_parser.parse_java_file` - Parser JPA
- `hibernate_xml_parser.parse_hibernate_xml` - Parser Hibernate XML
- `models.ScanResult` - Modelo de datos
- `utils.should_ignore_path` - Verificacion de directorios
