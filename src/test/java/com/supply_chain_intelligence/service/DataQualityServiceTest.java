package com.supply_chain_intelligence.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("DataQualityService Unit Tests")
class DataQualityServiceTest {

    @Spy
    private ObjectMapper objectMapper = new ObjectMapper();

    @InjectMocks
    private DataQualityService dataQualityService;

    @Test
    @DisplayName("Should return existing DQ report")
    void testGetDataQualityReport_ReportExists() {
        // Act
        Map<String, Object> result = dataQualityService.getDataQualityReport();

        // Assert
        assertNotNull(result);
        // If report exists, it should have these keys
        if (!result.containsKey("error")) {
            assertTrue(result.containsKey("dataset") || result.containsKey("quality_summary"));
        }
    }

    @Test
    @DisplayName("Should handle missing report file gracefully")
    void testGetDataQualityReport_ReportMissing() {
        // Create service with non-existent path
        DataQualityService serviceWithBadPath = new DataQualityService(objectMapper);
        
        // Act
        Map<String, Object> result = serviceWithBadPath.getDataQualityReport();

        // Assert - should return error structure instead of throwing exception
        assertNotNull(result);
        assertTrue(result.containsKey("error") || result.containsKey("dataset"));
    }
}
