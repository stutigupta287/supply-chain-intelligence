package com.supply_chain_intelligence.service;

import com.supply_chain_intelligence.model.Shipment;
import com.supply_chain_intelligence.repository.ShipmentRepository;
import com.supply_chain_intelligence.model.Port;
import com.supply_chain_intelligence.repository.PortRepository;
import com.supply_chain_intelligence.model.PortEvent;
import com.supply_chain_intelligence.repository.PortEventRepository;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.io.Reader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

@Component
public class CsvDataLoaderService implements CommandLineRunner {

    private static final Logger logger = LoggerFactory.getLogger(CsvDataLoaderService.class);
    
    private final ShipmentRepository shipmentRepository;
    private final PortRepository portRepository;
    private final PortEventRepository portEventRepository;
    
    @Value("${app.data.load-csv-on-startup:false}")
    private boolean loadCsvOnStartup;
    
    @Value("${app.data.csv-path:curated/shipments_curated.csv}")
    private String csvPath;
    
    @Value("${app.data.skip-if-data-exists:true}")
    private boolean skipIfDataExists;

    @Value("${app.data.ports-csv-path:curated/ports_curated.csv}")
    private String portsCsvPath;

    @Value("${app.data.port-events-csv-path:curated/port_events_curated.csv}")
    private String portEventsCsvPath;

    public CsvDataLoaderService(ShipmentRepository shipmentRepository, PortRepository portRepository, PortEventRepository portEventRepository) {
        this.shipmentRepository = shipmentRepository;
        this.portRepository = portRepository;
        this.portEventRepository = portEventRepository;
    }

    @Override
    public void run(String... args) throws Exception {
        if (!loadCsvOnStartup) {
            logger.info("CSV data loading is DISABLED. Set LOAD_CSV_ON_STARTUP=true to enable.");
            return;
        }

        logger.info("CSV data loading is ENABLED. Checking data...");

        try {
            loadPortsIfNeeded();
            loadShipmentsIfNeeded();
            loadPortEventsIfNeeded();
        } catch (Exception e) {
            logger.error("Failed to load CSV data: {}", e.getMessage(), e);
            throw e;
        }
    }

    private void loadShipmentsIfNeeded() throws IOException {
        long existingCount = shipmentRepository.count();

        if (skipIfDataExists && existingCount > 0) {
            logger.info(
                    "Database already contains {} shipments. Skipping shipments CSV load.",
                    existingCount
            );
            return;
        }

        loadShipmentsFromCsv();
    }

    private void loadPortsIfNeeded() throws IOException {

        long existingCount = portRepository.count();

        if (skipIfDataExists && existingCount > 0) {
            logger.info(
                    "Database already contains {} ports. Skipping ports CSV load.",
                    existingCount
            );
            return;
        }

        loadPortsFromCsv();
    }

    private void loadPortsFromCsv() throws IOException {

        Path path = Paths.get(portsCsvPath);

        if (!Files.exists(path)) {
            logger.error("Ports CSV file not found at: {}", portsCsvPath);
            throw new IOException("Ports CSV file not found: " + portsCsvPath);
        }

        logger.info("Loading ports from: {}", path.toAbsolutePath());

        List<Port> ports = new ArrayList<>();

        int lineNumber = 0;
        int successCount = 0;
        int errorCount = 0;

        try (BufferedReader reader =
                     new BufferedReader(new FileReader(path.toFile()))) {

            String line;
            String[] headers = null;

            while ((line = reader.readLine()) != null) {

                lineNumber++;

                if (line.trim().isEmpty()) {
                    continue;
                }

                if (lineNumber == 1) {
                    headers = parseCsvLine(line);
                    logger.info(
                            "Ports CSV headers: {}",
                            String.join(", ", headers)
                    );
                    continue;
                }

                try {
                    String[] values = parseCsvLine(line);

                    if (values.length != headers.length) {
                        logger.warn(
                                "Line {}: Column count mismatch. Expected {}, got {}",
                                lineNumber,
                                headers.length,
                                values.length
                        );

                        errorCount++;
                        continue;
                    }

                    Port port = parsePort(headers, values);

                    ports.add(port);
                    successCount++;

                } catch (Exception e) {

                    logger.warn(
                            "Line {}: Failed to parse port - Error: {}",
                            lineNumber,
                            e.getMessage()
                    );

                    errorCount++;
                }
            }

            if (!ports.isEmpty()) {
                portRepository.saveAll(ports);
            }

            logger.info("Ports CSV loading complete!");
            logger.info("Successfully loaded: {} ports", successCount);
            logger.info("Errors: {} rows", errorCount);
            logger.info("Total ports in database: {}", portRepository.count());
        }
    }

    private Port parsePort(String[] headers, String[] values) {

        Port port = new Port();

        for (int i = 0; i < headers.length; i++) {

            String header = headers[i].trim().toLowerCase();
            String value = values[i].trim();

            if (value.isEmpty() || value.equalsIgnoreCase("null")) {
                continue;
            }

            switch (header) {

                case "port_code":
                    port.setPortCode(value);
                    break;

                case "port_name":
                    port.setPortName(value);
                    break;

                case "country":
                    port.setCountry(value);
                    break;

                case "region":
                    port.setRegion(value);
                    break;

                case "timezone":
                    port.setTimezone(value);
                    break;

                case "avg_congestion_score":
                    port.setAvgCongestionScore(
                            Double.parseDouble(value)
                    );
                    break;
            }
        }

        return port;
    }

    private void loadPortEventsIfNeeded() throws IOException {

        long existingCount = portEventRepository.count();

        if (skipIfDataExists && existingCount > 0) {
            logger.info(
                    "Database already contains {} port events. Skipping port events CSV load.",
                    existingCount
            );
            return;
        }

        loadPortEventsFromCsv();
    }

    private void loadPortEventsFromCsv() throws IOException {

        Path path = Paths.get(portEventsCsvPath);

        if (!Files.exists(path)) {
            logger.error("Port events CSV file not found at: {}", portEventsCsvPath);
            throw new IOException(
                    "Port events CSV file not found: " + portEventsCsvPath
            );
        }

        logger.info("Loading port events from: {}", path.toAbsolutePath());

        List<PortEvent> portEvents = new ArrayList<>();

        int successCount = 0;
        int errorCount = 0;

        try (
                Reader reader = Files.newBufferedReader(path);

                CSVParser csvParser = CSVFormat.DEFAULT
                        .builder()
                        .setHeader()
                        .setSkipHeaderRecord(true)
                        .get()
                        .parse(reader)
        ) {

            for (CSVRecord record : csvParser) {

                try {

                    PortEvent portEvent = new PortEvent();

                    portEvent.setEventId(
                            record.get("event_id")
                    );

                    portEvent.setEventTimestamp(
                            parseDateTime(record.get("event_timestamp"))
                    );

                    portEvent.setPortCode(
                            record.get("port_code")
                    );

                    portEvent.setVesselId(
                            record.get("vessel_id")
                    );

                    portEvent.setEventType(
                            record.get("event_type")
                    );

                    portEvent.setDelayMinutes(
                            Integer.parseInt(record.get("delay_minutes"))
                    );

                    String notes = record.get("notes");

                    portEvent.setNotes(
                            notes == null || notes.isBlank()
                                    ? null
                                    : notes
                    );

                    portEvents.add(portEvent);
                    successCount++;

                    // Save every 500 records
                    if (portEvents.size() >= 500) {

                        portEventRepository.saveAll(portEvents);

                        logger.info(
                                "Saved batch of {} port events. Total: {}",
                                portEvents.size(),
                                successCount
                        );

                        portEvents.clear();
                    }

                } catch (Exception e) {

                    errorCount++;

                    logger.warn(
                            "Failed to parse port event at CSV record {}: {}",
                            record.getRecordNumber(),
                            e.getMessage()
                    );
                }
            }

            // Save remaining records
            if (!portEvents.isEmpty()) {

                portEventRepository.saveAll(portEvents);

                logger.info(
                        "Saved final batch of {} port events",
                        portEvents.size()
                );
            }
        }

        logger.info("Port events CSV loading complete!");
        logger.info("Successfully loaded: {} port events", successCount);
        logger.info("Errors: {} rows", errorCount);
        logger.info(
                "Total port events in database: {}",
                portEventRepository.count()
        );
    }

    private PortEvent parsePortEvent(String[] headers, String[] values) {

        PortEvent portEvent = new PortEvent();

        for (int i = 0; i < headers.length; i++) {

            String header = headers[i].trim().toLowerCase();
            String value = values[i].trim();

            if (value.isEmpty() || value.equalsIgnoreCase("null")) {
                continue;
            }

            switch (header) {

                case "event_id":
                    portEvent.setEventId(value);
                    break;

                case "event_timestamp":
                    portEvent.setEventTimestamp(parseDateTime(value));
                    break;

                case "port_code":
                    portEvent.setPortCode(value);
                    break;

                case "vessel_id":
                    portEvent.setVesselId(value);
                    break;

                case "event_type":
                    portEvent.setEventType(value);
                    break;

                case "delay_minutes":
                    portEvent.setDelayMinutes(Integer.parseInt(value));
                    break;

                case "notes":
                    portEvent.setNotes(value);
                    break;
            }
        }

        return portEvent;
    }

    private void loadShipmentsFromCsv() throws IOException {
        Path path = Paths.get(csvPath);
        
        if (!Files.exists(path)) {
            logger.error("CSV file not found at: {}", csvPath);
            logger.error("Current working directory: {}", System.getProperty("user.dir"));
            throw new IOException("CSV file not found: " + csvPath);
        }

        logger.info("Loading shipments from: {}", path.toAbsolutePath());

        List<Shipment> shipments = new ArrayList<>();
        int lineNumber = 0;
        int successCount = 0;
        int errorCount = 0;

        try (BufferedReader reader = new BufferedReader(new FileReader(path.toFile()))) {
            String line;
            String[] headers = null;

            while ((line = reader.readLine()) != null) {
                lineNumber++;

                // Skip empty lines
                if (line.trim().isEmpty()) {
                    continue;
                }

                // Parse header
                if (lineNumber == 1) {
                    headers = parseCsvLine(line);
                    logger.info("CSV headers: {}", String.join(", ", headers));
                    continue;
                }

                // Parse data row
                try {
                    String[] values = parseCsvLine(line);
                    
                    if (values.length != headers.length) {
                        logger.warn("Line {}: Column count mismatch. Expected {}, got {}",
                                lineNumber, headers.length, values.length);
                        errorCount++;
                        continue;
                    }

                    Shipment shipment = parseShipment(headers, values);
                    shipments.add(shipment);
                    successCount++;

                    // Batch insert every 500 records
                    if (shipments.size() >= 500) {
                        shipmentRepository.saveAll(shipments);
                        logger.info("Saved batch of {} shipments. Total: {}", shipments.size(), successCount);
                        shipments.clear();
                    }

                } catch (Exception e) {
                    logger.warn("Line {}: Failed to parse: {} - Error: {}", lineNumber, line, e.getMessage());
                    errorCount++;
                }
            }

            // Save remaining shipments
            if (!shipments.isEmpty()) {
                shipmentRepository.saveAll(shipments);
                logger.info("Saved final batch of {} shipments", shipments.size());
            }

            logger.info("CSV loading complete!");
            logger.info("Successfully loaded: {} shipments", successCount);
            logger.info("Errors: {} rows", errorCount);
            logger.info("Total in database: {}", shipmentRepository.count());

        } catch (IOException e) {
            logger.error("Error reading CSV file: {}", e.getMessage());
            throw e;
        }
    }

    private Shipment parseShipment(String[] headers, String[] values) {
        Shipment shipment = new Shipment();

        for (int i = 0; i < headers.length; i++) {
            String header = headers[i].trim().toLowerCase();
            String value = values[i].trim();

            // Skip empty values
            if (value.isEmpty() || value.equalsIgnoreCase("null")) {
                continue;
            }

            try {
                switch (header) {
                    case "shipment_id":
                        shipment.setShipmentId(value);
                        break;
                    case "customer_id":
                        shipment.setCustomerId(value);
                        break;
                    case "origin_port":
                        shipment.setOriginPort(value);
                        break;
                    case "destination_port":
                        shipment.setDestinationPort(value);
                        break;
                    case "vessel_id":
                        shipment.setVesselId(value);
                        break;
                    case "booking_date":
                        shipment.setBookingDate(parseDateTime(value));
                        break;
                    case "planned_departure":
                        shipment.setPlannedDeparture(parseDateTime(value));
                        break;
                    case "actual_departure":
                        shipment.setActualDeparture(parseDateTime(value));
                        break;
                    case "planned_arrival":
                        shipment.setPlannedArrival(parseDateTime(value));
                        break;
                    case "actual_arrival":
                        shipment.setActualArrival(parseDateTime(value));
                        break;
                    case "container_count":
                        shipment.setContainerCount(Integer.parseInt(value));
                        break;
                    case "cargo_type":
                        shipment.setCargoType(value);
                        break;
                    case "weight_tons":
                        shipment.setWeightTons(Double.parseDouble(value));
                        break;
                    case "status":
                        shipment.setStatus(value);
                        break;
                    case "actual_delay_hours":
                        shipment.setActualDelayHours(Double.parseDouble(value));
                        break;
                    case "on_time_flag":
                        shipment.setOnTimeFlag(parseBoolean(value));
                        break;
                    case "route_key":
                        shipment.setRouteKey(value);
                        break;
                    case "transit_days_planned":
                        shipment.setTransitDaysPlanned(Double.parseDouble(value));
                        break;
                    case "transit_days_actual":
                        shipment.setTransitDaysActual(Double.parseDouble(value));
                        break;
                }
            } catch (Exception e) {
                logger.debug("Failed to parse field '{}' with value '{}': {}", header, value, e.getMessage());
            }
        }

        return shipment;
    }

    private LocalDateTime parseDateTime(String value) {
        if (value == null || value.trim().isEmpty()) {
            return null;
        }

        try {
            // Try ISO format first (2024-01-01T10:00:00)
            return LocalDateTime.parse(value, DateTimeFormatter.ISO_LOCAL_DATE_TIME);
        } catch (Exception e1) {
            try {
                // Try with space separator (2024-01-01 10:00:00)
                return LocalDateTime.parse(value, DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
            } catch (Exception e2) {
                logger.debug("Failed to parse datetime: {}", value);
                return null;
            }
        }
    }

    private Boolean parseBoolean(String value) {
        if (value == null || value.trim().isEmpty()) {
            return null;
        }
        
        value = value.trim().toLowerCase();
        return value.equals("true") || value.equals("1") || value.equals("yes");
    }

    private String[] parseCsvLine(String line) {
        // Simple CSV parser (handles basic comma-separated values)
        // For production, consider using a library like OpenCSV
        return line.split(",");
    }
}
