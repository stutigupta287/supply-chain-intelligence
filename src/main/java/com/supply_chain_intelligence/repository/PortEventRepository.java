package com.supply_chain_intelligence.repository;

import com.supply_chain_intelligence.model.PortEvent;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PortEventRepository extends JpaRepository<PortEvent, String> {
}
