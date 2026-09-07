# Supply Chain Intelligence Platform

A **microservices-based** supply chain analytics platform featuring:
- **Spring Boot API** (Java 17) for shipment analytics and orchestration
- **ML Microservice** (Python/FastAPI) for real-time delay prediction
- **PostgreSQL** for persistent data storage
- **GenAI Assistant** (Python/LangChain/Ollama) for natural language queries
- **Docker Compose** orchestration with health checks

The platform exposes REST endpoints for shipment search, route statistics, data quality reports, **delay prediction**, and health monitoring. It includes a complete data pipeline with ETL scripts, CSV ingestion, and a trained machine learning model for booking-time delay risk assessment.

## Table of Contents

- [Getting Started](#getting-started)
- [Architecture](#architecture)
- [Current Capabilities](#current-capabilities)
- [GenAI Assistant](#genai-assistant)
- [Data Pipeline](#data-pipeline)
- [Machine Learning](#machine-learning)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Docker Notes](#docker-notes)
- [CI/CD](#cicd)

---

## Getting Started

Follow these steps to get the complete Supply Chain Intelligence Platform running on your local machine.

### Prerequisites

1. **Docker & Docker Compose**
   ```bash
   docker --version  # Should be 20.10+
   docker compose version  # Should be 2.0+
   ```

2. **Python 3.11+** (for GenAI assistant)
   ```bash
   python --version
   ```

3. **Ollama** (for GenAI assistant)
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Pull the llama3.2 model
   ollama pull llama3.2
   
   # Verify installation
   ollama list
   ```

### Step 1: Start the Backend Services

The platform consists of three core services: PostgreSQL database, ML prediction service, and Spring Boot API.

```bash
# Clone the repository (if not already done)
cd supply-chain-intelligence

# Build and start all services
docker compose up --build -d

# Verify all services are healthy (wait ~60 seconds for startup)
docker compose ps
```

You should see three containers running:
- `supply-chain-postgres` (port 5432)
- `supply-chain-ml` (port 5000)
- `supply-chain-api` (port 8080)

### Step 2: Verify Services are Running

```bash
# Test API health
curl http://localhost:8080/health

# Test ML service integration
curl http://localhost:8080/predict-delay/health

# Test a sample shipment query
curl "http://localhost:8080/shipments?size=5"

# Test delay prediction
curl -X POST http://localhost:8080/predict-delay/shipment/SHP-03038
```

### Step 3: Start the GenAI Assistant

The GenAI assistant provides a conversational interface to query the platform using natural language.

```bash
# Navigate to the GenAI assistant directory
cd genai-assistant

# Install Python dependencies
pip install -r requirements.txt

# Start the interactive CLI
python main.py
```

You'll see the assistant prompt:

```
=== Supply Chain GenAI Assistant ===

Example questions:
  • What is the on-time rate for shipments from Shanghai to Rotterdam?
  • Which routes have the highest average delay?
  • What is the delay risk for shipment SHP-00421?

Commands: exit, quit, help

>> 
```

### Step 4: Try Example Queries

**Via GenAI Assistant:**
```
>> Which routes have the highest average delay?
>> What is the delay risk for shipment SHP-03038?
>> Show me shipments from Shanghai
```

**Via REST API:**
```bash
# Get route statistics
curl "http://localhost:8080/routes/CNSHA/NLRTM/stats"

# Search shipments
curl "http://localhost:8080/shipments?origin=CNSHA&size=10"

# Predict delay by shipment ID
curl -X POST http://localhost:8080/predict-delay/shipment/SHP-03038

# Predict delay from booking details
curl -X POST http://localhost:8080/predict-delay \
  -H "Content-Type: application/json" \
  -d '{
    "origin_port": "CNSHA",
    "destination_port": "USLAX",
    "cargo_type": "Electronics",
    "weight_tons": 500.0,
    "container_count": 5,
    "planned_transit_days": 14.0,
    "booking_lead_days": 10.0,
    "booking_month": 9,
    "booking_day_of_week": 1,
    "origin_congestion_score": 7.5,
    "destination_congestion_score": 6.0
  }'
```

### Stopping the Services

```bash
# Stop all Docker services
docker compose down

# Stop and remove all data (including database)
docker compose down -v

# Exit GenAI assistant (press Ctrl+C or type 'exit')
```

### Troubleshooting

**Services not starting:**
```bash
# Check logs
docker compose logs api
docker compose logs ml-service
docker compose logs postgres

# Restart a specific service
docker compose restart api
```

**Ollama not responding:**
```bash
# Check if Ollama is running
ollama list

# Restart Ollama service (if installed as service)
sudo systemctl restart ollama
```

**Port conflicts:**
```bash
# Check if ports are in use
lsof -i :8080  # API
lsof -i :5000  # ML service
lsof -i :5432  # PostgreSQL
```

---

## Architecture

The platform follows a microservices architecture with clear separation of concerns.

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────┐              ┌──────────────────────┐    │
│  │   GenAI Assistant    │              │   External Clients   │    │
│  │  (Python/LangChain)  │              │    (REST/HTTP)       │    │
│  │   - Ollama LLM       │              │   - Web Apps         │    │
│  │   - Tool Calling     │              │   - Mobile Apps      │    │
│  │   - NL Interface     │              │   - Third Party      │    │
│  └──────────┬───────────┘              └──────────┬───────────┘    │
│             │                                      │                 │
│             └──────────────────┬───────────────────┘                │
│                                │                                     │
└────────────────────────────────┼─────────────────────────────────────┘
                                 │
                          HTTP REST API
                                 │
┌────────────────────────────────▼─────────────────────────────────────┐
│                        APPLICATION LAYER                              │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │         Spring Boot API Service (Java 17)                      │ │
│  │                    Port: 8080                                  │ │
│  ├────────────────────────────────────────────────────────────────┤ │
│  │  Controllers:                                                  │ │
│  │   • ShipmentController    - Search & lookup                   │ │
│  │   • RouteController       - Route statistics                  │ │
│  │   • DataQualityController - DQ reports                        │ │
│  │   • DelayPredictionController - ML integration                │ │
│  │   • HealthController      - Health checks                     │ │
│  ├────────────────────────────────────────────────────────────────┤ │
│  │  Services:                                                     │ │
│  │   • ShipmentService       - Business logic                    │ │
│  │   • DelayPredictionService - ML orchestration                 │ │
│  │   • CsvLoaderService      - Data ingestion                    │ │
│  ├────────────────────────────────────────────────────────────────┤ │
│  │  Repositories (JPA):                                           │ │
│  │   • ShipmentRepository    - Database access                   │ │
│  │   • PortRepository        - Port data                         │ │
│  │   • PortEventRepository   - Event data                        │ │
│  └───────────────┬────────────────────────────────┬───────────────┘ │
│                  │                                 │                 │
└──────────────────┼─────────────────────────────────┼─────────────────┘
                   │                                 │
                   │ JPA/Hibernate                   │ HTTP REST
                   │                                 │
         ┌─────────▼──────────┐           ┌─────────▼──────────┐
         │                    │           │                    │
┌────────┤  PostgreSQL DB     │           │  ML Service        ├────────┐
│        │    Port: 5432      │           │  (Python/FastAPI)  │        │
│        │                    │           │    Port: 5000      │        │
│        ├────────────────────┤           ├────────────────────┤        │
│        │  Tables:           │           │  Endpoints:        │        │
│        │   • shipments      │           │   • /predict       │        │
│        │   • ports          │           │   • /health        │        │
│        │   • port_events    │           │   • /model/info    │        │
│        │                    │           │                    │        │
│        │  Features:         │           │  Components:       │        │
│        │   • JSONB support  │           │   • scikit-learn   │        │
│        │   • UUID types     │           │   • Logistic Reg   │        │
│        │   • Indexes        │           │   • Feature Eng    │        │
│        └────────────────────┘           └────────────────────┘        │
│                                                                        │
│                          DATA LAYER                                   │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│                       INFRASTRUCTURE LAYER                              │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Docker Compose Orchestration:                                         │
│   • Network: supply-chain-network (bridge)                             │
│   • Volumes: postgres_data (persistent storage)                        │
│   • Health Checks: All services monitored                              │
│   • Dependency Management: Startup order enforced                      │
│                                                                         │
│  Data Pipeline (Optional):                                             │
│   • Python ETL Scripts (data-engineering/)                             │
│   • Data Quality Checks                                                │
│   • CSV Transformation (raw → curated/quarantine)                      │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### Component Descriptions

#### 1. **GenAI Assistant** (Python/LangChain)
- **Technology**: Python 3.11, LangChain, Ollama (llama3.2)
- **Purpose**: Natural language interface for supply chain queries
- **Features**:
  - Tool calling framework with LangChain
  - Local LLM inference via Ollama
  - Automatic tool selection based on user intent
  - Interactive CLI REPL

#### 2. **Spring Boot API Service** (Java 17)
- **Technology**: Spring Boot 4.1.1, Spring Data JPA, Hibernate
- **Purpose**: Central API gateway and business logic orchestration
- **Features**:
  - RESTful endpoints for shipments, routes, and predictions
  - CSV data ingestion on startup
  - Health monitoring and observability
  - Integration with ML service via REST

#### 3. **ML Prediction Service** (Python/FastAPI)
- **Technology**: Python 3.11, FastAPI, scikit-learn 1.9.0
- **Purpose**: Real-time delay prediction using trained ML model
- **Features**:
  - Logistic regression model for delay classification
  - Feature engineering pipeline
  - Model versioning and metadata
  - Independent microservice (no database dependency)

#### 4. **PostgreSQL Database**
- **Technology**: PostgreSQL 16 (Alpine)
- **Purpose**: Persistent data storage
- **Schema**:
  - `shipments`: Shipment records with JSONB fields
  - `ports`: Port reference data
  - `port_events`: Port event timeline data

### Data Flow

**Prediction Request Flow:**
```
User Query → API Controller → DelayPredictionService 
          → HTTP Request → ML Service (/predict) 
          → Feature Extraction → Model Inference 
          → Response → API → User
```

**Natural Language Query Flow:**
```
User Question → GenAI Assistant → Ollama LLM 
            → Tool Selection → API Call (HTTP) 
            → Response Processing → Natural Language Response
```

### Communication Protocols

- **External → API**: HTTP/REST (JSON)
- **API → Database**: JDBC/JPA (PostgreSQL wire protocol)
- **API → ML Service**: HTTP/REST (JSON)
- **GenAI → API**: HTTP/REST (JSON)
- **All Services**: Docker bridge network (internal DNS)

---

## Technology Choices

This section explains the rationale behind our technology stack decisions.

### Spring Boot (Java 17) - API Service

**Why Spring Boot:**
- ✅ **Enterprise-grade**: Battle-tested in production environments with robust error handling
- ✅ **Rich ecosystem**: Spring Data JPA, Spring Boot Actuator, comprehensive testing support
- ✅ **Type safety**: Java's strong typing reduces runtime errors in business logic
- ✅ **Performance**: Efficient for high-throughput API operations with connection pooling
- ✅ **Developer productivity**: Auto-configuration, embedded servers, minimal boilerplate
- ✅ **Integration**: Seamless integration with PostgreSQL via JPA/Hibernate
- ✅ **Observability**: Built-in health checks, metrics, and monitoring endpoints


### PostgreSQL 16 - Database

**Why PostgreSQL:**
- ✅ **JSONB support**: Native JSON storage for flexible shipment metadata without schema changes
- ✅ **Advanced indexing**: B-tree, GiST, GIN indexes for complex queries
- ✅ **ACID compliance**: Strong consistency guarantees for transactional data
- ✅ **UUID support**: Native UUID type for distributed ID generation
- ✅ **Open source**: No licensing costs, active community, extensive documentation
- ✅ **Mature**: Proven reliability for analytical workloads

**Alternatives considered:**
- MySQL: Weaker JSON support, less robust for complex analytics
- MongoDB: Overkill for structured data, harder to enforce data integrity
- SQLite: Not suitable for multi-service concurrent access

### Python/FastAPI - ML Service

**Why Python + FastAPI:**
- ✅ **ML ecosystem**: scikit-learn, pandas, numpy - de facto standard for ML
- ✅ **FastAPI performance**: Async support, automatic OpenAPI docs, Pydantic validation
- ✅ **Type hints**: Python 3.11+ type hints improve code quality and IDE support
- ✅ **Rapid development**: Quick iteration for model experimentation and deployment
- ✅ **Separation**: Isolates ML dependencies from Java API (no version conflicts)
- ✅ **Model portability**: Easy to swap models, retrain, and version independently
- ✅ **Lightweight**: Smaller container footprint than embedding ML in JVM

### LangChain + Ollama - GenAI Assistant

**Why LangChain + Ollama:**
- ✅ **Local inference**: No API costs, no data privacy concerns, works offline
- ✅ **Tool calling**: LangChain's agent framework handles tool selection and chaining
- ✅ **Model flexibility**: Easy to swap LLMs (llama3.2, mistral, gemma) via Ollama
- ✅ **Open source**: No vendor lock-in, community-driven improvements
- ✅ **Rapid prototyping**: LangChain abstracts LLM orchestration complexity
- ✅ **Cost effective**: No per-token charges for development and demos
- ✅ **Integration**: Simple HTTP API client to call Spring Boot endpoints

### Docker Compose - Orchestration

**Why Docker Compose:**
- ✅ **Simplicity**: Single YAML file defines entire stack
- ✅ **Local development**: Fast iteration without Kubernetes complexity
- ✅ **Health checks**: Built-in service health monitoring and dependency ordering
- ✅ **Networking**: Automatic service discovery via DNS names
- ✅ **Portability**: Works identically on Linux, macOS, Windows (WSL2)
- ✅ **Volume management**: Easy persistent storage for PostgreSQL
- ✅ **Production path**: Compose files translate to Kubernetes manifests via Kompose

**Alternatives considered:**
- Kubernetes: Overkill for local development, steeper learning curve
- Bare metal scripts: Harder to reproduce environments, manual dependency management
- Vagrant: Heavier, slower, more resource-intensive

### scikit-learn - ML Framework

**Why scikit-learn:**
- ✅ **Simplicity**: Clean API, easy to understand and maintain
- ✅ **Lightweight**: Fast inference, small model files (<1MB)
- ✅ **Interpretable**: Logistic regression coefficients are explainable
- ✅ **Stable**: Mature library with consistent API across versions
- ✅ **No GPU required**: CPU inference is fast enough for real-time predictions
- ✅ **Deployment**: Joblib serialization makes model loading trivial

**Alternatives considered:**
- TensorFlow/PyTorch: Overkill for tabular data, slower inference, larger models
- XGBoost/LightGBM: More complex to tune, less interpretable
- H2O.ai: Heavyweight, JVM-based (negates microservice benefits)

### JPA/Hibernate - ORM

**Why JPA + Hibernate:**
- ✅ **Standard**: Java Persistence API is industry standard
- ✅ **Productivity**: Automatic CRUD, entity relationships, lazy loading
- ✅ **Type safety**: Compile-time checking for queries via Spring Data JPA
- ✅ **Caching**: Second-level cache reduces database round trips
- ✅ **Migrations**: Works well with Flyway/Liquibase for schema versioning
- ✅ **Testing**: Easy to swap with H2 in-memory database for tests

**Alternatives considered:**
- jOOQ: More control but more boilerplate, loses Spring Data repositories
- MyBatis: XML-heavy, manual mapping, less type safety
- JDBC Template: Too low-level, repetitive code for CRUD operations

### Design Principles

Our technology choices follow these core principles:

1. **Separation of Concerns**: Each service has a single responsibility (API orchestration, ML inference, data storage)
2. **Best Tool for the Job**: Python for ML, Java for enterprise APIs, SQL for analytics
3. **Developer Experience**: Minimize configuration, maximize productivity with conventions
4. **Operational Simplicity**: Docker Compose for easy deployment, health checks for observability
5. **Cost Efficiency**: Open-source stack with no recurring API costs
6. **Future-Proof**: Microservices can scale independently, easy to add new services

---

## Current Capabilities

### API Services
- ✅ Shipment search and lookup with pagination and optional filters
- ✅ Route-level statistics for delay, on-time rate, and transit days
- ✅ Data quality report serving from `reports/dq_report.json`
- ✅ **Delay prediction API** - Predict shipment delays using ML microservice
- ✅ Health checks and monitoring endpoints

### Data Pipeline
- ✅ Startup CSV loader for three database tables: `shipments`, `ports`, and `port_events`
- ✅ Python ETL scripts that transform raw CSVs into curated and quarantine outputs
- ✅ Automated data quality checks with detailed reporting
- ✅ Idempotent data loading with configurable behavior

### Machine Learning
- ✅ **ML Microservice** (Python/FastAPI) serving delay predictions in real-time
- ✅ Trained Logistic Regression model using booking-time features
- ✅ Feature engineering and automatic extraction from shipment data
- ✅ Model metadata and performance tracking
- ✅ Two prediction endpoints: by shipment ID or direct features

### Infrastructure
- ✅ Docker Compose stack with PostgreSQL, Java API, and Python ML service
- ✅ Multi-stage Docker builds for optimized images
- ✅ Health checks with automatic dependency management
- ✅ Persistent volumes for database
- ✅ Optional data-engineering service for batch processing

**Note**: Ports and port events are loaded into PostgreSQL for persistence, analytics, and model features. They do not have dedicated API endpoints but are used by the prediction service.

## GenAI Assistant

The platform includes a **conversational AI assistant** powered by LangChain and Ollama that provides natural language access to supply chain analytics. Users can ask questions in plain English, and the assistant automatically selects and calls the appropriate tools to answer them.

### Technology Stack

- **LangChain** - Tool calling framework and prompt management
- **Ollama** - Local LLM inference (llama3.2 model)
- **Python 3.11** - Core implementation
- **httpx** - HTTP client for API integration
- **pytest** - Testing framework

### Prerequisites

1. **Ollama installed and running**:
   ```bash
   # Install Ollama (see https://ollama.ai)
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Pull the llama3.2 model
   ollama pull llama3.2
   
   # Verify Ollama is running
   ollama list
   ```

2. **Spring Boot API and ML service running**:
   ```bash
   cd supply-chain-intelligence
   docker compose up -d
   ```

3. **Python dependencies**:
   ```bash
   cd genai-assistant
   pip install -r requirements.txt
   ```

### Running the Assistant

```bash
cd supply-chain-intelligence/genai-assistant
python main.py
```

You'll see a welcome message with example questions:

```
🚢 Supply Chain Intelligence Assistant
--------------------------------------
Ask me about routes, shipments, or delay predictions!

Examples:
  • What is the on-time rate for shipments from Shanghai to Rotterdam?
  • Which routes have had the highest average delay this quarter?
  • What is the delay risk for shipment SHP-00421?

Type 'exit' or 'quit' to end the session.
--------------------------------------
```

### Supported Use Cases

The assistant can answer three types of questions:

#### UC-01: Route Delay Analysis

**Question**: *"Which routes have had the highest average delay in January 2024?"*

**How it works**:
- Calls `query_shipments` tool with date filters
- Aggregates shipments by route (origin → destination)
- Calculates average delay per route
- Returns top routes sorted by delay

**Example interaction**:
```
You: Which routes have had the highest average delay in January 2024?
```

Predicts delay risk (>24 hours late) for a shipment already in the database.

Example:

```bash
curl -X POST http://localhost:8080/predict-delay/shipment/SHP-03038
```

Response:

```json
{
  "prediction": "DELAYED",
  "probability": 0.988,
  "delay_risk_score": 0.988,
  "confidence": "HIGH",
  "model_version": "20260906151259"
}
```

Fields:
- `prediction`: `ON_TIME` or `DELAYED` (>24 hours late)
- `probability`: Confidence in predicted class (0.0 - 1.0)
- `delay_risk_score`: Probability of delay occurring (0.0 - 1.0)
- `confidence`: `LOW` (<0.55), `MEDIUM` (0.55-0.70), `HIGH` (>0.70)
- `model_version`: Model training timestamp

#### Predict Delay from Booking Details

```http
POST /predict-delay
```

Predicts delay risk from raw booking features (useful for "what-if" scenarios).

Example:

```bash
curl -X POST http://localhost:8080/predict-delay \
  -H "Content-Type: application/json" \
  -d '{
    "origin_port": "CNSHA",
    "destination_port": "USLAX",
    "cargo_type": "Electronics",
    "weight_tons": 500.0,
    "container_count": 5,
    "planned_transit_days": 14.0,
    "booking_lead_days": 10.0,
    "booking_month": 9,
    "booking_day_of_week": 1,
    "origin_congestion_score": 7.5,
    "destination_congestion_score": 6.0
  }'
```

Response: Same as above.

#### Check ML Service Health

```http
GET /predict-delay/health
```

Example:

```bash
curl http://localhost:8080/predict-delay/health
```

Response:

```json
{
  "ml_service_status": "UP",
  "endpoint_available": true
}
```

**Architecture**:
- ML Service: Python 3.11 + FastAPI + scikit-learn 1.9.0 (port 5000)
- API Service: Java 17 + Spring Boot 4.1.1 (port 8080)
- Communication: HTTP REST between services
- Orchestration: Docker Compose with health checks

**Model Details**:
- Type: Logistic Regression
- Performance: ROC-AUC 0.4987, F1 0.43, Precision 0.40, Recall 0.46
- Features: Uses only booking-time features (no data leakage)
- Note: Performance is near chance due to limited signal in booking-time features

### Error Shape

Application errors use:

```json
{
  "timestamp": "2024-01-26T10:30:00.000Z",
  "status": 404,
  "error": "Not Found",
  "message": "Shipment not found with id: INVALID-ID",
  "path": "/shipments/INVALID-ID"
}
```

## Testing

Tests use H2 in-memory database and Spring MockMvc.

Run locally with the Maven wrapper:

```bash
sh mvnw clean test
```

If the wrapper is executable in your checkout, this is equivalent:

```bash
./mvnw clean test
```

Run selected test groups:

```bash
sh mvnw test -Dtest=*Test
sh mvnw verify -Dtest=*IntegrationTest
```

Run tests through Docker if Java is not installed locally:

```bash
docker run --rm -v "$(pwd)":/app -w /app maven:3.9-eclipse-temurin-17 mvn test
```

## Docker Notes

The platform uses **multi-container architecture** with three core services:

### Images

1. **API Service** (`Dockerfile`)
   - Multi-stage build: Maven build + JRE runtime
   - Base: `eclipse-temurin:17-jre`
   - Non-root user: `spring`
   - Copies data directories: `data`, `reports`, `curated`, `quarantine`, `data-engineering`
   - Exposes port 8080
   - Health check: `wget --spider http://localhost:8080/health`

2. **ML Service** (`Dockerfile.ml`)
   - Base: `python:3.11-slim`
   - Python dependencies: FastAPI, scikit-learn 1.9.0, pandas, httpx
   - Copies ML code and model files
   - Exposes port 5000
   - Health check: Python httpx request to `/health`

3. **PostgreSQL**
   - Official image: `postgres:16-alpine`
   - Persistent volume for data
   - Init script: `init-db.sql` (creates UUID extension)
   - Health check: `pg_isready`

### Docker Compose Configuration

Services start in dependency order with health checks:

```yaml
postgres:
  healthcheck: pg_isready
  
ml-service:
  depends_on: []  # Independent
  healthcheck: HTTP request to /health
  
api:
  depends_on:
    postgres: service_healthy
    ml-service: service_healthy
  healthcheck: HTTP request to /health
```

All services connected via `supply-chain-network` bridge network for internal communication.

### Common Commands

```bash
# Build and start all services
docker compose up --build -d

# View logs for specific service
docker compose logs -f api          # Java API
docker compose logs -f ml-service   # Python ML service
docker compose logs -f postgres     # Database

# Check service health
docker compose ps

# Restart specific service
docker compose restart ml-service
docker compose restart api

# Rebuild specific service
docker compose up --build -d ml-service

# Stop all services
docker compose down

# Full reset (removes database volume)
docker compose down -v

# View resource usage
docker stats supply-chain-api supply-chain-ml supply-chain-postgres

# Execute commands in containers
docker exec -it supply-chain-api bash
docker exec -it supply-chain-ml python --version
docker exec -it supply-chain-postgres psql -U postgres -d supply_chain
```

## CI/CD

GitHub Actions workflow at `.github/workflows/ci.yml` runs on every push and pull request:

### Pipeline Stages

1. **Lint & Format Check**
   - Java code style validation
   - Maven checkstyle plugin

2. **Unit Tests**
   - Java unit tests with JUnit 5 and Mockito
   - Uses H2 in-memory database
   - Tests: Service layer, specifications, utilities

3. **Integration Tests**
   - Full Spring Boot context with MockMvc
   - HTTP endpoint testing
   - Database integration with test profile

4. **Docker Build**
   - Builds both API and ML service images
   - Validates Dockerfile syntax
   - Tests multi-stage builds

5. **Security Scan**
   - Dependency vulnerability scanning
   - OWASP dependency check
   - Container image scanning

6. **Coverage Report**
   - JaCoCo code coverage
   - Uploads to Codecov (if configured)
   - Minimum threshold: 70%


### Post-Deployment Health Checks

Verify all services after deployment:

```bash
# 1. Check all containers are healthy
docker compose ps

# 2. Test API health
curl http://localhost:8080/health

# 3. Test ML service integration
curl http://localhost:8080/predict-delay/health

# 4. Test endpoints
curl "http://localhost:8080/shipments?size=1"
curl http://localhost:8080/data-quality/report
curl http://localhost:8080/routes/BEANR/USLAX/stats
curl -X POST http://localhost:8080/predict-delay/shipment/SHP-03038

# 5. Check logs
docker logs supply-chain-api --tail 50
docker logs supply-chain-ml --tail 50
```

Verify table counts:

```bash
docker exec supply-chain-postgres psql -U postgres -d supply_chain -c "SELECT COUNT(*) FROM shipments;"
docker exec supply-chain-postgres psql -U postgres -d supply_chain -c "SELECT COUNT(*) FROM ports;"
docker exec supply-chain-postgres psql -U postgres -d supply_chain -c "SELECT COUNT(*) FROM port_events;"
```

### Troubleshooting

**ML Service Not Responding**:
```bash
docker compose logs ml-service --tail=50
curl http://localhost:5000/health  # Direct test
docker compose restart ml-service
```

**Database Connection Issues**:
```bash
docker compose logs postgres --tail=50
docker exec supply-chain-postgres psql -U postgres -d supply_chain -c "SELECT COUNT(*) FROM shipments;"
```

**CSV Data Not Loading**:
- Check `LOAD_CSV_ON_STARTUP`, `SKIP_IF_DATA_EXISTS`, `CSV_PATH`
- Verify curated CSV files exist
- View startup logs: `docker logs supply-chain-api | grep CSV`

### Monitoring

Monitor these key metrics:
- `/health` endpoint status (API and ML)
- Prediction latency and error rates
- Database connection pool usage
- Container resource usage: `docker stats`

### Security Considerations

- Enable HTTPS/TLS for external access
- Keep ML service internal (only API accesses it)
- Use secrets management for credentials

### Model Updates

To update the ML model:

```bash
# 1. Train new model
python ml/train_model.py

# 2. Rebuild ML service
docker compose up --build -d ml-service

# 3. Verify
curl http://localhost:5000/model/info
```

## Skipped Section - 
- Guardrails for LLM due to time crunch

## Data Quality Summary

A standalone, rerunnable data-quality check is performed on the raw shipments.csv before transformation. The source dataset contains *5,028 rows*, and *13 of 23 data-quality checks identified issues*. The full machine-readable results are available in reports/dq_report.json.

| Data Quality Issue | Rows Affected | Handling |
|---|---:|---|
| Exact duplicate rows | 16 | Removed duplicate records during transformation. |
| Duplicate shipment IDs | 56 | Treated as conflicting business-key records and quarantined to avoid ambiguous shipment records. |
| Missing cargo type | 15 | Retained as null rather than inferring an unsupported cargo type; issue is reported for downstream awareness. |
| Missing weight | 73 | Retained as null where no reliable value was available; reported as a completeness issue. |
| Negative weight | 36 | Treated as physically invalid and quarantined. |
| Zero container count | 23 | Flagged as invalid/incomplete booking data and quarantined for review. |
| Missing shipment status | 54 | Retained/flagged rather than guessing a lifecycle status from other fields. |
| Inconsistent status values | 92 | Normalized to a consistent canonical representation where appropriate; unsupported/inconsistent values are flagged. |
| Inconsistent cargo-type formatting | 3,611 | Normalized by trimming whitespace and applying consistent capitalization. |
| Actual departure before booking | 39 | Treated as a chronological inconsistency and quarantined. |
| Missing actual departure | 349 | Retained as null where valid for cancelled or not-yet-departed shipments; reported as an informational issue. |
| Missing actual arrival | 349 | Retained as null where valid for cancelled or in-progress shipments; excluded from calculations that require an actual arrival. |
| Delivered without actual arrival | 28 | Treated as an inconsistent shipment lifecycle record and quarantined/reported for investigation. |

The pipeline follows a *raw → curated → serving* approach. Raw source files are preserved unchanged, valid and standardized records are written to the curated/ layer, and records that cannot be safely corrected are written to quarantine/ rather than silently discarded.

The DQ process also checks shipment identifiers, negative container counts, date parsing, and chronological relationships such as planned arrival before planned departure. These checks reported *zero affected rows* in the supplied dataset but remain part of the reusable DQ pipeline to detect future data-quality regressions.

The complete DQ report, including severity, affected-row percentage, and recommended action for all 23 checks, is generated at: `reports/dq_report.json`

---

## Scaling to Production

This section outlines the roadmap for scaling the platform from a development setup to a production-ready system handling millions of requests.

### Phase 1: Production Readiness (0-10K requests/day)

#### Infrastructure Changes

**1. Container Orchestration - Migrate to Kubernetes**
```yaml
Rationale: Docker Compose → Kubernetes for high availability and auto-scaling

Benefits:
- Auto-scaling based on CPU/memory metrics
- Self-healing (automatic pod restarts)
- Rolling deployments with zero downtime
- Resource limits and quotas
- Service mesh integration (Istio/Linkerd)

Implementation:
- Use Helm charts for service deployment
- Configure Horizontal Pod Autoscaler (HPA)
- Set up Ingress controller (NGINX/Traefik)
- Implement readiness/liveness probes
```

**2. Database Optimization**
```sql
-- Add connection pooling (HikariCP already configured)
-- Optimize for production workload

-- Add indexes for common queries
CREATE INDEX idx_shipments_origin_dest ON shipments(origin_port, destination_port);
CREATE INDEX idx_shipments_booking_date ON shipments(booking_date);
CREATE INDEX idx_shipments_actual_arrival ON shipments(actual_arrival_date);
CREATE INDEX idx_port_events_shipment ON port_events(shipment_id);

-- Enable query performance monitoring
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET pg_stat_statements.track = all;

-- Configure replication for read replicas
-- Primary (writes) + 2 Read Replicas (queries)
```

**3. Caching Layer - Redis**
```yaml
Use Cases:
- Route statistics (TTL: 1 hour)
- Frequently accessed shipment data (TTL: 15 minutes)
- ML prediction results (TTL: 24 hours for same inputs)
- Session storage for future auth

Configuration:
- Redis Cluster for high availability
- Spring Cache abstraction with Redis backend
- Cache-aside pattern for shipment queries
- Write-through for frequently updated data

Code Example:
@Cacheable(value = "routeStats", key = "#origin + '-' + #destination")
public RouteStats getRouteStats(String origin, String destination) {
    // Expensive computation cached for 1 hour
}
```

**4. Load Balancing**
```yaml
API Service:
- Deploy 3+ instances behind ALB/NLB
- Configure health check endpoint: /health
- Session affinity: Not required (stateless API)
- Connection draining: 30 seconds

ML Service:
- Deploy 2+ instances (CPU-intensive)
- Use round-robin load balancing
- Consider GPU instances for deep learning models
- Model warming on startup
```

#### Security Hardening

**1. Authentication & Authorization**
```yaml
Implement:
- JWT-based authentication (Spring Security + OAuth2)
- Role-based access control (RBAC)
  - ADMIN: Full access
  - ANALYST: Read-only + predictions
  - API_CLIENT: Rate-limited access

- API key management for external clients
- OAuth2 integration (Google/Azure AD) for GenAI assistant

Spring Security Config:
@EnableWebSecurity
public class SecurityConfig {
    @Bean
    SecurityFilterChain filterChain(HttpSecurity http) {
        http.authorizeHttpRequests()
            .requestMatchers("/health", "/actuator/health").permitAll()
            .requestMatchers("/predict-delay/**").hasRole("ANALYST")
            .anyRequest().authenticated()
            .and()
            .oauth2ResourceServer().jwt();
    }
}
```

**2. Secrets Management**
```yaml
Replace environment variables with:
- AWS Secrets Manager / Azure Key Vault
- HashiCorp Vault
- Kubernetes Secrets with encryption at rest

Sensitive Data:
- Database passwords
- JWT signing keys
- API keys for external services
- ML model encryption keys
```

**3. Network Security**
```yaml
- Enable HTTPS/TLS (Let's Encrypt + cert-manager)
- Mutual TLS (mTLS) between microservices
- Network policies (deny-all by default)
- WAF (Web Application Firewall) for API gateway
- Rate limiting per client (Spring Cloud Gateway)
- DDoS protection (AWS Shield / Cloudflare)
```

#### Observability & Monitoring

**1. Structured Logging**
```yaml
Current: Console logs → Production: Centralized logging

Stack: ELK (Elasticsearch, Logstash, Kibana) or Grafana Loki

Configuration:
- JSON logging format (already implemented)
- Correlation IDs for request tracing
- Log levels: ERROR/WARN → Alerts, INFO → Analytics
- Retention: 30 days hot, 90 days cold storage

Log Aggregation:
- Application logs → Fluentd → Elasticsearch
- Search and analysis via Kibana dashboards
```

**2. Metrics & Alerting**
```yaml
Stack: Prometheus + Grafana + AlertManager

Metrics to Track:
- Request rate, latency (p50, p95, p99)
- Error rates (4xx, 5xx)
- ML prediction latency and accuracy drift
- Database connection pool usage
- Cache hit/miss rates
- JVM heap usage and GC pauses
- Pod CPU/memory utilization

Alerts:
- Error rate > 5% for 5 minutes
- API latency p95 > 500ms
- ML service unavailable
- Database connection pool exhausted
- Disk usage > 80%

Spring Boot Actuator:
- Expose /actuator/prometheus endpoint
- Configure Micrometer registry
```

**3. Distributed Tracing**
```yaml
Stack: Jaeger or Zipkin with OpenTelemetry

Trace Flow:
GenAI Assistant → API → ML Service → Database

Benefits:
- Identify bottlenecks across services
- Root cause analysis for slow requests
- Service dependency mapping

Implementation:
- Spring Cloud Sleuth (auto-instrumentation)
- Propagate trace context via HTTP headers
- Sample 100% in dev, 10% in production
```

#### CI/CD Pipeline Enhancements

**1. Automated Deployment**
```yaml
Current: Manual Docker builds → GitOps with ArgoCD

Pipeline Stages:
1. Code commit → GitHub Actions triggered
2. Run tests (unit + integration)
3. SonarQube code quality scan (quality gate)
4. Build Docker images (API, ML)
5. Push to container registry (ECR/GCR/ACR)
6. Update Kubernetes manifests in GitOps repo
7. ArgoCD auto-syncs to cluster
8. Run smoke tests
9. Notify Slack/Teams on success/failure

Blue-Green Deployment:
- Deploy new version to "green" environment
- Run automated tests
- Switch traffic from "blue" to "green"
- Keep "blue" for quick rollback
```

**2. Database Migrations**
```yaml
Replace hibernate.ddl-auto=update with Flyway

Benefits:
- Version-controlled schema changes
- Rollback capability
- Audit trail of migrations
- No accidental schema drops

Migration Structure:
/src/main/resources/db/migration/
  V1__initial_schema.sql
  V2__add_shipment_indexes.sql
  V3__add_delay_prediction_table.sql

Flyway auto-runs migrations on startup
```

---

### Phase 2: High-Scale Architecture (10K-1M requests/day)

#### Horizontal Scaling

**1. API Service Auto-Scaling**
```yaml
Kubernetes HPA Configuration:
- Min replicas: 3
- Max replicas: 20
- Target CPU: 70%
- Target memory: 80%
- Scale up: Add 2 pods per cycle
- Scale down: Remove 1 pod per 5 minutes

Geographic Distribution:
- Multi-region deployment (US-East, US-West, EU, Asia)
- Route53/Cloud DNS for geo-routing
- Cross-region database replication
```

**2. ML Service Optimization**
```yaml
Model Serving Strategies:

Option A: Batch Predictions
- Pre-compute predictions for known shipments
- Store in cache (Redis) with 24h TTL
- Serve from cache (sub-millisecond latency)
- Background job refreshes predictions

Option B: Model Quantization
- Convert float32 → int8 (4x smaller, faster)
- Use ONNX Runtime for inference
- Deploy on CPU (cheaper than GPU for logistic regression)

Option C: Async Predictions
- Accept prediction request → Return job ID
- Process in background queue (RabbitMQ/Kafka)
- Client polls for result or webhook callback
```

**3. Database Scaling**
```yaml
Read/Write Splitting:
- Primary DB: All writes + critical reads
- Read Replicas (2-3): Analytical queries, reports
- Spring Boot config:
    @Transactional(readOnly = true) → Route to replica
    @Transactional → Route to primary

Partitioning Strategy:
- Partition shipments table by booking_date (monthly)
- Archive old data to cold storage (S3 + Athena)
- Keep last 12 months in hot storage

Connection Pooling:
- HikariCP: max-pool-size=20 per instance
- PgBouncer for connection pooling (1000s → 100)

Query Optimization:
- Use EXPLAIN ANALYZE for slow queries
- Add partial indexes for filtered queries
- Materialized views for complex aggregations
```

#### Event-Driven Architecture

**1. Migrate to Async Communication**
```yaml
Use Case: Real-time shipment updates

Current: Synchronous REST
Future: Event streaming with Kafka

Events:
- ShipmentBookedEvent
- DelayPredictionRequestedEvent
- PortEventRecordedEvent
- RouteStatsUpdatedEvent

Benefits:
- Decouple services (loose coupling)
- Handle traffic spikes (backpressure)
- Event replay for debugging
- Multiple consumers for same event

Example Flow:
API publishes ShipmentBookedEvent → Kafka
├─> ML Service: Generate delay prediction
├─> Analytics Service: Update dashboards
└─> Notification Service: Alert stakeholders
```

**2. CQRS Pattern**
```yaml
Command Query Responsibility Segregation

Write Model (Commands):
- POST /shipments → PostgreSQL (normalized)
- Strong consistency, ACID transactions

Read Model (Queries):
- GET /shipments?filters → Elasticsearch (denormalized)
- Eventually consistent, optimized for search
- Full-text search, faceted filtering

Sync Mechanism:
- CDC (Change Data Capture) via Debezium
- PostgreSQL → Kafka → Elasticsearch
- Near real-time replication (<1 second lag)
```

#### Advanced ML Capabilities

**1. Model Versioning & A/B Testing**
```yaml
ML Flow Integration:
- Track model versions with metadata
- Compare model performance across versions
- Gradual rollout (5% → 25% → 50% → 100%)

A/B Testing:
- Split traffic: 90% model v1.0, 10% model v2.0
- Compare metrics (accuracy, latency, business KPIs)
- Automated rollback if metrics degrade

Feature Store:
- Centralize feature engineering (Feast/Tecton)
- Consistent features for training and serving
- Real-time and batch feature computation
```

**2. Model Monitoring & Retraining**
```yaml
Drift Detection:
- Monitor input distribution shifts
- Track prediction confidence over time
- Alert if accuracy drops below threshold

Automated Retraining:
- Schedule: Weekly or when drift detected
- Pipeline: Airflow DAG
  1. Extract new data from PostgreSQL
  2. Feature engineering
  3. Train model
  4. Evaluate on hold-out set
  5. If improved → Deploy via MLflow
  6. If not → Alert data scientists

Online Learning:
- Incremental model updates with new data
- Feedback loop: Actual vs predicted delays
```

---

### Phase 3: Enterprise-Scale (1M+ requests/day)

#### Multi-Tenancy

**1. Tenant Isolation**
```yaml
Strategies:
- Database per tenant (high isolation, high cost)
- Schema per tenant (medium isolation, medium cost)
- Row-level security (shared tables, low cost) ✓

Implementation:
- Add tenant_id column to all tables
- Spring Boot filter injects tenant context
- PostgreSQL RLS policies enforce isolation

CREATE POLICY tenant_isolation ON shipments
  USING (tenant_id = current_setting('app.current_tenant')::UUID);
```

**2. Resource Quotas**
```yaml
Per-Tenant Limits:
- API rate limits (1000 req/min for free, 10K for premium)
- Storage quotas (1GB data per tenant)
- ML predictions (100/day free, unlimited premium)
- Concurrent connections

Enforcement:
- API Gateway (Kong/Apigee) for rate limiting
- Custom Spring Boot interceptor for quotas
- PostgreSQL table storage monitoring
```

#### Global Distribution

**1. Multi-Region Deployment**
```yaml
Regions: US-East, US-West, EU-Central, Asia-Pacific

Architecture:
- Active-Active: All regions serve traffic
- GeoDNS routes users to nearest region
- Database: Multi-region replication (PostgreSQL + Patroni)
- Cache: Redis cluster with cross-region replication
- Storage: S3 multi-region buckets

Consistency:
- Eventual consistency for reads (acceptable for analytics)
- Strong consistency for writes (leader-based)
```

**2. CDN for Static Assets**
```yaml
Use Cases:
- API documentation (Swagger UI)
- GenAI assistant web interface (future)
- Data quality reports (JSON/PDF)

CDN: CloudFront / CloudFlare / Fastly
- Cache static content at edge
- Reduce latency for global users
- DDoS protection
```

#### Cost Optimization

**1. Resource Right-Sizing**
```yaml
Current Dev Setup:
- API: 512MB RAM, 0.5 CPU
- ML: 1GB RAM, 1 CPU
- DB: 2GB RAM, 1 CPU

Production Optimized:
- API: 2GB RAM, 2 CPU (3 instances)
- ML: 4GB RAM, 2 CPU (2 instances) + auto-scale
- DB: 8GB RAM, 4 CPU + read replicas

Tools:
- Kubernetes Vertical Pod Autoscaler (VPA)
- AWS Compute Optimizer
- Rightsizing recommendations from monitoring
```

**2. Cost Monitoring**
```yaml
Track:
- Compute costs (EC2/EKS instances)
- Database costs (RDS/Aurora)
- Storage costs (S3, EBS volumes)
- Network egress costs
- Third-party API costs (if using external LLM)

Optimization:
- Use spot instances for non-critical workloads
- Archive old data to Glacier (90+ days)
- Compress logs before storage
- Use reserved instances for predictable workload
- Implement data lifecycle policies
```

---

### Technology Upgrades for Scale

| Component | Current | Production | Reason |
|-----------|---------|------------|--------|
| Orchestration | Docker Compose | Kubernetes | Auto-scaling, HA |
| API Gateway | None | Kong/AWS ALB | Auth, rate limiting, routing |
| Cache | None | Redis Cluster | Reduce DB load |
| Message Queue | None | Kafka/RabbitMQ | Async processing |
| Search | PostgreSQL | Elasticsearch | Full-text search |
| Monitoring | Logs | Prometheus + Grafana | Metrics, dashboards |
| Tracing | None | Jaeger/Zipkin | Distributed tracing |
| Service Mesh | None | Istio/Linkerd | Traffic mgmt, security |
| Database | PostgreSQL | PostgreSQL + Replicas | Read scaling |
| ML Serving | FastAPI | TensorFlow Serving / Seldon | Model versioning, A/B testing |
| CI/CD | GitHub Actions | GitHub Actions + ArgoCD | GitOps, declarative |

---

### Key Metrics to Track

**Business Metrics:**
- Total shipments tracked
- Predictions served per day
- Prediction accuracy vs actual delays
- User adoption (GenAI queries/day)

**Technical Metrics:**
- API latency: p50, p95, p99
- Error rate: 4xx (client), 5xx (server)
- Throughput: requests per second
- Availability: 99.9% SLA (8.76 hours downtime/year)

**Operational Metrics:**
- Deployment frequency (daily/weekly)
- Mean time to recovery (MTTR < 30 min)
- Change failure rate (<5%)
- Lead time for changes (<1 day)

---

## What would I improve?
- Train a more accurate model for delay prediction.
  - Model comparision Logistic Regression vs Random Forest
- Focus towards scaling the Application.
- Would increase the usecase for genai cli tool.