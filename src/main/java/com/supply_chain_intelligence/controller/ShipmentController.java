package com.supply_chain_intelligence.controller;

import com.supply_chain_intelligence.model.Shipment;
import com.supply_chain_intelligence.service.ShipmentService;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;

@RestController
@RequestMapping("/shipments")
public class ShipmentController {
    private final ShipmentService shipmentService;

    public ShipmentController(ShipmentService shipmentService) {
        this.shipmentService = shipmentService;
    }

    @GetMapping("/{id}")
    public ResponseEntity<Shipment> getShipmentById(
            @PathVariable String id) {

        Shipment shipment = shipmentService.getShipmentById(id);

        return ResponseEntity.ok(shipment);
    }

    @GetMapping
    public ResponseEntity<Page<Shipment>> getShipments(
            @RequestParam(required = false) String origin,
            @RequestParam(required = false) String destination,
            @RequestParam(required = false) String status,

            @RequestParam(required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME)
            LocalDateTime fromDate,

            @RequestParam(required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME)
            LocalDateTime toDate,

            @PageableDefault(
                    page = 0,
                    size = 20,
                    sort = "plannedDeparture"
            )
            Pageable pageable) {

        Page<Shipment> shipments = shipmentService.getShipments(
                origin,
                destination,
                status,
                fromDate,
                toDate,
                pageable
        );

        return ResponseEntity.ok(shipments);
    }
}
