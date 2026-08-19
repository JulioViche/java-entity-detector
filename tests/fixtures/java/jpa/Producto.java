package com.ejemplo.model;

import javax.persistence.*;

@Entity
@Table(name = "PRODUCTOS")
public class Producto {

    @Id
    @Column(name = "ID_PRODUCTO")
    private Long id;

    @Column(name = "NOMBRE", length = 200, nullable = false)
    private String nombre;

    @Column(name = "PRECIO")
    private java.math.BigDecimal precio;

    @OneToOne
    @JoinColumn(name = "ID_CATEGORIA")
    private Categoria categoria;
}
