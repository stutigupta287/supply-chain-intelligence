package com.supply_chain_intelligence.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class DelayPredictionResponse {
    private String prediction;        // "ON_TIME" or "DELAYED"
    private Double probability;       // Probability of predicted class
    
    @JsonProperty("delay_risk_score")
    private Double delayRiskScore;    // Probability of delay
    
    private String confidence;        // "LOW", "MEDIUM", or "HIGH"
    
    @JsonProperty("model_version")
    private String modelVersion;      // Model version used
}
