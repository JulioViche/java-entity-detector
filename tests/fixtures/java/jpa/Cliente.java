package com.ejemplo.model;

import javax.persistence.*;

@Entity
@Table(name = "CLIENTES")
public class Cliente {

    @Id
    @Column(name = "ID_CLIENTE")
    private Long id;

    @Column(name = "NOMBRE", length = 100, nullable = false)
    private String nombre;

    @Column(name = "APELLIDO", length = 100)
    private String apellido;

    @Column(name = "EMAIL", unique = true)
    private String email;

    @OneToMany(mappedBy = "cliente", cascade = CascadeType.ALL)
    private java.util.List<Pedido> pedidos;

    @ManyToOne
    @JoinColumn(name = "ID_ZONA")
    private Zona zona;
}
