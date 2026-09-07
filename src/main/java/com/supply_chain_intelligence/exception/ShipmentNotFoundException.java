package com.supply_chain_intelligence.exception;

public class ShipmentNotFoundException extends RuntimeException{
    public ShipmentNotFoundException(String shipmentId) {
        super("Shipment not found with id: " + shipmentId);
    }
}
