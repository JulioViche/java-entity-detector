package com.ejemplo.model;

import javax.persistence.*;

@Entity
@Table(name = "ZONAS")
@Inheritance(strategy = InheritanceType.SINGLE_TABLE)
public class Zona {

    @Id
    @Column(name = "ID_ZONA")
    private Long id;

    @Column(name = "NOMBRE", length = 100)
    private String nombre;
}
