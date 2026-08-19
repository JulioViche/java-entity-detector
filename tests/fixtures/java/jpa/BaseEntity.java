package com.ejemplo.model;

import javax.persistence.*;

@MappedSuperclass
public abstract class BaseEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "ID")
    private Long id;

    @Column(name = "FECHA_CREACION")
    private java.util.Date fechaCreacion;

    @Column(name = "FECHA_MODIFICACION")
    private java.util.Date fechaModificacion;
}
