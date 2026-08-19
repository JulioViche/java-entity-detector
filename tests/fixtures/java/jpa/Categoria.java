package com.ejemplo.model;

import javax.persistence.*;

@Entity
@Table(name = "CATEGORIAS")
public class Categoria {

    @Id
    @Column(name = "ID_CATEGORIA")
    private Long id;

    @Column(name = "NOMBRE", length = 50)
    private String nombre;
}
