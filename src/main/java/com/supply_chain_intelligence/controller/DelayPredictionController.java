package com.supply_chain_intelligence.controller;

import com.supply_chain_intelligence.dto.DelayPredictionRequest;
import com.supply_chain_intelligence.dto.DelayPredictionResponse;
import com.supply_chain_intelligence.service.DelayPredictionService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/predict-delay")
public class DelayPredictionController {

    private final DelayPredictionService delayPredictionService;

    public DelayPredictionController(DelayPredictionService delayPredictionService) {
        this.delayPredictionService = delayPredictionService;
    }

    /**
     * Predict delay risk for an existing shipment by ID
     */
    @PostMapping("/shipment/{id}")
    public ResponseEntity<DelayPredictionResponse> predictByShipmentId(@PathVariable String id) {
        DelayPredictionResponse response = delayPredictionService.predictDelayForShipment(id);
        return ResponseEntity.ok(response);
    }

    /**
     * Predict delay risk from booking details
     */
    @PostMapping
    public ResponseEntity<DelayPredictionResponse> predictFromFeatures(@RequestBody DelayPredictionRequest request) {
        DelayPredictionResponse response = delayPredictionService.predictDelayFromFeatures(request);
        return ResponseEntity.ok(response);
    }

    /**
     * Check ML service health
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> checkMlHealth() {
        boolean healthy = delayPredictionService.isMlServiceHealthy();
        
        Map<String, Object> response = new HashMap<>();
        response.put("ml_service_status", healthy ? "UP" : "DOWN");
        response.put("endpoint_available", healthy);
        
        return ResponseEntity.ok(response);
    }
}
