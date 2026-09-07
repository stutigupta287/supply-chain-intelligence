package com.supply_chain_intelligence.service;

import com.supply_chain_intelligence.dto.DelayPredictionRequest;
import com.supply_chain_intelligence.dto.DelayPredictionResponse;
import com.supply_chain_intelligence.model.Shipment;
import com.supply_chain_intelligence.repository.ShipmentRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.DayOfWeek;
import java.time.temporal.ChronoUnit;
import java.util.Optional;

@Service
public class DelayPredictionService {

    private static final Logger logger = LoggerFactory.getLogger(DelayPredictionService.class);

    private final RestTemplate restTemplate;
    private final ShipmentRepository shipmentRepository;

    @Value("${ml.service.url:http://ml-service:5000}")
    private String mlServiceUrl;

    // Default port congestion scores (can be loaded from ports.csv later)
    private static final double DEFAULT_CONGESTION_SCORE = 5.0;

    public DelayPredictionService(RestTemplate restTemplate, ShipmentRepository shipmentRepository) {
        this.restTemplate = restTemplate;
        this.shipmentRepository = shipmentRepository;
    }

    /**
     * Predict delay risk for a shipment by ID
     * Loads shipment from database and extracts features
     */
    public DelayPredictionResponse predictDelayForShipment(String shipmentId) {
        logger.info("Predicting delay for shipment: {}", shipmentId);

        // Load shipment from database
        Optional<Shipment> shipmentOpt = shipmentRepository.findById(shipmentId);
        if (shipmentOpt.isEmpty()) {
            throw new RuntimeException("Shipment not found: " + shipmentId);
        }

        Shipment shipment = shipmentOpt.get();

        // Extract features from shipment
        DelayPredictionRequest request = extractFeatures(shipment);

        // Call ML service
        return callMlService(request);
    }

    /**
     * Predict delay risk from booking details
     */
    public DelayPredictionResponse predictDelayFromFeatures(DelayPredictionRequest request) {
        logger.info("Predicting delay for route: {} -> {}", request.getOriginPort(), request.getDestinationPort());
        return callMlService(request);
    }

    /**
     * Extract features from a Shipment entity
     */
    private DelayPredictionRequest extractFeatures(Shipment shipment) {
        DelayPredictionRequest request = new DelayPredictionRequest();

        // Categorical features
        request.setOriginPort(shipment.getOriginPort());
        request.setDestinationPort(shipment.getDestinationPort());
        request.setCargoType(shipment.getCargoType());

        // Numeric features
        request.setWeightTons(shipment.getWeightTons());
        request.setContainerCount(shipment.getContainerCount());

        // Calculate planned transit days
        if (shipment.getPlannedDeparture() != null && shipment.getPlannedArrival() != null) {
            long days = ChronoUnit.DAYS.between(
                    shipment.getPlannedDeparture(),
                    shipment.getPlannedArrival()
            );
            request.setPlannedTransitDays((double) days);
        } else {
            request.setPlannedTransitDays(shipment.getTransitDaysPlanned());
        }

        // Calculate booking lead days
        if (shipment.getBookingDate() != null && shipment.getPlannedDeparture() != null) {
            long leadDays = ChronoUnit.DAYS.between(
                    shipment.getBookingDate(),
                    shipment.getPlannedDeparture()
            );
            request.setBookingLeadDays((double) leadDays);
        } else {
            request.setBookingLeadDays(5.0); // Default
        }

        // Booking date features
        if (shipment.getBookingDate() != null) {
            request.setBookingMonth(shipment.getBookingDate().getMonthValue());
            DayOfWeek dayOfWeek = shipment.getBookingDate().getDayOfWeek();
            request.setBookingDayOfWeek(dayOfWeek.getValue() - 1); // 0=Monday, 6=Sunday
        } else {
            request.setBookingMonth(1);
            request.setBookingDayOfWeek(0);
        }

        // Port congestion scores (using defaults for now)
        // TODO: Load from ports.csv
        request.setOriginCongestionScore(DEFAULT_CONGESTION_SCORE);
        request.setDestinationCongestionScore(DEFAULT_CONGESTION_SCORE);

        return request;
    }

    /**
     * Call the ML microservice to get prediction
     */
    private DelayPredictionResponse callMlService(DelayPredictionRequest request) {
        String url = mlServiceUrl + "/predict";

        logger.debug("Calling ML service at: {}", url);
        logger.debug("Request: {}", request);

        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            HttpEntity<DelayPredictionRequest> entity = new HttpEntity<>(request, headers);

            ResponseEntity<DelayPredictionResponse> response = restTemplate.postForEntity(
                    url,
                    entity,
                    DelayPredictionResponse.class
            );

            DelayPredictionResponse prediction = response.getBody();
            logger.info("ML Service response: {}", prediction);

            return prediction;

        } catch (Exception e) {
            logger.error("Failed to call ML service: {}", e.getMessage(), e);
            throw new RuntimeException("ML service call failed: " + e.getMessage(), e);
        }
    }

    /**
     * Check if ML service is healthy
     */
    public boolean isMlServiceHealthy() {
        String url = mlServiceUrl + "/health";
        try {
            ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);
            return response.getStatusCode().is2xxSuccessful();
        } catch (Exception e) {
            logger.warn("ML service health check failed: {}", e.getMessage());
            return false;
        }
    }
}
