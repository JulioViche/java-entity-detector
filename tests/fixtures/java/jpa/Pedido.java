package com.ejemplo.model;

import javax.persistence.*;

@Entity
@Table(name = "PEDIDOS")
public class Pedido {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "ID_PEDIDO")
    private Long id;

    @Column(name = "FECHA")
    private java.util.Date fecha;

    @Column(name = "MONTO", precision = 10, scale = 2)
    private java.math.BigDecimal monto;

    @ManyToOne
    @JoinColumn(name = "ID_CLIENTE", nullable = false)
    private Cliente cliente;

    @ManyToMany
    @JoinTable(
        name = "PEDIDO_PRODUCTOS",
        joinColumns = @JoinColumn(name = "ID_PEDIDO"),
        inverseJoinColumns = @JoinColumn(name = "ID_PRODUCTO")
    )
    private java.util.Set<Producto> productos;
}
