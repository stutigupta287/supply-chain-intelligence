package com.supply_chain_intelligence.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class RouteStatsResponse {
    private String origin;
    private String destination;
    private String routeKey;
    private Long shipmentCount;
    private Double averageDelayHours;
    private Double onTimeRate;
    private Double averageTransitDaysPlanned;
    private Double averageTransitDaysActual;
}
