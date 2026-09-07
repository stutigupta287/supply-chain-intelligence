package com.supply_chain_intelligence.service;

import com.supply_chain_intelligence.dto.RouteStatsResponse;
import com.supply_chain_intelligence.model.Shipment;
import com.supply_chain_intelligence.repository.ShipmentRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("RouteStatsService Unit Tests")
class RouteStatsServiceTest {

    @Mock
    private ShipmentRepository shipmentRepository;

    @InjectMocks
    private RouteStatsService routeStatsService;

    private List<Shipment> testShipments;

    @BeforeEach
    void setUp() {
        testShipments = new ArrayList<>();

        // Shipment 1 - On time
        Shipment s1 = new Shipment();
        s1.setShipmentId("SHP-001");
        s1.setOriginPort("SHANGHAI");
        s1.setDestinationPort("ROTTERDAM");
        s1.setActualDelayHours(10.0);
        s1.setOnTimeFlag(true);
        s1.setTransitDaysPlanned(20.0);
        s1.setTransitDaysActual(21.0);
        testShipments.add(s1);

        // Shipment 2 - Delayed
        Shipment s2 = new Shipment();
        s2.setShipmentId("SHP-002");
        s2.setOriginPort("SHANGHAI");
        s2.setDestinationPort("ROTTERDAM");
        s2.setActualDelayHours(30.0);
        s2.setOnTimeFlag(false);
        s2.setTransitDaysPlanned(20.0);
        s2.setTransitDaysActual(22.0);
        testShipments.add(s2);

        // Shipment 3 - On time
        Shipment s3 = new Shipment();
        s3.setShipmentId("SHP-003");
        s3.setOriginPort("SHANGHAI");
        s3.setDestinationPort("ROTTERDAM");
        s3.setActualDelayHours(5.0);
        s3.setOnTimeFlag(true);
        s3.setTransitDaysPlanned(19.0);
        s3.setTransitDaysActual(20.0);
        testShipments.add(s3);
    }

    @Test
    @DisplayName("Should calculate correct route statistics")
    void testGetRouteStats_Success() {
        // Arrange
        when(shipmentRepository.findByOriginPortAndDestinationPort("SHANGHAI", "ROTTERDAM"))
                .thenReturn(testShipments);

        // Act
        RouteStatsResponse result = routeStatsService.getRouteStats("SHANGHAI", "ROTTERDAM");

        // Assert
        assertNotNull(result);
        assertEquals("SHANGHAI", result.getOrigin());
        assertEquals("ROTTERDAM", result.getDestination());
        assertEquals("SHANGHAI → ROTTERDAM", result.getRouteKey());
        assertEquals(3L, result.getShipmentCount());
        
        // Average delay: (10 + 30 + 5) / 3 = 15.0
        assertEquals(15.0, result.getAverageDelayHours(), 0.01);
        
        // On-time rate: 2 out of 3 = 66.67%
        assertEquals(66.67, result.getOnTimeRate(), 0.1);
        
        // Average planned transit: (20 + 20 + 19) / 3 = 19.67
        assertEquals(19.67, result.getAverageTransitDaysPlanned(), 0.01);
        
        // Average actual transit: (21 + 22 + 20) / 3 = 21.0
        assertEquals(21.0, result.getAverageTransitDaysActual(), 0.01);

        verify(shipmentRepository, times(1))
                .findByOriginPortAndDestinationPort("SHANGHAI", "ROTTERDAM");
    }

    @Test
    @DisplayName("Should return empty stats when no shipments found")
    void testGetRouteStats_NoShipments() {
        // Arrange
        when(shipmentRepository.findByOriginPortAndDestinationPort("UNKNOWN", "UNKNOWN"))
                .thenReturn(new ArrayList<>());

        // Act
        RouteStatsResponse result = routeStatsService.getRouteStats("UNKNOWN", "UNKNOWN");

        // Assert
        assertNotNull(result);
        assertEquals("UNKNOWN", result.getOrigin());
        assertEquals("UNKNOWN", result.getDestination());
        assertEquals(0L, result.getShipmentCount());
        assertNull(result.getAverageDelayHours());
        assertNull(result.getOnTimeRate());
        assertNull(result.getAverageTransitDaysPlanned());
        assertNull(result.getAverageTransitDaysActual());

        verify(shipmentRepository, times(1))
                .findByOriginPortAndDestinationPort("UNKNOWN", "UNKNOWN");
    }

    @Test
    @DisplayName("Should handle shipments with null values")
    void testGetRouteStats_WithNullValues() {
        // Arrange
        List<Shipment> shipmentsWithNulls = new ArrayList<>();
        Shipment s1 = new Shipment();
        s1.setShipmentId("SHP-004");
        s1.setOriginPort("SHANGHAI");
        s1.setDestinationPort("ROTTERDAM");
        s1.setActualDelayHours(null);  // null delay
        s1.setOnTimeFlag(null);  // null flag
        s1.setTransitDaysPlanned(null);
        s1.setTransitDaysActual(null);
        shipmentsWithNulls.add(s1);

        when(shipmentRepository.findByOriginPortAndDestinationPort("SHANGHAI", "ROTTERDAM"))
                .thenReturn(shipmentsWithNulls);

        // Act
        RouteStatsResponse result = routeStatsService.getRouteStats("SHANGHAI", "ROTTERDAM");

        // Assert
        assertNotNull(result);
        assertEquals(1L, result.getShipmentCount());
        assertEquals(0.0, result.getAverageDelayHours());  // No valid delays
        assertEquals(0.0, result.getOnTimeRate());  // No on-time flags
        assertEquals(0.0, result.getAverageTransitDaysPlanned());
        assertEquals(0.0, result.getAverageTransitDaysActual());
    }
}
