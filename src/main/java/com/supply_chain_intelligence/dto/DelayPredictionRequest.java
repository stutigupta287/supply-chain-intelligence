package com.supply_chain_intelligence.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class DelayPredictionRequest {
    @JsonProperty("origin_port")
    private String originPort;
    
    @JsonProperty("destination_port")
    private String destinationPort;
    
    @JsonProperty("cargo_type")
    private String cargoType;
    
    @JsonProperty("weight_tons")
    private Double weightTons;
    
    @JsonProperty("container_count")
    private Integer containerCount;
    
    @JsonProperty("planned_transit_days")
    private Double plannedTransitDays;
    
    @JsonProperty("booking_lead_days")
    private Double bookingLeadDays;
    
    @JsonProperty("booking_month")
    private Integer bookingMonth;
    
    @JsonProperty("booking_day_of_week")
    private Integer bookingDayOfWeek;
    
    @JsonProperty("origin_congestion_score")
    private Double originCongestionScore;
    
    @JsonProperty("destination_congestion_score")
    private Double destinationCongestionScore;
}
