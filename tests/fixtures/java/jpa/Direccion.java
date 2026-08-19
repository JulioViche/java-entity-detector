package com.ejemplo.model;

import javax.persistence.*;

@Embeddable
public class Direccion {

    @Column(name = "CALLE", length = 200)
    private String calle;

    @Column(name = "CIUDAD", length = 100)
    private String ciudad;

    @Column(name = "CODIGO_POSTAL", length = 10)
    private String codigoPostal;

    @Column(name = "PAIS", length = 50)
    private String pais;
}
