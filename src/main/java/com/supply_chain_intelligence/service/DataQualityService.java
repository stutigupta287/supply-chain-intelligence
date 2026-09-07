package com.supply_chain_intelligence.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

@Service
public class DataQualityService {
    private static final String DQ_REPORT_PATH = "reports/dq_report.json";
    private final ObjectMapper objectMapper;

    public DataQualityService(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> getDataQualityReport() {
        File reportFile = new File(DQ_REPORT_PATH);

        if (!reportFile.exists()) {
            Map<String, Object> emptyReport = new HashMap<>();
            emptyReport.put("error", "Data quality report not found");
            emptyReport.put("message", "Please run data quality checks first: python data-engineering/dq_check.py");
            return emptyReport;
        }

        try {
            return objectMapper.readValue(reportFile, Map.class);
        } catch (IOException e) {
            Map<String, Object> errorReport = new HashMap<>();
            errorReport.put("error", "Failed to read data quality report");
            errorReport.put("message", e.getMessage());
            return errorReport;
        }
    }
}
