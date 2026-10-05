# Iran-carbon-black
## Comprehensive Proposal for Implementing Artificial Intelligence at Iran Carbon Company

---

## Infrastructure setup (Phase 1)

An on-premise microservices-based platform per SRS domain 6.

### Prerequisites
- Docker Desktop / Docker Compose
- Python 3.11+ (optional, for the seed script)

### Quick start

```powershell
.\scripts\bootstrap.ps1
```

Or:

```powershell
Copy-Item .env.example .env
docker compose up -d --build
```

### Access points

| Service | Address |
|:---|:---|
| **Online dashboard** | http://localhost:8080 |
| API Gateway | http://localhost:8080/api/... |
| Auth | http://localhost:8001/docs |
| Ingestion | http://localhost:8002/docs |
| Energy | http://localhost:8003/docs |
| Supply | http://localhost:8004/docs |
| Quality | http://localhost:8005/docs |
| Sales | http://localhost:8006/docs |
| Finance | http://localhost:8007/docs |
| Demand | http://localhost:8008/docs |
| Integration / ERP | http://localhost:8009/docs |
| Training | http://localhost:8010/docs |
| Ops / SLA | http://localhost:8011/docs |
| Maturity / MLOps | http://localhost:8012/docs |
| Grafana | http://localhost:3000 |
| MinIO Console | http://localhost:9001 |
| Prometheus | http://localhost:9090 |
| MQTT | localhost:1883 |

### Web dashboard (SPA)

The Persian RTL dashboard is served at the gateway root and retrieves operational data from the Phase 1–5 APIs.

```powershell
# Local development (Vite on :5173 with a proxy to :8080)
cd web
npm install
npm run dev

# or only build the dashboard image inside the stack
docker compose up -d --build dashboard gateway
```

Tabs: Executive view · Energy · Quality · Demand/Production · Sales/Finance · Maturity/MLOps
The portal refreshes automatically every 60 seconds.

Default user: `admin` / `Admin@ChangeMe1` — change the passwords in `.env` before a real environment.

### Running the dashboard offline in VS Code

Full guide: [docs/OFFLINE_DASHBOARD.fa.md](docs/OFFLINE_DASHBOARD.fa.md)

**Saving and running without internet:**

```powershell
.\scripts\offline-save.ps1    # once: build the SPA → offline/dashboard
.\scripts\offline-run.ps1     # every offline run: local Docker + UI on :5173
```

Development with Hot Reload:

```powershell
.\scripts\dev-dashboard.ps1
# → http://127.0.0.1:5173
```

In VS Code: Task **ICB: Offline run** or **ICB: Live dashboard**.

Sample synthetic data:

```powershell
python scripts/seed_synthetic.py
```

## Phase 5 — Product maturity, MLOps and competitive advantage

### Capabilities
- Model registry + retraining (weekly in prod / hourly in dev) and publication to MinIO
- Promoting a model version to production (`/models/{domain}/{version}/promote`)
- Inventory optimization and reducing excess inventory
- High-margin / specialty grade portfolio
- Benefit tracking toward the annual target of **200 billion rials** and a payback of about 24 months
- Grafana dashboard: Phase 5 — Maturity, MLOps & ROI

### Key APIs

```http
GET  /api/v1/maturity/models
POST /api/v1/maturity/retrain
POST /api/v1/maturity/models/{domain}/{version}/promote
POST /api/v1/maturity/inventory/optimize
GET  /api/v1/maturity/portfolio
POST /api/v1/maturity/portfolio/recommend-mix
POST /api/v1/maturity/roi/snapshot
GET  /api/v1/maturity/dashboard
```

```powershell
python scripts\phase5_smoke.py
```

Maturity docs: http://localhost:8012/docs

---

## Phase 4 — Production deployment, security, backup and training

### Capabilities
- Auth hardening: account lockout, password policy, enforced 2FA in production, security events
- Rate limit + Security headers + hiding `/docs` in prod
- OT / IT / DMZ zoning (`GET /api/v1/ops/zones`)
- Backup/restore with a target of RPO≤1h and RTO≤2h (`scripts/backup.ps1`, `scripts/restore.ps1`)
- Training and change management service for rolling out to 350+ people
- Live SLA monitoring + Prometheus alert
- Production overlay: `docker-compose.prod.yml`

### Key APIs

```http
POST /api/v1/auth/login
POST /api/v1/auth/password/change
POST /api/v1/auth/2fa/setup
GET  /api/v1/ops/status
GET  /api/v1/ops/sla
GET  /api/v1/ops/zones
POST /api/v1/ops/backups/report
GET  /api/v1/training/courses
POST /api/v1/training/enroll
GET  /api/v1/training/compliance
POST /api/v1/training/surveys
```

### Production

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
.\scripts\backup.ps1
python scripts\phase4_smoke.py
```

Grafana: **Phase 4 — Security, SLA & Training**

---

## Phase 3 — Sales, finance and ERP integration

### Capabilities
- Sales forecasting and pricing `sales-gbr-v1` (target ≥ 85%)
- Lightweight CRM of key customers + customers at risk of churn
- Cash flow forecasting `finance-gbr-v1` (target ≥ 80%)
- Financial ratio analysis and board dashboard (`/finance/dashboard`)
- ERP integration gateway on `/api/v1/erp/*`
- Grafana dashboard: Phase 3 — Sales, Finance & ERP

### Key APIs

```http
POST /api/v1/sales/forecast
POST /api/v1/sales/pricing/recommend
GET  /api/v1/sales/crm/at-risk
GET  /api/v1/sales/customers/{id}
POST /api/v1/finance/cashflow/forecast
GET  /api/v1/finance/ratios/analyze
GET  /api/v1/finance/dashboard
POST /api/v1/erp/sales/orders
POST /api/v1/erp/finance/journal
GET  /api/v1/erp/export/sales-forecasts
GET  /api/v1/erp/openapi-contract
```

```powershell
$env:PYTHONPATH="."
python -m ml.sales.train_forecast
python -m ml.finance.train_cashflow
python scripts\phase3_smoke.py
```

Integration docs: http://localhost:8009/docs

---

## Phase 2 — Quality, demand and supply chain

### Capabilities
- Quality anomaly model `quality-anomaly-rf-v1` (target ≥ 95%)
- Furnace/reactor process parameter optimization (`/process/optimize`)
- Demand forecasting of 12 grades with 1/3/6-month horizons (`demand-gbr-v1`)
- Production planning + grade recommender
- Raw material price forecasting and purchase timing suggestion (`supply-price-gbr-v1`)
- Quality MQTT: `icb/quality/+/process`
- Grafana dashboard: Phase 2 — Quality, Demand & Supply

### Key APIs

```http
POST /api/v1/quality/anomaly/check
POST /api/v1/quality/process/optimize
POST /api/v1/demand/forecast
POST /api/v1/demand/forecast/all
POST /api/v1/demand/production/plan
POST /api/v1/demand/recommend-grade
POST /api/v1/supply/purchase/advice
POST /api/v1/supply/tenders/score
```

```powershell
$env:PYTHONPATH="."
python -m ml.quality.train_anomaly
python -m ml.demand.train_forecast
python -m ml.supply.train_price
python scripts\phase2_smoke.py
```

---

## Phase 1 — Energy and predictive maintenance pilot

### Capabilities
- MQTT worker on Ingestion (`icb/energy/+/sensors` and `.../consumption`)
- Edge OT simulator (`edge-simulator`) for generating live pilot data
- Real RUL model (`rul-gbr-v1`) with a 3-day alert threshold (PM-02 / PM-03)
- Decision between grid power and generator based on peak tariff (PM-04)
- Grafana dashboard: Phase 1 — Energy & Predictive Maintenance

### Phase 1 key APIs

```http
POST /api/v1/energy/rul/predict
POST /api/v1/energy/rul/scan
GET  /api/v1/energy/alerts
POST /api/v1/energy/source/decide
GET  /api/v1/energy/consumption/summary
GET  /api/v1/ingestion/topics
```

Model retraining:

```powershell
$env:PYTHONPATH="."
python -m ml.energy.train_rul
```

---

### Integration of seven process domains with a digital transformation and smart manufacturing approach

---

### 1. Executive Summary

Iran Carbon Company, with the ticker "Shekarbon" on the Tehran Stock Exchange, faces serious operational and financial challenges: a 29 percent drop in monthly sales, frequent suspension of the trading symbol, high energy costs (with frequent power outages and generator rental), and severe volatility in raw material prices, which make up 85% of the cost of goods sold.

This proposal presents a **comprehensive program for implementing artificial intelligence in seven key domains** which also covers the new domain of **"demand-driven smart carbon black production"**. According to global reports, the carbon black market is transitioning from commodity production toward performance- and sustainability-based production, and artificial intelligence plays a key role in this industry as a practical enabler in production, quality control, logistics and support for customers' formulation .

---

### 2. Project domains and itemized costs

#### Domain 1: Energy and utilities management

| Sub-project | Description | Estimated cost (billion rials) |
|:---|:---|:---|
| **Predictive maintenance** | Installing IoT sensors on generators, compressors, furnaces and vertical coolers (38 m height) using a layered sensing architecture, edge computing and AI modeling  | 25 |
| **Energy consumption optimization** | An energy price and peak consumption time forecasting model for deciding between grid power and generator | 10 |
| **Domain 1 subtotal** | **Total** | **35** |

#### Domain 2: Supply chain and procurement

| Sub-project | Description | Estimated cost (billion rials) |
|:---|:---|:---|
| **Purchasing and supply optimization** | Analyzing supplier data, exchange rate and global prices to suggest the best time to purchase coal tar and furfural extract | 8 |
| **Smart tender management** | Analysis and optimal selection in tenders for purchasing supplies | 4 |
| **Domain 2 subtotal** | **Total** | **12** |

#### Domain 3: Production and quality control

| Sub-project | Description | Estimated cost (billion rials) |
|:---|:---|:---|
| **Real-time quality control with machine vision** | Real-time quality monitoring of 12 carbon black grades using DCS system data and smart cameras  | 15 |
| **Waste reduction and process optimization** | Analysis of furnace and reactor data to reduce the energy consumption coefficient and reduce the production of off-spec products  | 10 |
| **Domain 3 subtotal** | **Total** | **25** |

#### Domain 4: Sales and marketing

| Sub-project | Description | Estimated cost (billion rials) |
|:---|:---|:---|
| **Sales forecasting and market management** | Analysis of monthly sales data and economic indicators to optimize pricing strategy in domestic and export markets | 7 |
| **Smart customer management** | Analysis of the needs of key customers (domestic and international tire makers) | 3 |
| **Domain 4 subtotal** | **Total** | **10** |

#### Domain 5: Finance and reporting

| Sub-project | Description | Estimated cost (billion rials) |
|:---|:---|:---|
| **Financial analysis and forecasting** | Clarifying financial ratios, forecasting profitability and improving investor confidence | 5 |
| **Smart management dashboard** | Integrating financial, operational and sales information in a real-time dashboard | 4 |
| **Domain 5 subtotal** | **Total** | **9** |

#### Domain 6: Integration and infrastructure

| Sub-project | Description | Estimated cost (billion rials) |
|:---|:---|:---|
| **Central data lake** | Creating an integrated data repository from all sensors, the DCS system, the financial system and sales | 12 |
| **Security and technical infrastructure** | Local servers (given internet outages), backup and cybersecurity | 8 |
| **Training and organizational culture change** | Training personnel (more than 350 people) on the application of AI in industry | 5 |
| **Domain 6 subtotal** | **Total** | **25** |

#### Domain 7: Demand-driven smart manufacturing (NEW)

| Sub-project | Description | Estimated cost (billion rials) |
|:---|:---|:---|
| **Demand forecasting system** | Developing machine learning algorithms to analyze the market and accurately forecast customers' needs by carbon black grade (more than 12 grades) using historical sales data, economic indicators and downstream industry trends (tire, rubber, paint, cable)  | 12 |
| **Production planning optimization** | Integrating demand forecasting with the production planning system to reduce waste, optimally manage inventory and respond faster to downstream industries' needs  | 8 |
| **Grade recommender system** | Developing an AI model to suggest the appropriate grade to customers based on their specific needs (conductivity, dispersion, color strength, etc.) which, using machine learning, can shorten formulation cycles for specific performance  | 5 |
| **Domain 7 subtotal** | **Total** | **25** |

---

### 3. Summary of capital expenditures (CAPEX)

| Domain | Cost (billion rials) |
|:---|:---|
| Domain 1: Energy and utilities management | 35 |
| Domain 2: Supply chain and procurement | 12 |
| Domain 3: Production and quality control | 25 |
| Domain 4: Sales and marketing | 10 |
| Domain 5: Finance and reporting | 9 |
| Domain 6: Integration and infrastructure | 25 |
| Domain 7: Demand-driven smart manufacturing | 25 |
| **Total initial investment** | **141 billion rials** |

---

### 4. Annual operating costs (OPEX)

| No. | Cost items | Estimated annual cost (billion rials) |
|:---|:---|:---|
| 1 | Technical maintenance and support of the systems (seven domains) | 15 |
| 2 | Infrastructure running costs (electricity, internet, cloud space) | 6 |
| 3 | Internal support team (3 data specialists + 2 instrumentation engineers) | 15 |
| **Total annual operating costs** | **36 billion rials** ||

---

### 5. Implementation timeline (Timeline)

| Phase | Domains covered | Duration (months) |
|:---|:---|:---|
| **Phase 1: Infrastructure** | Domain 6 (data lake, server, security) | 4 months |
| **Phase 2: Data and modeling** | Domains 1, 2, 3 and 7 (data collection, model training) | 7 months |
| **Phase 3: Integration** | Domains 4 and 5 (connection to the financial and sales systems) | 3 months |
| **Phase 4: Deployment and training** | All domains (personnel training and operation) | 2 months |

**Total implementation duration: 16 months**

---

### 6. Required expertise (Required Expertise)

| Expertise | Count | Responsibilities |
|:---|:---|:---|
| **Chief Digital Transformation Officer (CDO)** | 1 person | Overall project management, coordination among domains and reporting to the CEO |
| **Data Engineer** | 2 people | Setting up the data lake, managing data flow from sensors, DCS and financial systems |
| **Data scientist / machine learning specialist** | 3 people | Developing prediction models for all seven domains (including demand forecasting and production optimization models) |
| **Instrumentation and automation engineer** | 2 people | Installing sensors, connecting to the DCS system and integrating with PLCs |
| **Maintenance expert** | 1 person | Cooperating in defining equipment failure scenarios |
| **Finance and commerce expert** | 1 person | Cooperating in designing financial and market forecasting models |
| **Production and planning expert** | 1 person | Cooperating in designing the demand forecasting and production optimization model |
| **Project manager (PM)** | 1 person | Team coordination, budget and schedule management |
| **Organizational change and development consultant** | 1 person | Managing resistance to change and training employees |

---

### 7. Financial analysis (Financial Analysis)

#### Baseline assumptions:
- Discount rate (WACC): 25% (considering economic risks and the inflation rate in Iran)
- Analysis horizon: 5 years
- Annual growth of the carbon black market: about 3.6% to 5.3% globally

#### Estimated annual benefits (after full maturity):

| No. | Source of savings | Annual estimate (billion rials) |
|:---|:---|:---|
| 1 | Reduction of emergency repair costs (30%)  | 35 |
| 2 | Reduced energy consumption and optimized choice of power source | 40 |
| 3 | Reduced production waste and increased quality (reduced production of off-spec products)  | 30 |
| 4 | Increased revenue through optimized pricing and sales | 40 |
| 5 | Reduced procurement costs through purchase optimization | 20 |
| 6 | Increased revenue through demand-driven smart manufacturing (reduced excess inventory, faster response, production of higher-margin grades)  | 35 |
| **Total annual benefits** | **200 billion rials** ||

#### Cash flow and NPV and IRR calculations:

| Year | Benefits (billion rials) | Costs (billion rials) | Net cash flow (billion rials) | Discounted cash flow (25%) |
|:---|:---|:---|:---|:---|
| 0 (investment) | - | -141 | -141 | -141 |
| Year 1 (35% operation) | 70 | 36 | 34 | 27.2 |
| Year 2 (65% operation) | 130 | 36 | 94 | 60.2 |
| Year 3 (full operation) | 200 | 36 | 164 | 83.9 |
| Year 4 (full operation) | 200 | 36 | 164 | 67.2 |
| Year 5 (full operation) | 200 | 36 | 164 | 53.7 |

#### Financial results:
- **NPV (net present value):** about **151 billion rials** (strongly positive and justifiable)
- **IRR (internal rate of return):** about **88%** (far above the 25% discount rate)
- **Payback period:** about **2 years**

---

### 8. Time to product maturity (Time to Maturity)

| Indicator | Duration |
|:---|:---|
| Technical maturity of prediction models (domains 1, 2, 3 and 7) | After 9 months |
| Full operational maturity of all domains | After 16 months |
| Payback | About 24 months (2 years) |

---

### 9. Risks and management solutions

| Risk | Probability | Mitigation |
|:---|:---|:---|
| Low quality of historical data for model training | Medium | Using semi-supervised learning methods and generating synthetic data |
| Personnel resistance to the new system | Medium | Comprehensive training and team participation in the design  |
| Exchange rate volatility and increased equipment costs | High | Procuring domestic equipment as far as possible |
| Power and internet outages | High | Implementing the system locally (On-Premise) with offline backup |
| Unexpected market and demand changes | Medium | Using machine learning models with continuous update capability  |

---

### 10. Conclusion and recommendation

The integrated AI project in seven key domains of Iran Carbon Company, with an investment of 141 billion rials, while returning the investment in about 2 years, can generate more than 200 billion rials per year in savings and increased revenue.

**It is recommended that:**
1. The project start with a **pilot phase in the energy and maintenance domain** (faster payback).
2. Domain 7 (demand-driven smart manufacturing) be developed as a **strategic competitive advantage** alongside the other domains to move the company from commodity production toward smart, market-responsive manufacturing.
3. Concurrently with project execution, a **comprehensive training and cultural change program** be run for more than 350 personnel.
4. Given the successful experience of leading carbon black companies such as Birla Carbon and Linyuan Advanced in using AI , domestic capacity and cooperation with knowledge-based companies be used for implementation.

---

## Appendix: System Requirements Specification (SRS)

### 1. Introduction

#### 1-1 Purpose
The purpose of this document is to precisely specify the requirements of the integrated AI system for Iran Carbon Company in seven key domains.

#### 1-2 System scope
The system includes collecting data from IoT sensors, the DCS system, the financial and sales system, and delivering analytical and predictive outputs to managers and operators. The new system also includes a demand forecasting and production planning optimization module.

#### 1-3 Definitions and abbreviations
- **RUL:** Remaining Useful Life
- **CMMS:** Computerized Maintenance Management System
- **DCS:** Distributed Control System
- **IoT:** Internet of Things
- **MPC:** Model Predictive Control

---

### 2. General system requirements

#### 2-1 Platform and architecture
- The system shall be implemented **on-premise (On-Premise)** with offline backup capability.
- Architecture based on **Microservices** for independent development and deployment of each domain.
- Support for **Real-time Data Processing** with a delay of less than 500 milliseconds .

#### 2-2 Security
- Two-factor authentication (2FA) for all users.
- Encryption of data at rest and in transit.
- Operational data (OT) must remain in the local environment and follow a security architecture based on zoning .

---

### 3. Requirements of the seven domains

#### 3-1 Energy and utilities management domain
**Functional requirements:**

| ID | Requirement | Priority |
|:---|:---|:---|
| PM-01 | Collecting data from vibration, temperature, pressure and current sensors on key equipment  | High |
| PM-02 | Calculating RUL for each equipment with an accuracy of at least 90% | High |
| PM-03 | Issuing an automatic alert at least 3 days before the predicted failure | High |
| PM-04 | Forecasting grid electricity prices and generator cost for optimal decision-making | Medium |
| PM-05 | Providing a real-time energy consumption dashboard by production line | Medium |

**Non-functional requirements:**
- RUL prediction accuracy ≥ 90%
- Prediction delay ≤ 1 second
- Retaining historical data for at least 5 years

---

#### 3-2 Supply chain and procurement domain
**Functional requirements:**

| ID | Requirement | Priority |
|:---|:---|:---|
| SC-01 | Analyzing supplier data and ranking them | High |
| SC-02 | Forecasting raw material prices based on the exchange rate and global prices | High |
| SC-03 | Suggesting the best time and quantity to purchase to reduce costs | Medium |
| SC-04 | Analyzing and ranking purchase tenders | Medium |
| SC-05 | Integration with the existing warehouse system | Low |

**Non-functional requirements:**
- Price prediction accuracy ≥ 85% over a 3-month horizon
- Data updated at least daily

---

#### 3-3 Production and quality control domain
**Functional requirements:**

| ID | Requirement | Priority |
|:---|:---|:---|
| QC-01 | Real-time quality monitoring of 12 carbon black grades using machine vision and DCS data  | High |
| QC-02 | Detecting production process anomalies and issuing alerts | High |
| QC-03 | Predicting the final product quality before the end of the process using neural networks  | High |
| QC-04 | Analyzing furnace and reactor data to predict carbon black emissions  | Medium |
| QC-05 | Providing recommendations to optimize process parameters | Medium |

**Non-functional requirements:**
- Anomaly detection accuracy ≥ 95%
- Analysis delay ≤ 100 milliseconds
- Ability to connect to the DCS system via OPC-UA

---

#### 3-4 Sales and marketing domain
**Functional requirements:**

| ID | Requirement | Priority |
|:---|:---|:---|
| SM-01 | Monthly sales forecasting with an accuracy of ≥ 85% | High |
| SM-02 | Market analysis and suggesting optimal pricing for domestic and export markets | High |
| SM-03 | Analyzing the needs of key customers | Medium |
| SM-04 | Identifying new market opportunities for different carbon black grades | Medium |
| SM-05 | Integration with the existing sales system | Low |

**Non-functional requirements:**
- Sales forecast accuracy ≥ 85%
- Market data updated weekly

---

#### 3-5 Finance and reporting domain
**Functional requirements:**

| ID | Requirement | Priority |
|:---|:---|:---|
| FI-01 | Forecasting profitability and cash flow with an accuracy of ≥ 80% | High |
| FI-02 | Analyzing financial ratios and identifying improvement points | High |
| FI-03 | Providing an integrated management dashboard | High |
| FI-04 | Clarifying costs by production line and grade | Medium |
| FI-05 | Forecasting liquidity needs for financial planning | Medium |

**Non-functional requirements:**
- Dashboard updated in real time
- Ability to issue standard financial and operational reports

---

#### 3-6 Integration and infrastructure domain
**Functional requirements:**

| ID | Requirement | Priority |
|:---|:---|:---|
| IN-01 | Creating an integrated central data lake from all sensors, the DCS system and the financial and sales systems | High |
| IN-02 | Implementing an integrated log management and monitoring system | High |
| IN-03 | Providing a virtual training platform for employees | Medium |
| IN-04 | Implementing a change management system and user adoption assessment | Medium |
| IN-05 | Creating a standard API for connecting to future systems | Low |

**Non-functional requirements:**
- System availability ≥ 99.9%
- RTO (Recovery Time Objective) ≤ 2 hours
- RPO (Recovery Point Objective) ≤ 1 hour

---

#### 3-7 Demand-driven smart manufacturing domain (NEW)
**Functional requirements:**

| ID | Requirement | Priority |
|:---|:---|:---|
| DM-01 | Developing a machine learning model to forecast the demand for each carbon black grade with 1, 3 and 6-month horizons based on historical sales data, economic indicators and downstream industry trends  | High |
| DM-02 | Analyzing demand sensitivity to economic factors (exchange rate, global oil price, inflation rate) | High |
| DM-03 | Integrating demand forecasting with the production planning system (ERP) to optimize the production volume of each grade | High |
| DM-04 | Developing a recommender system to suggest the appropriate grade to customers based on functional needs (conductivity, dispersion, color strength, etc.) using machine learning to shorten formulation cycles  | Medium |
| DM-05 | Providing a market and demand analysis dashboard with the ability to simulate different scenarios | Medium |
| DM-06 | Suggesting the production of specific grades with higher profit margins based on market analysis  | Medium |

**Non-functional requirements:**
- Demand forecast accuracy ≥ 80% over a 3-month horizon
- Models updated weekly with new data
- Ability to connect to external databases (economic indicators, global prices)

---

### 4. Synthetic Data

#### 4-1 Maintenance and repair domain data

```json
{
  "equipment_id": "GEN-001",
  "timestamp": "2026-07-16T08:00:00Z",
  "sensors": {
    "vibration_x": 2.34,
    "vibration_y": 1.87,
    "vibration_z": 3.12,
    "temperature": 78.5,
    "pressure": 12.3,
    "current_draw": 145.2,
    "oil_pressure": 4.8,
    "coolant_temp": 65.2
  },
  "operational_status": "running",
  "maintenance_history": [
    {
      "date": "2026-06-15",
      "type": "preventive",
      "duration_hours": 4,
      "cost_irr": 150000000
    }
  ],
  "target": {
    "remaining_useful_life_days": 45,
    "failure_probability": 0.12
  }
}
```

#### 4-2 Production and quality control domain data

```json
{
  "batch_id": "CB-2026-07-16-0042",
  "production_line": 1,
  "timestamp": "2026-07-16T08:00:00Z",
  "process_parameters": {
    "reactor_temp": 1425.3,
    "feed_rate": 2.45,
    "air_flow": 18.7,
    "residence_time": 2.3,
    "pressure": 1.45,
    "oil_to_air_ratio": 0.78
  },
  "quality_metrics": {
    "iodine_absorption": 82.5,
    "DBP_absorption": 115.3,
    "surface_area": 78.2,
    "particle_size": 22.5,
    "tint_strength": 118.7
  },
  "grade": "N220",
  "target_grade_quality": {
    "iodine_absorption": [80, 85],
    "DBP_absorption": [110, 120],
    "surface_area": [75, 82]
  }
}
```

#### 4-3 Sales and market domain data

```json
{
  "sale_date": "2026-07-15",
  "product": {
    "grade": "N330",
    "quantity_kg": 24500,
    "unit_price_irr": 185000,
    "total_price_irr": 4532500000
  },
  "customer": {
    "id": "CUST-0047",
    "name": "Sahand Tire",
    "segment": "tire_manufacturer",
    "industry": "tire",
    "annual_consumption_kg": 180000
  },
  "region": "domestic",
  "economic_indicators": {
    "usd_irr_rate": 245000,
    "crude_oil_price_usd": 78.5,
    "inflation_rate": 35.2,
    "tire_production_index": 112.5
  }
}
```

#### 4-4 Demand-driven smart manufacturing domain data (NEW)

```json
{
  "forecast_date": "2026-07-16",
  "product_grade": "N220",
  "forecast_period": "3_months",
  "forecast_quantity_kg": 185000,
  "confidence_interval": {
    "lower": 165000,
    "upper": 205000,
    "confidence_level": 0.90
  },
  "historical_demand": [
    {"month": "2026-01", "quantity": 165000},
    {"month": "2026-02", "quantity": 172000},
    {"month": "2026-03", "quantity": 168000},
    {"month": "2026-04", "quantity": 175000},
    {"month": "2026-05", "quantity": 180000},
    {"month": "2026-06", "quantity": 178000}
  ],
  "influencing_factors": {
    "tire_industry_growth": 0.045,
    "crude_oil_price_trend": "increasing",
    "exchange_rate_volatility": 0.12,
    "seasonal_factor": 0.95,
    "market_share_change": 0.02
  },
  "recommended_production": {
    "quantity_kg": 182000,
    "safety_stock_kg": 15000,
    "production_line": "Line_3",
    "start_date": "2026-08-01"
  }
}
```

#### 4-5 Supply chain domain data

```json
{
  "purchase_order": "PO-2026-07-16-003",
  "material": "Coal tar (furfural extract)",
  "supplier": {
    "id": "SUP-0012",
    "name": "Tabriz Petrochemical",
    "rating": 4.2,
    "delivery_reliability": 0.92,
    "quality_rating": 4.5
  },
  "quantity_kg": 32000,
  "unit_price_irr": 42500,
  "total_price_irr": 1360000000,
  "delivery_date": "2026-07-25",
  "market_benchmark": {
    "global_price_usd_ton": 215,
    "exchange_rate": 245000,
    "price_trend": "increasing"
  },
  "historical_price_trend": [
    {"month": "2026-01", "price": 38000},
    {"month": "2026-02", "price": 39500},
    {"month": "2026-03", "price": 41000},
    {"month": "2026-04", "price": 40500},
    {"month": "2026-05", "price": 41800},
    {"month": "2026-06", "price": 42500}
  ]
}
```

#### 4-6 Finance and reporting domain data

```json
{
  "report_date": "2026-07-16",
  "financial_metrics": {
    "revenue_ytd": 245000000000,
    "cost_of_goods_sold": 195000000000,
    "gross_profit": 50000000000,
    "operating_expenses": 32000000000,
    "net_profit": 18000000000,
    "current_ratio": 1.2,
    "debt_to_equity": 2.8,
    "inventory_turnover": 4.5,
    "profit_margin": 0.073
  },
  "operational_kpis": {
    "production_volume_kg": 42500,
    "capacity_utilization": 0.85,
    "defect_rate": 0.023,
    "downtime_hours": 12.5,
    "grade_mix_efficiency": 0.78
  },
  "forecast": {
    "next_month_revenue": 42000000000,
    "next_month_production": 45000,
    "risk_level": "moderate",
    "recommended_actions": [
      "increase N220 production by 15%",
      "review N330 pricing strategy",
      "optimize inventory of raw materials"
    ]
  }
}
```

---

### 5. SRS Summary

This System Requirements Specification (SRS) will serve as a roadmap for the development, implementation and deployment of the integrated AI system at Iran Carbon Company. The new domain of **demand-driven smart manufacturing** moves the company from commodity production toward smart, market-responsive manufacturing and, by reducing waste, optimally managing inventory and responding faster to downstream industries' needs, creates a considerable competitive advantage . Given global trends and published reports, leading carbon black companies that offer a combination of efficient production with low-emission operations, AI-based process control and innovation in specialty applications will be best positioned in the value chains of the automotive, infrastructure, electronics and packaging industries .
