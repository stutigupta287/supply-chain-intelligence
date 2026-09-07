package com.supply_chain_intelligence.controller;

import com.supply_chain_intelligence.dto.RouteStatsResponse;
import com.supply_chain_intelligence.service.RouteStatsService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/routes")
public class RouteStatsController {
    private final RouteStatsService routeStatsService;

    public RouteStatsController(RouteStatsService routeStatsService) {
        this.routeStatsService = routeStatsService;
    }

    @GetMapping("/{origin}/{destination}/stats")
    public ResponseEntity<RouteStatsResponse> getRouteStats(
            @PathVariable String origin,
            @PathVariable String destination) {

        RouteStatsResponse stats = routeStatsService.getRouteStats(origin, destination);

        return ResponseEntity.ok(stats);
    }
}
