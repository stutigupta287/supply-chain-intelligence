package com.supply_chain_intelligence.repository;

import com.supply_chain_intelligence.model.Shipment;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;

import java.util.List;

public interface ShipmentRepository extends JpaRepository<Shipment, String>, JpaSpecificationExecutor<Shipment> {

    List<Shipment> findByOriginPortAndDestinationPort(
            String originPort,
            String destinationPort
    );
}