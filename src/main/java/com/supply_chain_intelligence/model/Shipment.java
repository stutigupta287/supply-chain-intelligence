package com.supply_chain_intelligence.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.time.LocalDateTime;

@Entity
@Table(name = "shipments")
@Getter
@Setter
@NoArgsConstructor
public class Shipment {

        @Id
        @Column(name = "shipment_id")
        private String shipmentId;

        @Column(name = "customer_id")
        private String customerId;

        @Column(name = "origin_port")
        private String originPort;

        @Column(name = "destination_port")
        private String destinationPort;

        @Column(name = "vessel_id")
        private String vesselId;

        @Column(name = "booking_date")
        private LocalDateTime bookingDate;

        @Column(name = "planned_departure")
        private LocalDateTime plannedDeparture;

        @Column(name = "actual_departure")
        private LocalDateTime actualDeparture;

        @Column(name = "planned_arrival")
        private LocalDateTime plannedArrival;

        @Column(name = "actual_arrival")
        private LocalDateTime actualArrival;

        @Column(name = "container_count")
        private Integer containerCount;

        @Column(name = "cargo_type")
        private String cargoType;

        @Column(name = "weight_tons")
        private Double weightTons;

        @Column(name = "status")
        private String status;

        @Column(name = "actual_delay_hours")
        private Double actualDelayHours;

        @Column(name = "on_time_flag")
        private Boolean onTimeFlag;

        @Column(name = "route_key")
        private String routeKey;

        @Column(name = "transit_days_planned")
        private Double transitDaysPlanned;

        @Column(name = "transit_days_actual")
        private Double transitDaysActual;
}