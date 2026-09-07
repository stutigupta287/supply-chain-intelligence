package com.supply_chain_intelligence.controller;

import com.supply_chain_intelligence.service.DataQualityService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/data-quality")
public class DataQualityController {
    private final DataQualityService dataQualityService;

    public DataQualityController(DataQualityService dataQualityService) {
        this.dataQualityService = dataQualityService;
    }

    @GetMapping("/report")
    public ResponseEntity<Map<String, Object>> getDataQualityReport() {
        Map<String, Object> report = dataQualityService.getDataQualityReport();
        return ResponseEntity.ok(report);
    }
}
