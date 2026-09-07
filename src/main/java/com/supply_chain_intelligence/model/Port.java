package com.supply_chain_intelligence.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "ports")
@Getter
@Setter
@NoArgsConstructor
public class Port {

    @Id
    @Column(name = "port_code")
    private String portCode;

    @Column(name = "port_name", nullable = false)
    private String portName;

    @Column(name = "country")
    private String country;

    @Column(name = "region", nullable = false)
    private String region;

    @Column(name = "timezone", nullable = false)
    private String timezone;

    @Column(name = "avg_congestion_score", nullable = false)
    private Double avgCongestionScore;
}
