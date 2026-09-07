package com.supply_chain_intelligence.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.util.ContentCachingRequestWrapper;
import org.springframework.web.util.ContentCachingResponseWrapper;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

@Component
public class RequestLoggingFilter extends OncePerRequestFilter {
    private static final Logger logger = LoggerFactory.getLogger(RequestLoggingFilter.class);
    private final ObjectMapper objectMapper;

    public RequestLoggingFilter(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain) throws ServletException, IOException {

        long startTime = System.currentTimeMillis();

        ContentCachingRequestWrapper requestWrapper = new ContentCachingRequestWrapper(request, 1024);
        ContentCachingResponseWrapper responseWrapper = new ContentCachingResponseWrapper(response);

        try {
            filterChain.doFilter(requestWrapper, responseWrapper);
        } finally {
            long latency = System.currentTimeMillis() - startTime;

            Map<String, Object> logData = new HashMap<>();
            logData.put("timestamp", System.currentTimeMillis());
            logData.put("method", request.getMethod());
            logData.put("path", request.getRequestURI());
            logData.put("queryString", request.getQueryString());
            logData.put("statusCode", response.getStatus());
            logData.put("latencyMs", latency);
            logData.put("remoteAddr", request.getRemoteAddr());
            logData.put("userAgent", request.getHeader("User-Agent"));

            try {
                String jsonLog = objectMapper.writeValueAsString(logData);
                logger.info(jsonLog);
            } catch (Exception e) {
                logger.error("Failed to create JSON log", e);
            }

            responseWrapper.copyBodyToResponse();
        }
    }
}
