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
@Table(name = "port_events")
@Getter
@Setter
@NoArgsConstructor
public class PortEvent {

    @Id
    @Column(name = "event_id")
    private String eventId;

    @Column(name = "event_timestamp", nullable = false)
    private LocalDateTime eventTimestamp;

    @Column(name = "port_code", nullable = false)
    private String portCode;

    @Column(name = "vessel_id", nullable = false)
    private String vesselId;

    @Column(name = "event_type", nullable = false)
    private String eventType;

    @Column(name = "delay_minutes", nullable = false)
    private Integer delayMinutes;

    @Column(name = "notes")
    private String notes;
}