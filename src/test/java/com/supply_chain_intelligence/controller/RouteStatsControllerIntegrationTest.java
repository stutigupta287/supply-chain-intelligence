package com.supply_chain_intelligence.controller;

import com.supply_chain_intelligence.model.Shipment;
import com.supply_chain_intelligence.repository.ShipmentRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@Transactional
@DisplayName("Route Stats API Integration Tests")
class RouteStatsControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ShipmentRepository shipmentRepository;

    @BeforeEach
    void setUp() {
        shipmentRepository.deleteAll();

        // Create test shipments for SHANGHAI -> ROTTERDAM route
        for (int i = 1; i <= 3; i++) {
            Shipment s = new Shipment();
            s.setShipmentId("SHP-ROUTE-00" + i);
            s.setCustomerId("CUST-00" + i);
            s.setOriginPort("SHANGHAI");
            s.setDestinationPort("ROTTERDAM");
            s.setVesselId("VESSEL-00" + i);
            s.setBookingDate(LocalDateTime.now().minusDays(30));
            s.setPlannedDeparture(LocalDateTime.now().minusDays(25));
            s.setActualDeparture(LocalDateTime.now().minusDays(25));
            s.setPlannedArrival(LocalDateTime.now().minusDays(5));
            s.setActualArrival(LocalDateTime.now().minusDays(5).plusHours(i * 10));
            s.setContainerCount(20);
            s.setCargoType("Electronics");
            s.setWeightTons(500.0);
            s.setStatus("DELIVERED");
            s.setActualDelayHours((double) (i * 10));
            s.setOnTimeFlag(i <= 2); // First 2 are on time
            s.setRouteKey("SHANGHAI → ROTTERDAM");
            s.setTransitDaysPlanned(20.0);
            s.setTransitDaysActual(20.0 + (i * 0.5));
            shipmentRepository.save(s);
        }
    }

    @Test
    @DisplayName("GET /routes/{origin}/{destination}/stats - Success")
    void testGetRouteStats_Success() throws Exception {
        mockMvc.perform(get("/routes/SHANGHAI/ROTTERDAM/stats"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.origin").value("SHANGHAI"))
                .andExpect(jsonPath("$.destination").value("ROTTERDAM"))
                .andExpect(jsonPath("$.routeKey").value("SHANGHAI → ROTTERDAM"))
                .andExpect(jsonPath("$.shipmentCount").value(3))
                .andExpect(jsonPath("$.averageDelayHours").exists())
                .andExpect(jsonPath("$.onTimeRate").exists())
                .andExpect(jsonPath("$.averageTransitDaysPlanned").exists())
                .andExpect(jsonPath("$.averageTransitDaysActual").exists());
    }

    @Test
    @DisplayName("GET /routes/{origin}/{destination}/stats - No shipments")
    void testGetRouteStats_NoShipments() throws Exception {
        mockMvc.perform(get("/routes/UNKNOWN/UNKNOWN/stats"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.origin").value("UNKNOWN"))
                .andExpect(jsonPath("$.destination").value("UNKNOWN"))
                .andExpect(jsonPath("$.shipmentCount").value(0))
                .andExpect(jsonPath("$.averageDelayHours").isEmpty())
                .andExpect(jsonPath("$.onTimeRate").isEmpty());
    }
}
