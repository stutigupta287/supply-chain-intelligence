package com.supply_chain_intelligence.service;

import com.supply_chain_intelligence.exception.ShipmentNotFoundException;
import com.supply_chain_intelligence.model.Shipment;
import com.supply_chain_intelligence.repository.ShipmentRepository;
import com.supply_chain_intelligence.specification.ShipmentSpecification;
import org.springframework.data.domain.Page;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.data.domain.Pageable;
import java.time.LocalDateTime;

@Service
public class ShipmentService {
    private final ShipmentRepository shipmentRepository;

    public ShipmentService(ShipmentRepository shipmentRepository) {
        this.shipmentRepository = shipmentRepository;
    }

    public Shipment getShipmentById(String shipmentId) {

        return shipmentRepository.findById(shipmentId)
                .orElseThrow(() -> new ShipmentNotFoundException(shipmentId));
    }

    public Page<Shipment> getShipments(
            String origin,
            String destination,
            String status,
            LocalDateTime fromDate,
            LocalDateTime toDate,
            Pageable pageable) {

        Specification<Shipment> specification =
                Specification.where(ShipmentSpecification.hasOrigin(origin))
                        .and(ShipmentSpecification.hasDestination(destination))
                        .and(ShipmentSpecification.hasStatus(status))
                        .and(ShipmentSpecification.departureFrom(fromDate))
                        .and(ShipmentSpecification.departureTo(toDate));

        return shipmentRepository.findAll(specification, pageable);
    }
}
