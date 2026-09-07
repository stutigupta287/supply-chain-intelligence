# Build stage
FROM maven:3.9-eclipse-temurin-17 AS build

WORKDIR /app

# Copy pom.xml and download dependencies (cached layer)
COPY pom.xml .
COPY .mvn .mvn
RUN mvn dependency:go-offline -B

# Copy source code
COPY src ./src

# Build the application (skip tests in Docker build for faster builds)
RUN mvn clean package -DskipTests -Dmaven.test.skip=true

# Runtime stage
FROM eclipse-temurin:17-jre

WORKDIR /app

# Create non-root user
RUN groupadd --system spring && useradd --system --gid spring spring
USER spring:spring

# Copy the built JAR from build stage
COPY --from=build /app/target/*.jar app.jar

# Copy data files and reports
COPY --chown=spring:spring data ./data
COPY --chown=spring:spring reports ./reports
COPY --chown=spring:spring curated ./curated
COPY --chown=spring:spring quarantine ./quarantine
COPY --chown=spring:spring data-engineering ./data-engineering

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# Run the application
ENTRYPOINT ["java", "-jar", "app.jar"]
