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

import static org.hamcrest.Matchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@Transactional
@DisplayName("Shipment API Integration Tests")
class ShipmentControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ShipmentRepository shipmentRepository;

    @BeforeEach
    void setUp() {
        shipmentRepository.deleteAll();

        // Create test shipments
        Shipment s1 = new Shipment();
        s1.setShipmentId("SHP-TEST-001");
        s1.setCustomerId("CUST-001");
        s1.setOriginPort("SHANGHAI");
        s1.setDestinationPort("ROTTERDAM");
        s1.setVesselId("VESSEL-001");
        s1.setBookingDate(LocalDateTime.of(2024, 1, 1, 10, 0));
        s1.setPlannedDeparture(LocalDateTime.of(2024, 1, 5, 10, 0));
        s1.setActualDeparture(LocalDateTime.of(2024, 1, 5, 12, 0));
        s1.setPlannedArrival(LocalDateTime.of(2024, 1, 25, 10, 0));
        s1.setActualArrival(LocalDateTime.of(2024, 1, 25, 15, 0));
        s1.setContainerCount(20);
        s1.setCargoType("Electronics");
        s1.setWeightTons(500.0);
        s1.setStatus("DELIVERED");
        s1.setActualDelayHours(5.0);
        s1.setOnTimeFlag(true);
        s1.setRouteKey("SHANGHAI → ROTTERDAM");
        s1.setTransitDaysPlanned(20.0);
        s1.setTransitDaysActual(20.125);
        shipmentRepository.save(s1);

        Shipment s2 = new Shipment();
        s2.setShipmentId("SHP-TEST-002");
        s2.setCustomerId("CUST-002");
        s2.setOriginPort("SHANGHAI");
        s2.setDestinationPort("LOS ANGELES");
        s2.setVesselId("VESSEL-002");
        s2.setBookingDate(LocalDateTime.of(2024, 1, 10, 10, 0));
        s2.setPlannedDeparture(LocalDateTime.of(2024, 1, 15, 10, 0));
        s2.setActualDeparture(LocalDateTime.of(2024, 1, 15, 10, 0));
        s2.setPlannedArrival(LocalDateTime.of(2024, 2, 5, 10, 0));
        s2.setActualArrival(LocalDateTime.of(2024, 2, 7, 10, 0));
        s2.setContainerCount(15);
        s2.setCargoType("Furniture");
        s2.setWeightTons(300.0);
        s2.setStatus("DELAYED");
        s2.setActualDelayHours(48.0);
        s2.setOnTimeFlag(false);
        s2.setRouteKey("SHANGHAI → LOS ANGELES");
        s2.setTransitDaysPlanned(21.0);
        s2.setTransitDaysActual(23.0);
        shipmentRepository.save(s2);
    }

    @Test
    @DisplayName("GET /shipments/{id} - Success")
    void testGetShipmentById_Success() throws Exception {
        mockMvc.perform(get("/shipments/SHP-TEST-001"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.shipmentId").value("SHP-TEST-001"))
                .andExpect(jsonPath("$.originPort").value("SHANGHAI"))
                .andExpect(jsonPath("$.destinationPort").value("ROTTERDAM"))
                .andExpect(jsonPath("$.status").value("DELIVERED"))
                .andExpect(jsonPath("$.onTimeFlag").value(true))
                .andExpect(jsonPath("$.actualDelayHours").value(5.0));
    }

    @Test
    @DisplayName("GET /shipments/{id} - Not Found (404)")
    void testGetShipmentById_NotFound() throws Exception {
        mockMvc.perform(get("/shipments/INVALID-ID"))
                .andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.status").value(404))
                .andExpect(jsonPath("$.error").value("Not Found"))
                .andExpect(jsonPath("$.message").exists());
    }

    @Test
    @DisplayName("GET /shipments - List all shipments")
    void testGetShipments_All() throws Exception {
        mockMvc.perform(get("/shipments"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.content").isArray())
                .andExpect(jsonPath("$.content", hasSize(2)))
                .andExpect(jsonPath("$.totalElements").value(2));
    }

    @Test
    @DisplayName("GET /shipments - Filter by origin")
    void testGetShipments_FilterByOrigin() throws Exception {
        mockMvc.perform(get("/shipments")
                        .param("origin", "SHANGHAI"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content").isArray())
                .andExpect(jsonPath("$.content", hasSize(2)));
    }

    @Test
    @DisplayName("GET /shipments - Filter by destination")
    void testGetShipments_FilterByDestination() throws Exception {
        mockMvc.perform(get("/shipments")
                        .param("destination", "ROTTERDAM"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content").isArray())
                .andExpect(jsonPath("$.content", hasSize(1)))
                .andExpect(jsonPath("$.content[0].shipmentId").value("SHP-TEST-001"));
    }

    @Test
    @DisplayName("GET /shipments - Filter by status")
    void testGetShipments_FilterByStatus() throws Exception {
        mockMvc.perform(get("/shipments")
                        .param("status", "DELAYED"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content").isArray())
                .andExpect(jsonPath("$.content", hasSize(1)))
                .andExpect(jsonPath("$.content[0].status").value("DELAYED"));
    }

    @Test
    @DisplayName("GET /shipments - Pagination")
    void testGetShipments_Pagination() throws Exception {
        mockMvc.perform(get("/shipments")
                        .param("page", "0")
                        .param("size", "1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content", hasSize(1)))
                .andExpect(jsonPath("$.totalElements").value(2))
                .andExpect(jsonPath("$.totalPages").value(2));
    }

    @Test
    @DisplayName("GET /shipments - Multiple filters")
    void testGetShipments_MultipleFilters() throws Exception {
        mockMvc.perform(get("/shipments")
                        .param("origin", "SHANGHAI")
                        .param("destination", "ROTTERDAM")
                        .param("status", "DELIVERED"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content", hasSize(1)))
                .andExpect(jsonPath("$.content[0].shipmentId").value("SHP-TEST-001"));
    }
}
