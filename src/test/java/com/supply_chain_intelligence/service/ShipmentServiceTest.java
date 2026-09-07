package com.supply_chain_intelligence.service;

import com.supply_chain_intelligence.exception.ShipmentNotFoundException;
import com.supply_chain_intelligence.model.Shipment;
import com.supply_chain_intelligence.repository.ShipmentRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("ShipmentService Unit Tests")
class ShipmentServiceTest {

    @Mock
    private ShipmentRepository shipmentRepository;

    @InjectMocks
    private ShipmentService shipmentService;

    private Shipment testShipment;

    @BeforeEach
    void setUp() {
        testShipment = new Shipment();
        testShipment.setShipmentId("SHP-001");
        testShipment.setOriginPort("SHANGHAI");
        testShipment.setDestinationPort("ROTTERDAM");
        testShipment.setStatus("DELIVERED");
        testShipment.setOnTimeFlag(true);
        testShipment.setActualDelayHours(5.0);
    }

    @Test
    @DisplayName("Should return shipment when ID exists")
    void testGetShipmentById_Success() {
        // Arrange
        when(shipmentRepository.findById("SHP-001")).thenReturn(Optional.of(testShipment));

        // Act
        Shipment result = shipmentService.getShipmentById("SHP-001");

        // Assert
        assertNotNull(result);
        assertEquals("SHP-001", result.getShipmentId());
        assertEquals("SHANGHAI", result.getOriginPort());
        verify(shipmentRepository, times(1)).findById("SHP-001");
    }

    @Test
    @DisplayName("Should throw ShipmentNotFoundException when ID does not exist")
    void testGetShipmentById_NotFound() {
        // Arrange
        when(shipmentRepository.findById("INVALID")).thenReturn(Optional.empty());

        // Act & Assert
        assertThrows(ShipmentNotFoundException.class, () -> {
            shipmentService.getShipmentById("INVALID");
        });
        verify(shipmentRepository, times(1)).findById("INVALID");
    }

    @Test
    @DisplayName("Should return paginated shipments with filters")
    void testGetShipments_WithFilters() {
        // Arrange
        List<Shipment> shipments = List.of(testShipment);
        Page<Shipment> expectedPage = new PageImpl<>(shipments);
        Pageable pageable = PageRequest.of(0, 20);

        when(shipmentRepository.findAll(any(Specification.class), eq(pageable)))
                .thenReturn(expectedPage);

        // Act
        Page<Shipment> result = shipmentService.getShipments(
                "SHANGHAI",
                "ROTTERDAM",
                "DELIVERED",
                LocalDateTime.now().minusDays(30),
                LocalDateTime.now(),
                pageable
        );

        // Assert
        assertNotNull(result);
        assertEquals(1, result.getTotalElements());
        assertEquals("SHP-001", result.getContent().get(0).getShipmentId());
        verify(shipmentRepository, times(1)).findAll(any(Specification.class), eq(pageable));
    }

    @Test
    @DisplayName("Should return all shipments when no filters applied")
    void testGetShipments_NoFilters() {
        // Arrange
        List<Shipment> shipments = List.of(testShipment);
        Page<Shipment> expectedPage = new PageImpl<>(shipments);
        Pageable pageable = PageRequest.of(0, 20);

        when(shipmentRepository.findAll(any(Specification.class), eq(pageable)))
                .thenReturn(expectedPage);

        // Act
        Page<Shipment> result = shipmentService.getShipments(
                null, null, null, null, null, pageable
        );

        // Assert
        assertNotNull(result);
        assertFalse(result.getContent().isEmpty());
        verify(shipmentRepository, times(1)).findAll(any(Specification.class), eq(pageable));
    }
}
