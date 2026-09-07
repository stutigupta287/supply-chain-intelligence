package com.supply_chain_intelligence.specification;

import com.supply_chain_intelligence.model.Shipment;
import org.springframework.data.jpa.domain.Specification;

import java.time.LocalDateTime;

public class ShipmentSpecification {
    public static Specification<Shipment> hasOrigin(String origin) {
        return (root, query, cb) ->
                origin == null || origin.isBlank()
                        ? cb.conjunction()
                        : cb.equal(root.get("originPort"), origin);
    }

    public static Specification<Shipment> hasDestination(String destination) {
        return (root, query, cb) ->
                destination == null || destination.isBlank()
                        ? cb.conjunction()
                        : cb.equal(root.get("destinationPort"), destination);
    }

    public static Specification<Shipment> hasStatus(String status) {
        return (root, query, cb) ->
                status == null || status.isBlank()
                        ? cb.conjunction()
                        : cb.equal(root.get("status"), status);
    }

    public static Specification<Shipment> departureFrom(LocalDateTime fromDate) {
        return (root, query, cb) ->
                fromDate == null
                        ? cb.conjunction()
                        : cb.greaterThanOrEqualTo(
                        root.get("plannedDeparture"),
                        fromDate
                );
    }

    public static Specification<Shipment> departureTo(LocalDateTime toDate) {
        return (root, query, cb) ->
                toDate == null
                        ? cb.conjunction()
                        : cb.lessThanOrEqualTo(
                        root.get("plannedDeparture"),
                        toDate
                );
    }
}
