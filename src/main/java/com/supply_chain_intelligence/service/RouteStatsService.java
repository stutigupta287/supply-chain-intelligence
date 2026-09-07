package com.supply_chain_intelligence.service;

import com.supply_chain_intelligence.dto.RouteStatsResponse;
import com.supply_chain_intelligence.model.Shipment;
import com.supply_chain_intelligence.repository.ShipmentRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class RouteStatsService {
    private final ShipmentRepository shipmentRepository;

    public RouteStatsService(ShipmentRepository shipmentRepository) {
        this.shipmentRepository = shipmentRepository;
    }

    public RouteStatsResponse getRouteStats(String origin, String destination) {
        List<Shipment> shipments = shipmentRepository.findByOriginPortAndDestinationPort(origin, destination);

        if (shipments.isEmpty()) {
            return new RouteStatsResponse(
                    origin,
                    destination,
                    origin + " → " + destination,
                    0L,
                    null,
                    null,
                    null,
                    null
            );
        }

        long shipmentCount = shipments.size();

        // Calculate average delay hours (only for shipments with actual data)
        Double averageDelayHours = shipments.stream()
                .filter(s -> s.getActualDelayHours() != null)
                .mapToDouble(Shipment::getActualDelayHours)
                .average()
                .orElse(0.0);

        // Calculate on-time rate (percentage of shipments that arrived on time)
        long onTimeCount = shipments.stream()
                .filter(s -> s.getOnTimeFlag() != null && s.getOnTimeFlag())
                .count();
        Double onTimeRate = (double) onTimeCount / shipmentCount * 100.0;

        // Calculate average transit days
        Double avgTransitPlanned = shipments.stream()
                .filter(s -> s.getTransitDaysPlanned() != null)
                .mapToDouble(Shipment::getTransitDaysPlanned)
                .average()
                .orElse(0.0);

        Double avgTransitActual = shipments.stream()
                .filter(s -> s.getTransitDaysActual() != null)
                .mapToDouble(Shipment::getTransitDaysActual)
                .average()
                .orElse(0.0);

        return new RouteStatsResponse(
                origin,
                destination,
                origin + " → " + destination,
                shipmentCount,
                averageDelayHours,
                onTimeRate,
                avgTransitPlanned,
                avgTransitActual
        );
    }
}
