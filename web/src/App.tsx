import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { apiGet, apiPost, formatIrr, formatNum } from "./api";
import { buildLocalCatalog, type CatalogResponse, type ProductGrade } from "./data/grades";
import {
  buildLocalProcurementBoard,
  rankMaterialWarehouseRisks,
  resolveSupplierCity,
  resolveSupplierName,
  sanitizeProcurementBoard,
  warehouseRiskTone,
  type ProcurementBoard,
  type ProcurementMaterial,
} from "./data/procurement";
import { buildLocalSalesPipeline, sanitizeSalesPipeline, type SalesPipeline } from "./data/sales_pipeline";
import { buildLocalExportBoard, sanitizeExportBoard, type ExportBoard } from "./data/export_markets";
import {
  buildLocalEquipmentBoard,
  flattenEquipmentSensors,
  loggerKindLabel,
  opStatusLabel,
  sensorRangePct,
  sensorTrafficStatus,
  trafficLabel,
  type EquipmentBoard,
  type EquipmentSensor,
  type EquipmentUnit,
  type ProcessActionLog,
  type ProcessAlert,
  type RulComponentsBoard,
} from "./data/equipment";
import { buildLocalRulComponentsBoard, severityLabelFa } from "./data/rul_components";
import { buildLocalStockBoard, type StockBoard } from "./data/stock";
import { buildLivePnlSnapshot } from "./data/live_pnl";
import { buildLocalProductionBoard, type ProductionBoard } from "./data/production_plan";
import {
  actionLabelFa,
  buildLocalMarketScenarioBoard,
  buyAdviceLabelFa,
  riskTone,
  type MarketScenarioBoard,
} from "./data/market_scenarios";
import { StockChart } from "./StockChart";
import { ExportForecastChart } from "./ExportForecastChart";

type TabId =
  | "overview"
  | "products"
  | "supply"
  | "energy"
  | "quality"
  | "demand"
  | "commercial"
  | "export"
  | "market"
  | "maturity";

type FinanceDash = {
  generated_at?: string;
  finance?: Record<string, unknown> | null;
  sales_mtd?: { month_revenue?: number; month_qty?: number };
  production?: { open_batches?: number; active_grades?: number };
  maintenance_alerts_open?: number;
  quality_anomalies_24h?: number;
  crm_at_risk_customers?: number;
  cashflow?: {
    net_cashflow?: number;
    liquidity_risk?: string;
    projected_inflow?: number;
    projected_outflow?: number;
  } | null;
  sales_forecasts?: Array<Record<string, unknown>>;
  high_margin_production?: Array<Record<string, unknown>>;
  supply_signals?: Array<Record<string, unknown>>;
  ratios?: { ratios?: Record<string, number | null>; improvement_areas?: string[] };
};

type OpsStatus = {
  availability_pct?: number;
  sla_met?: boolean;
  target_availability_pct?: number;
  services?: Record<string, { status: string; latency_ms: number }>;
};

type MaturityDash = {
  production_models?: Array<{ domain: string; version: string; status: string }>;
  latest_roi?: {
    annual_benefits_irr?: number;
    payback_months?: number;
    maturity_pct?: number;
    npv_proxy_irr?: number;
    on_track?: boolean;
  } | null;
  targets?: { annual_benefits_irr?: number; payback_months?: number };
  inventory_actions_7d?: Array<{ action: string; n: number; saving: number }>;
};

const TABS: Array<{ id: TabId; label: string }> = [
  { id: "overview", label: "Executive view" },
  { id: "products", label: "Products and grades" },
  { id: "supply", label: "Supply and purchasing" },
  { id: "energy", label: "Equipment and energy" },
  { id: "quality", label: "Quality" },
  { id: "demand", label: "Demand and production" },
  { id: "commercial", label: "Sales and finance" },
  { id: "export", label: "Exports" },
  { id: "market", label: "Shekarbon stock" },
  { id: "maturity", label: "Maturity and MLOps" },
];

function Kpi({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "neutral" | "ok" | "warn" | "danger";
}) {
  return (
    <div className="panel" style={{ animationDelay: "0.05s" }}>
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
      {hint ? (
        <div className="kpi-hint">
          <span className={`badge ${tone}`}>{hint}</span>
        </div>
      ) : null}
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="panel">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

function TrafficLight({ status }: { status: string }) {
  const active = status === "critical" ? "red" : status === "warning" ? "yellow" : status === "ok" ? "green" : "off";
  return (
    <div className="traffic-light" title={trafficLabel(status)} aria-label={trafficLabel(status)}>
      <span className={`traffic-lamp red ${active === "red" ? "on" : ""}`} />
      <span className={`traffic-lamp yellow ${active === "yellow" ? "on" : ""}`} />
      <span className={`traffic-lamp green ${active === "green" ? "on" : ""}`} />
    </div>
  );
}

function SensorGaugeCard({
  sensor,
  equipmentName,
  lineId,
  onSelect,
}: {
  sensor: EquipmentSensor;
  equipmentName: string;
  lineId?: string;
  onSelect?: () => void;
}) {
  const status = sensorTrafficStatus(sensor);
  const pct = sensorRangePct(sensor);
  const digits = sensor.value != null && Math.abs(sensor.value) >= 100 ? 0 : 2;
  return (
    <button type="button" className={`sensor-gauge-card tone-${status}`} onClick={onSelect}>
      <div className="sensor-gauge-top">
        <TrafficLight status={status} />
        <div className="sensor-gauge-meta">
          <strong>{sensor.name_fa}</strong>
          <span className="kpi-hint">
            {equipmentName}
            {lineId ? ` · ${lineId}` : ""}
          </span>
        </div>
      </div>
      <div className="sensor-gauge-value">
        <span className="sensor-reading">
          {sensor.value == null ? "—" : formatNum(sensor.value, digits)}
        </span>
        <span className="sensor-unit">{sensor.unit}</span>
      </div>
      <div className="range-track" aria-hidden>
        <div className="range-band soft-lo" />
        <div className="range-band ok" />
        <div className="range-band soft-hi" />
        <div className="range-marker" style={{ insetInlineStart: `${pct}%` }} />
      </div>
      <div className="range-labels">
        <span>
          min {formatNum(sensor.min_op, sensor.min_op >= 100 ? 0 : 2)} {sensor.unit}
        </span>
        <span className={`badge ${status === "critical" ? "danger" : status === "warning" ? "warn" : status === "ok" ? "ok" : "neutral"}`}>
          {trafficLabel(status)}
        </span>
        <span>
          max {formatNum(sensor.max_op, sensor.max_op >= 100 ? 0 : 2)} {sensor.unit}
        </span>
      </div>
    </button>
  );
}

export default function App() {
  const [tab, setTab] = useState<TabId>("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [finance, setFinance] = useState<FinanceDash | null>(null);
  const [ops, setOps] = useState<OpsStatus | null>(null);
  const [maturity, setMaturity] = useState<MaturityDash | null>(null);
  const [energyAlerts, setEnergyAlerts] = useState<Array<Record<string, unknown>>>([]);
  const [equipmentBoard, setEquipmentBoard] = useState<EquipmentBoard>(() => buildLocalEquipmentBoard());
  const [selectedEquipmentId, setSelectedEquipmentId] = useState<string>("FUR-001");
  const [sensorLampFilter, setSensorLampFilter] = useState<"all" | "ok" | "warning" | "critical" | "nodata">(
    "all",
  );
  const [autopilotOn, setAutopilotOn] = useState(false);
  const [adviceBusyKey, setAdviceBusyKey] = useState<string | null>(null);
  const [processActions, setProcessActions] = useState<ProcessActionLog[]>([]);
  const [rulBoard, setRulBoard] = useState<RulComponentsBoard>(() => buildLocalRulComponentsBoard());
  const [rulScanBusy, setRulScanBusy] = useState(false);
  const [rulShowAll, setRulShowAll] = useState(false);
  const [equipment, setEquipment] = useState<Array<Record<string, unknown>>>([]);
  const [anomalyEvents, setAnomalyEvents] = useState<Array<Record<string, unknown>>>([]);
  const [plans, setPlans] = useState<Array<Record<string, unknown>>>([]);
  const [productionBoard, setProductionBoard] = useState<ProductionBoard>(() => buildLocalProductionBoard());
  const [marketScenarios, setMarketScenarios] = useState<MarketScenarioBoard>(() =>
    buildLocalMarketScenarioBoard(),
  );
  const [scenarioId, setScenarioId] = useState<string>("baseline");
  const [scenarioLoading, setScenarioLoading] = useState(false);
  const [planGenerating, setPlanGenerating] = useState(false);
  const [portfolio, setPortfolio] = useState<{ high_margin_focus?: Array<Record<string, unknown>> } | null>(
    null,
  );
  const [inventoryActions, setInventoryActions] = useState<Array<Record<string, unknown>>>([]);
  const [customersAtRisk, setCustomersAtRisk] = useState<Array<Record<string, unknown>>>([]);
  const [catalog, setCatalog] = useState<CatalogResponse>(() => buildLocalCatalog());
  const [selectedGrade, setSelectedGrade] = useState<string>("N-220");
  const [procurement, setProcurement] = useState<ProcurementBoard>(() => buildLocalProcurementBoard());
  const [selectedMaterial, setSelectedMaterial] = useState<string>("cbfs");
  const [salesPipeline, setSalesPipeline] = useState<SalesPipeline>(() => buildLocalSalesPipeline());
  const [exportBoard, setExportBoard] = useState<ExportBoard>(() => buildLocalExportBoard());
  const [stock, setStock] = useState<StockBoard>(() => buildLocalStockBoard());
  const [stockMode, setStockMode] = useState<"intraday" | "daily">("intraday");
  const [updatedAt, setUpdatedAt] = useState<string>("");

  const loadStock = useCallback(async () => {
    try {
      const board = await apiGet<StockBoard>("/api/v1/finance/stock/board");
      setStock(board);
    } catch {
      // keep previous / local board
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [
        financeDash,
        opsStatus,
        maturityDash,
        alerts,
        equip,
        equipBoard,
        rulCompBoard,
        anomalies,
        prodPlans,
        prodBoard,
        scenarioBoard,
        port,
        invOpt,
        crm,
        products,
        procurementBoard,
        pipeline,
        exportDash,
      ] = await Promise.all([
        apiGet<FinanceDash>("/api/v1/finance/dashboard").catch(() => null),
        apiGet<OpsStatus>("/api/v1/ops/status").catch(() => null),
        apiGet<MaturityDash>("/api/v1/maturity/dashboard").catch(() => null),
        apiGet<Array<Record<string, unknown>>>("/api/v1/energy/alerts?open_only=true").catch(() => []),
        apiGet<Array<Record<string, unknown>>>("/api/v1/energy/equipment").catch(() => []),
        apiGet<EquipmentBoard>("/api/v1/energy/equipment/board").catch(() => buildLocalEquipmentBoard()),
        apiGet<RulComponentsBoard>("/api/v1/energy/rul/components").catch(() =>
          buildLocalRulComponentsBoard(),
        ),
        apiGet<Array<Record<string, unknown>>>("/api/v1/quality/anomaly/events?limit=12").catch(() => []),
        apiGet<Array<Record<string, unknown>>>("/api/v1/demand/production/plans?limit=12").catch(() => []),
        apiGet<ProductionBoard>("/api/v1/demand/production/board").catch(() => buildLocalProductionBoard()),
        apiGet<MarketScenarioBoard>("/api/v1/demand/scenarios/board?scenario_id=baseline").catch(() =>
          buildLocalMarketScenarioBoard("baseline"),
        ),
        apiGet<{ high_margin_focus?: Array<Record<string, unknown>> }>("/api/v1/maturity/portfolio").catch(
          () => null,
        ),
        apiPost<{ actions?: Array<Record<string, unknown>> }>("/api/v1/maturity/inventory/optimize").catch(
          () => ({ actions: [] }),
        ),
        apiGet<Array<Record<string, unknown>>>("/api/v1/sales/crm/at-risk").catch(() => []),
        apiGet<CatalogResponse>("/api/v1/quality/products").catch(() => buildLocalCatalog()),
        apiGet<ProcurementBoard>("/api/v1/supply/procurement/board").catch(() =>
          buildLocalProcurementBoard(),
        ),
        apiGet<SalesPipeline>("/api/v1/sales/pipeline/dashboard").catch(() => buildLocalSalesPipeline()),
        apiGet<ExportBoard>("/api/v1/sales/export/board").catch(() => buildLocalExportBoard()),
      ]);

      setFinance(financeDash);
      setOps(opsStatus);
      setMaturity(maturityDash);
      setEnergyAlerts(alerts);
      setEquipment(equip);
      setEquipmentBoard(equipBoard);
      setRulBoard(equipBoard.rul_components ?? rulCompBoard);
      setAutopilotOn(Boolean(equipBoard.autopilot?.enabled));
      setProcessActions(equipBoard.recent_actions ?? []);
      setAnomalyEvents(anomalies);
      setPlans(prodPlans);
      setProductionBoard(prodBoard);
      setMarketScenarios(scenarioBoard);
      setScenarioId(scenarioBoard.selected_scenario?.id ?? "baseline");
      setPortfolio(port);
      setInventoryActions(invOpt.actions ?? []);
      setCustomersAtRisk(crm);
      setCatalog(products);
      setProcurement(sanitizeProcurementBoard(procurementBoard));
      setSalesPipeline(sanitizeSalesPipeline(pipeline));
      setExportBoard(sanitizeExportBoard(exportDash));
      setUpdatedAt(new Date().toLocaleString("fa-IR"));
      void loadStock();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error loading the dashboard");
    } finally {
      setLoading(false);
    }
  }, [loadStock]);

  const generateProductionPlan = useCallback(async () => {
    setPlanGenerating(true);
    try {
      const board = await apiPost<ProductionBoard>("/api/v1/demand/production/generate", {
        horizon_days: 30,
        schedule_days: 14,
        persist: true,
        forecast_period: "1_month",
      });
      setProductionBoard(board);
      const plansList = await apiGet<Array<Record<string, unknown>>>(
        "/api/v1/demand/production/plans?limit=20",
      ).catch(() => []);
      setPlans(plansList);
      setUpdatedAt(new Date().toLocaleString("fa-IR"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error creating the production plan");
    } finally {
      setPlanGenerating(false);
    }
  }, []);

  const loadMarketScenario = useCallback(async (id: string) => {
    setScenarioLoading(true);
    setScenarioId(id);
    try {
      const board = await apiPost<MarketScenarioBoard>("/api/v1/demand/scenarios/board", {
        scenario_id: id,
        horizon_days: 30,
        include_all_presets: true,
      });
      setMarketScenarios(board);
      setUpdatedAt(new Date().toLocaleString("fa-IR"));
    } catch {
      setMarketScenarios(buildLocalMarketScenarioBoard(id));
    } finally {
      setScenarioLoading(false);
    }
  }, []);

  const toggleAutopilot = useCallback(async () => {
    const next = !autopilotOn;
    try {
      const res = await apiPost<{ enabled: boolean; recent_actions?: ProcessActionLog[]; message_fa?: string }>(
        "/api/v1/energy/process/autopilot",
        { enabled: next },
      );
      setAutopilotOn(Boolean(res.enabled));
      if (res.recent_actions) setProcessActions(res.recent_actions);
      // refresh board so auto-apply runs when turning ON
      const board = await apiGet<EquipmentBoard>("/api/v1/energy/equipment/board").catch(() => null);
      if (board) {
        setEquipmentBoard(board);
        setAutopilotOn(Boolean(board.autopilot?.enabled));
        setProcessActions(board.recent_actions ?? res.recent_actions ?? []);
        if (board.rul_components) setRulBoard(board.rul_components);
      }
    } catch {
      setAutopilotOn(next);
    }
  }, [autopilotOn]);

  const scanComponentRul = useCallback(async () => {
    setRulScanBusy(true);
    try {
      const res = await apiPost<{
        scanned?: number;
        alerts?: number;
        inserted?: number;
        board?: RulComponentsBoard;
      }>("/api/v1/energy/rul/components/scan", {});
      if (res.board) {
        setRulBoard(res.board);
      } else {
        const board = await apiGet<RulComponentsBoard>("/api/v1/energy/rul/components").catch(() => null);
        if (board) setRulBoard(board);
      }
      const alerts = await apiGet<Array<Record<string, unknown>>>("/api/v1/energy/alerts?open_only=true").catch(
        () => null,
      );
      if (alerts) setEnergyAlerts(alerts);
      setUpdatedAt(new Date().toLocaleString("fa-IR"));
    } catch {
      setRulBoard(buildLocalRulComponentsBoard());
    } finally {
      setRulScanBusy(false);
    }
  }, []);

  const applyProcessAdvice = useCallback(
    async (alert: ProcessAlert, actionId?: string, mode: "manual" | "auto" = "manual") => {
      const key = `${alert.equipment_id}-${alert.sensor_key}-${actionId ?? "primary"}`;
      setAdviceBusyKey(key);
      try {
        const res = await apiPost<{ status: string; action?: ProcessActionLog }>(
          "/api/v1/energy/process/advice/apply",
          {
            equipment_id: alert.equipment_id,
            sensor_key: alert.sensor_key,
            measured_value: alert.measured_value ?? alert.value,
            min_op: alert.min_op,
            max_op: alert.max_op,
            unit: alert.unit,
            severity: alert.severity,
            message: alert.message,
            equipment_name: alert.equipment_name,
            sensor_name: alert.sensor_name,
            action_id: actionId ?? alert.primary_recommendation?.action_id,
            mode,
            operator: "dashboard-operator",
          },
        );
        if (res.action) {
          setProcessActions((prev) => [res.action!, ...prev].slice(0, 30));
        }
      } catch {
        // offline: log locally
        const rec = alert.primary_recommendation;
        if (rec) {
          setProcessActions((prev) =>
            [
              {
                id: `local-${Date.now()}`,
                applied_at: new Date().toISOString(),
                mode,
                operator: mode === "auto" ? "autopilot" : "dashboard-operator",
                equipment_id: alert.equipment_id,
                equipment_name: alert.equipment_name,
                sensor_key: alert.sensor_key,
                sensor_name: alert.sensor_name,
                action_id: rec.action_id,
                action_fa: rec.action_fa,
                status: "applied",
              },
              ...prev,
            ].slice(0, 30),
          );
        }
      } finally {
        setAdviceBusyKey(null);
      }
    },
    [],
  );

  useEffect(() => {
    void load();
    const id = window.setInterval(() => void load(), 60000);
    return () => window.clearInterval(id);
  }, [load]);

  useEffect(() => {
    void loadStock();
    const id = window.setInterval(() => void loadStock(), 5000);
    return () => window.clearInterval(id);
  }, [loadStock]);

  const serviceRows = useMemo(() => {
    if (!ops?.services) return [];
    return Object.entries(ops.services).map(([name, meta]) => ({ name, ...meta }));
  }, [ops]);

  const selectedProduct: ProductGrade | undefined = useMemo(
    () => catalog.products.find((p) => p.code === selectedGrade) ?? catalog.products[0],
    [catalog, selectedGrade],
  );

  const selectedMat: ProcurementMaterial | undefined = useMemo(
    () => procurement.materials.find((m) => m.id === selectedMaterial) ?? procurement.materials[0],
    [procurement, selectedMaterial],
  );

  const selectedEquip: EquipmentUnit | undefined = useMemo(
    () =>
      equipmentBoard.equipment.find((e) => e.id === selectedEquipmentId) ?? equipmentBoard.equipment[0],
    [equipmentBoard, selectedEquipmentId],
  );

  const allSensors = useMemo(() => flattenEquipmentSensors(equipmentBoard), [equipmentBoard]);
  const filteredSensors = useMemo(() => {
    if (sensorLampFilter === "all") return allSensors;
    return allSensors.filter((s) => sensorTrafficStatus(s) === sensorLampFilter);
  }, [allSensors, sensorLampFilter]);

  const lampCounts = useMemo(() => {
    const c = { ok: 0, warning: 0, critical: 0, nodata: 0 };
    for (const s of allSensors) {
      const st = sensorTrafficStatus(s);
      if (st in c) c[st as keyof typeof c] += 1;
    }
    return c;
  }, [allSensors]);

  const rulRows = useMemo(() => {
    if (rulShowAll) return rulBoard.components;
    return rulBoard.alerts.length > 0 ? rulBoard.alerts : rulBoard.components.filter((c) => c.alert);
  }, [rulBoard, rulShowAll]);

  const materialWarehouseRisks = useMemo(
    () =>
      rankMaterialWarehouseRisks(procurement.materials, {
        feedstockPressure: marketScenarios.macros?.indices?.cost_pressure,
      }),
    [procurement.materials, marketScenarios.macros?.indices?.cost_pressure],
  );

  const livePnl = useMemo(
    () =>
      buildLivePnlSnapshot({
        finance: finance?.finance,
        salesMtd: finance?.sales_mtd,
        procurement,
        salesPipeline,
        marketScenarios,
      }),
    [finance, procurement, salesPipeline, marketScenarios],
  );

  const title = TABS.find((t) => t.id === tab)?.label ?? "";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">Shokrban · AI Platform</div>
          <h1>Iran Carbon</h1>
          <p>Integrated AI dashboard for industrial carbon black production</p>
        </div>
        <nav className="nav">
          {TABS.map((item) => (
            <button
              key={item.id}
              className={tab === item.id ? "active" : ""}
              onClick={() => setTab(item.id)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          Auto-refresh every 60 seconds
          <br />
          Last time: {updatedAt || "—"}
        </div>
      </aside>

      <main className="main">
        <div className="topbar">
          <div>
            <h2>{title}</h2>
            <p className="subtitle">Online view of operations, quality, market and product maturity</p>
          </div>
          <div className="actions">
            <button className="btn" type="button" onClick={() => void load()}>
              Refresh
            </button>
            <a className="btn primary" href="/api/v1/finance/dashboard" target="_blank" rel="noreferrer">
              Live API
            </a>
          </div>
        </div>

        {loading && !finance && !ops ? <div className="loading">Connecting to services…</div> : null}
        {error ? (
          <div className="error">
            {error}
            <div style={{ marginTop: "0.75rem" }}>
              Bring up the Backend locally: <code>.\scripts\dev-backend.ps1</code>
              <br />
              Or the whole dashboard: <code>.\scripts\dev-dashboard.ps1</code>
              <br />
              Guide: <code>docs/OFFLINE_DASHBOARD.fa.md</code>
            </div>
          </div>
        ) : null}

        {!error && tab === "overview" ? (
          <div className="stack">
            <div className="grid kpi">
              <Kpi
                label="Revenue this month"
                value={formatIrr(Number(finance?.sales_mtd?.month_revenue ?? 0))}
                hint="MTD sales"
                tone="ok"
              />
              <Kpi
                label="Open maintenance alerts"
                value={formatNum(finance?.maintenance_alerts_open ?? 0, 0)}
                hint="RUL ≤ 3 days"
                tone={(finance?.maintenance_alerts_open ?? 0) > 0 ? "warn" : "ok"}
              />
              <Kpi
                label="Quality anomalies 24h"
                value={formatNum(finance?.quality_anomalies_24h ?? 0, 0)}
                hint="Process control"
                tone={(finance?.quality_anomalies_24h ?? 0) > 0 ? "warn" : "ok"}
              />
              <Kpi
                label="System availability"
                value={`${formatNum(ops?.availability_pct ?? 0)}%`}
                hint={ops?.sla_met ? "SLA met" : "Below the 99.9% target"}
                tone={ops?.sla_met ? "ok" : "danger"}
              />
            </div>

            <div className="grid kpi">
              <Kpi
                label={`Stock ${stock.ticker.symbol_fa}`}
                value={formatNum(stock.quote.last_price, 0)}
                hint={`${stock.quote.day_change_pct > 0 ? "+" : ""}${formatNum(stock.quote.day_change_pct)}% today`}
                tone={stock.quote.day_change_pct >= 0 ? "ok" : "danger"}
              />
              <Kpi
                label="Today's trading volume"
                value={formatNum(stock.quote.volume, 0)}
                hint={stock.quote.status}
              />
              <Kpi
                label="Weekly / monthly change"
                value={`${formatNum(stock.quote.week_change_pct)}%`}
                hint={`Monthly ${formatNum(stock.quote.month_change_pct)}%`}
                tone={stock.quote.month_change_pct >= 0 ? "ok" : "danger"}
              />
              <Kpi
                label="ISIN"
                value={stock.ticker.isin}
                hint={stock.ticker.market}
              />
            </div>
            <div className="actions" style={{ marginBottom: "0.5rem" }}>
              <button type="button" className="btn primary" onClick={() => setTab("market")}>
                View the Shekarbon board and live chart
              </button>
              <button type="button" className="btn" onClick={() => setTab("export")}>
                Export markets and forecast
              </button>
            </div>

            <Panel title="Current Iran Carbon products">
              <div className="grade-cards">
                {catalog.products.map((p) => (
                  <button
                    key={p.code}
                    type="button"
                    className={`grade-card ${selectedGrade === p.code ? "active" : ""}`}
                    onClick={() => {
                      setSelectedGrade(p.code);
                      setTab("products");
                    }}
                  >
                    <div className="grade-code">{p.code}</div>
                    <div className="grade-trade">
                      {p.trade_name}
                      {p.variant ? ` · ${p.variant}` : ""}
                    </div>
                    <div className="kpi-hint">{p.classification}</div>
                    <span className="badge ok">In production</span>
                  </button>
                ))}
              </div>
            </Panel>

            <Panel title="Raw material prices and best purchase source">
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Material</th>
                      <th>Current price</th>
                      <th>Best supplier</th>
                      <th>Trend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {procurement.materials.slice(0, 5).map((m) => (
                      <tr
                        key={m.id}
                        style={{ cursor: "pointer" }}
                        onClick={() => {
                          setSelectedMaterial(m.id);
                          setTab("supply");
                        }}
                      >
                        <td>{m.name_fa}</td>
                        <td>
                          <strong>{formatIrr(m.latest_price_irr)}</strong>
                        </td>
                        <td>{m.best_supplier ? resolveSupplierName(m.best_supplier.supplier_id, m.best_supplier.supplier_name, procurement) : "—"}</td>
                        <td>
                          <span
                            className={`badge ${
                              m.trend === "up" ? "danger" : m.trend === "down" ? "ok" : "neutral"
                            }`}
                          >
                            {m.trend === "up" ? "Rising" : m.trend === "down" ? "Falling" : "Stable"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>

            <div className="grid two">
              <Panel title="Raw material purchase warehousing risk">
                <p className="kpi-hint" style={{ marginBottom: "0.65rem" }}>
                  Sorted by risk severity — criticality, portfolio share, delivery time and price trend
                </p>
                {materialWarehouseRisks.length === 0 ? (
                  <div className="empty">No raw material to evaluate.</div>
                ) : (
                  materialWarehouseRisks.map((r) => (
                    <div
                      key={r.material_id}
                      className="list-row"
                      style={{ cursor: "pointer" }}
                      onClick={() => {
                        setSelectedMaterial(r.material_id);
                        setTab("supply");
                      }}
                    >
                      <span>
                        <strong>{r.name_fa}</strong>
                        <span className="kpi-hint" style={{ display: "block", marginTop: "0.15rem" }}>
                          {r.reason_fa}
                        </span>
                      </span>
                      <span className={`badge ${warehouseRiskTone(r.severity)}`}>{r.severity_fa}</span>
                    </div>
                  ))
                )}
              </Panel>

              <Panel title="Instantaneous profit and operating cost">
                <p className="kpi-hint" style={{ marginBottom: "0.55rem" }}>
                  {livePnl.as_of_label}
                  {livePnl.source ? ` · ${livePnl.source}` : ""}
                </p>
                <div className="list-row">
                  <span>Net profit at the moment</span>
                  <strong>{formatIrr(livePnl.net_profit_irr)}</strong>
                </div>
                <div className="list-row">
                  <span>Gross profit at the moment</span>
                  <strong>{formatIrr(livePnl.gross_profit_irr)}</strong>
                </div>
                <div className="list-row">
                  <span>Raw material purchases</span>
                  <span>{formatIrr(livePnl.material_purchase_irr)}</span>
                </div>
                <div className="list-row">
                  <span>Sales volume</span>
                  <span>{formatIrr(livePnl.sales_irr)}</span>
                </div>
                <div className="list-row">
                  <span>Purchase queue (tomans / {formatNum(livePnl.horizon_days, 0)} days)</span>
                  <span>{formatIrr(livePnl.purchase_queue_irr)}</span>
                </div>
                <div className="list-row">
                  <span>Material transport to the plant</span>
                  <span>{formatIrr(livePnl.inbound_freight_irr)}</span>
                </div>
                <div className="list-row">
                  <span>Sales distribution</span>
                  <span>{formatIrr(livePnl.outbound_distribution_irr)}</span>
                </div>
                <p className="kpi-hint" style={{ margin: "0.75rem 0 0.4rem" }}>
                  Profit from 5 scenarios if applied
                </p>
                {livePnl.scenario_profits.map((s) => (
                  <div key={s.id} className="list-row">
                    <span>
                      {s.name_fa}
                      {s.recommended ? (
                        <span className="badge ok" style={{ marginRight: "0.35rem" }}>
                          Suggested
                        </span>
                      ) : null}
                    </span>
                    <span>
                      <strong>{formatIrr(s.estimated_profit_irr)}</strong>
                      {s.delta_vs_baseline_irr !== 0 ? (
                        <span
                          className={`badge ${s.delta_vs_baseline_irr > 0 ? "ok" : "warn"}`}
                          style={{ marginRight: "0.35rem" }}
                        >
                          {s.delta_vs_baseline_irr > 0 ? "+" : ""}
                          {formatIrr(s.delta_vs_baseline_irr)}
                        </span>
                      ) : null}
                    </span>
                  </div>
                ))}
              </Panel>
            </div>

            <div className="grid two">
              <Panel title="Service status">
                <table>
                  <thead>
                    <tr>
                      <th>Service</th>
                      <th>Status</th>
                      <th>Latency (ms)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {serviceRows.slice(0, 10).map((row) => (
                      <tr key={row.name}>
                        <td>{row.name}</td>
                        <td>
                          <span className={`status-dot ${row.status}`} />
                          {row.status}
                        </td>
                        <td>{formatNum(row.latency_ms)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Panel>

              <Panel title="High-margin production plan">
                <table>
                  <thead>
                    <tr>
                      <th>Grade</th>
                      <th>Quantity (kg)</th>
                      <th>Margin</th>
                      <th>Line</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(finance?.high_margin_production ?? []).map((row, idx) => (
                      <tr key={`${row.product_grade}-${idx}`}>
                        <td>{String(row.product_grade)}</td>
                        <td>{formatNum(Number(row.planned_quantity_kg), 0)}</td>
                        <td>{formatNum(Number(row.margin_score) * 100)}%</td>
                        <td>{String(row.production_line ?? "—")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {(finance?.high_margin_production?.length ?? 0) === 0 ? (
                  <div className="empty">No production plan has been recorded yet.</div>
                ) : null}
              </Panel>
            </div>
          </div>
        ) : null}

        {!error && tab === "products" ? (
          <div className="stack">
            <div className="grid kpi">
              <Kpi label="Grades in production" value={formatNum(catalog.count, 0)} hint="Quality specification sheet" tone="ok" />
              <Kpi
                label="Families"
                value={formatNum(catalog.classifications?.length ?? new Set(catalog.products.map((p) => p.classification)).size, 0)}
                hint={(catalog.classifications ?? [...new Set(catalog.products.map((p) => p.classification))]).join(" · ")}
              />
              <Kpi
                label="Selected grade"
                value={selectedProduct?.code ?? "—"}
                hint={selectedProduct?.classification ?? ""}
                tone="ok"
              />
              <Kpi label="ASTM methods" value={formatNum(catalog.comparison.length, 0)} hint="Quality control index" />
            </div>

            <div className="grade-cards">
              {catalog.products.map((p) => (
                <button
                  key={p.code}
                  type="button"
                  className={`grade-card ${selectedProduct?.code === p.code ? "active" : ""}`}
                  onClick={() => setSelectedGrade(p.code)}
                >
                  <div className="grade-code">{p.code}</div>
                  <div className="grade-trade">
                    {p.trade_name}
                    {p.variant ? ` · ${p.variant}` : ""}
                  </div>
                  <div className="th-sub">{p.classification}</div>
                  <p className="grade-desc">{p.description_fa}</p>
                  <span className="badge ok">In production</span>
                </button>
              ))}
            </div>

            {selectedProduct ? (
              <div className="grid two">
                <Panel title={`Product data sheet — ${selectedProduct.code}`}>
                  <div className="list-row">
                    <span>ASTM code</span>
                    <strong>{selectedProduct.astm_code}</strong>
                  </div>
                  <div className="list-row">
                    <span>Trade name</span>
                    <strong>{selectedProduct.trade_name}</strong>
                  </div>
                  <div className="list-row">
                    <span>Version / variant</span>
                    <strong>{selectedProduct.variant ?? "—"}</strong>
                  </div>
                  <div className="list-row">
                    <span>Classification</span>
                    <strong>{selectedProduct.classification}</strong>
                  </div>
                  <div className="list-row">
                    <span>Status</span>
                    <span className="badge ok">Currently produced</span>
                  </div>
                  <p className="grade-desc" style={{ marginTop: "0.85rem" }}>
                    {selectedProduct.description_fa}
                  </p>
                </Panel>

                <Panel title="Complete quality specification (Quality Specification)">
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Indicator</th>
                          <th>ASTM</th>
                          <th>Specification</th>
                          <th>Unit</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedProduct.quality_specs.map((s) => (
                          <tr key={s.id}>
                            <td>{s.label_fa}</td>
                            <td>{s.astm}</td>
                            <td>
                              <strong>{s.spec}</strong>
                            </td>
                            <td>{s.unit}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Panel>
              </div>
            ) : null}

            <Panel title="Quality specification comparison table (Quality Specification)">
              <div className="table-scroll">
                <table className="spec-table">
                  <thead>
                    <tr>
                      <th>Indicator / test</th>
                      <th>ASTM</th>
                      <th>Unit</th>
                      {catalog.products.map((p) => (
                        <th key={p.code}>
                          {p.code}
                          <div className="th-sub">
                            {p.trade_name}
                            {p.variant ? ` ${p.variant}` : ""}
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {catalog.comparison.map((row) => (
                      <tr key={row.id}>
                        <td>
                          <div>{row.label_fa}</div>
                          <div className="th-sub">{row.label_en}</div>
                        </td>
                        <td>{row.astm}</td>
                        <td>{row.unit}</td>
                        {catalog.products.map((p) => (
                          <td key={`${row.id}-${p.code}`}>
                            <strong>{row.by_grade[p.code]}</strong>
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {catalog.source ? <p className="source-note">Source: {catalog.source}</p> : null}
            </Panel>
          </div>
        ) : null}

        {!error && tab === "supply" ? (
          <div className="stack">
            <div className="grid kpi">
              <Kpi
                label="Purchase sources"
                value={formatNum(procurement.summary?.supplier_count ?? procurement.suppliers.length, 0)}
                hint="Active suppliers"
                tone="ok"
              />
              <Kpi
                label="Raw materials"
                value={formatNum(procurement.summary?.material_count ?? procurement.materials.length, 0)}
                hint="Process feedstock and energy"
              />
              <Kpi
                label="Best CBFS price"
                value={
                  procurement.summary?.best_cbfs
                    ? formatIrr(procurement.summary.best_cbfs.price_irr)
                    : "—"
                }
                hint={resolveSupplierName(
                  procurement.summary?.best_cbfs?.supplier_id,
                  procurement.summary?.best_cbfs?.supplier_name,
                  procurement,
                )}
                tone="ok"
              />
              <Kpi
                label="Data source"
                value={procurement.materials[0]?.price_source === "database" ? "Live" : "Catalog"}
                hint={procurement.updated_label ?? ""}
              />
            </div>

            <Panel title="Updated raw material price board">
              <div className="table-scroll">
                <table className="spec-table">
                  <thead>
                    <tr>
                      <th>Material</th>
                      <th>Category</th>
                      <th>Current price</th>
                      <th>Average of offers</th>
                      <th>7-day change</th>
                      <th>Trend</th>
                      <th>Best supplier</th>
                      <th>Unit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {procurement.materials.map((m) => (
                      <tr
                        key={m.id}
                        className={selectedMaterial === m.id ? "row-active" : ""}
                        style={{ cursor: "pointer" }}
                        onClick={() => setSelectedMaterial(m.id)}
                      >
                        <td>
                          <strong>{m.name_fa}</strong>
                          <div className="th-sub">{m.name_en}</div>
                        </td>
                        <td>{m.category}</td>
                        <td>
                          <strong>{formatIrr(m.latest_price_irr)}</strong>
                        </td>
                        <td>{formatIrr(m.avg_market_irr)}</td>
                        <td>
                          {m.change_pct_7d == null
                            ? "—"
                            : `${m.change_pct_7d > 0 ? "+" : ""}${formatNum(m.change_pct_7d)}%`}
                        </td>
                        <td>
                          <span
                            className={`badge ${
                              m.trend === "up" ? "danger" : m.trend === "down" ? "ok" : "neutral"
                            }`}
                          >
                            {m.trend === "up" ? "Rising" : m.trend === "down" ? "Falling" : "Stable"}
                          </span>
                        </td>
                        <td>
                          {m.best_supplier
                            ? `${resolveSupplierName(m.best_supplier.supplier_id, m.best_supplier.supplier_name, procurement)} (${formatIrr(m.best_supplier.price_irr)})`
                            : "—"}
                        </td>
                        <td>{m.unit}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {procurement.source ? <p className="source-note">Source: {procurement.source}</p> : null}
            </Panel>

            {selectedMat ? (
              <div className="grid two">
                <Panel title={`Purchase offers — ${selectedMat.name_fa}`}>
                  <table>
                    <thead>
                      <tr>
                        <th>Supplier</th>
                        <th>City</th>
                        <th>Price</th>
                        <th>Delivery (days)</th>
                        <th>Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedMat.quotes.map((q) => (
                        <tr key={`${selectedMat.id}-${q.supplier_id}`}>
                          <td>{resolveSupplierName(q.supplier_id, q.supplier_name, procurement)}</td>
                          <td>{resolveSupplierCity(q.supplier_id, q.city, procurement)}</td>
                          <td>
                            <strong>{formatIrr(q.price_irr)}</strong>
                          </td>
                          <td>{q.lead_time_days ?? "—"}</td>
                          <td>{q.rating != null ? formatNum(q.rating) : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {selectedMat.forecast ? (
                    <div style={{ marginTop: "0.85rem" }}>
                      <div className="list-row">
                        <span>Price forecast</span>
                        <strong>{formatIrr(selectedMat.forecast.predicted_price_irr)}</strong>
                      </div>
                      <div className="list-row">
                        <span>Purchase recommendation</span>
                        <span className="badge warn">{selectedMat.forecast.recommendation}</span>
                      </div>
                    </div>
                  ) : null}
                </Panel>

                <Panel title="Material data sheet">
                  <div className="list-row">
                    <span>Importance</span>
                    <span
                      className={`badge ${
                        selectedMat.criticality === "critical"
                          ? "danger"
                          : selectedMat.criticality === "high"
                            ? "warn"
                            : "ok"
                      }`}
                    >
                      {selectedMat.criticality}
                    </span>
                  </div>
                  <div className="list-row">
                    <span>Approximate cost share</span>
                    <strong>{formatNum(selectedMat.typical_share_pct, 0)}%</strong>
                  </div>
                  <div className="list-row">
                    <span>Category</span>
                    <strong>{selectedMat.category}</strong>
                  </div>
                  <div className="list-row">
                    <span>Last market update</span>
                    <span>{selectedMat.market_as_of ?? "Catalog"}</span>
                  </div>
                </Panel>
              </div>
            ) : null}

            <Panel title="Purchase sources (suppliers)">
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Code</th>
                      <th>Name</th>
                      <th>Type</th>
                      <th>Location</th>
                      <th>Score</th>
                      <th>Delivery capability</th>
                      <th>Quality</th>
                      <th>Payment terms</th>
                      <th>Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {procurement.suppliers.map((s) => (
                      <tr key={s.id}>
                        <td>{s.id}</td>
                        <td>
                          <strong>{resolveSupplierName(s.id, s.name, procurement)}</strong>
                        </td>
                        <td>{s.type?.includes("?") ? "—" : s.type}</td>
                        <td>
                          {(s.city?.includes("?") ? "—" : s.city)} · {(s.province?.includes("?") ? "—" : s.province)}
                        </td>
                        <td>{formatNum(s.rating)}</td>
                        <td>{formatNum(s.delivery_reliability * 100, 0)}%</td>
                        <td>{formatNum(s.quality_rating)}</td>
                        <td>{s.payment_terms?.includes("?") ? "—" : s.payment_terms}</td>
                        <td>{s.notes_fa?.includes("?") ? "—" : s.notes_fa}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          </div>
        ) : null}

        {!error && tab === "energy" ? (
          <div className="stack">
            <div className="grid kpi">
              <Kpi
                label="Total sensors"
                value={formatNum(allSensors.length, 0)}
                hint={`${formatNum(equipmentBoard.summary.equipment_count, 0)} equipment`}
                tone="ok"
              />
              <Kpi
                label="Green light"
                value={formatNum(lampCounts.ok, 0)}
                hint="Within the operating range"
                tone="ok"
              />
              <Kpi
                label="Yellow light"
                value={formatNum(lampCounts.warning, 0)}
                hint="Near the limit / warning"
                tone={lampCounts.warning ? "warn" : "ok"}
              />
              <Kpi
                label="Red light"
                value={formatNum(lampCounts.critical, 0)}
                hint={`${formatNum(equipmentBoard.summary.open_process_alerts, 0)} process alerts`}
                tone={lampCounts.critical ? "danger" : "ok"}
              />
              <Kpi
                label="Component RUL alerts"
                value={formatNum(rulBoard.summary.alert_count, 0)}
                hint={`Minimum RUL: ${formatNum(Number(rulBoard.summary.min_rul_days ?? 0))} days`}
                tone={
                  (rulBoard.summary.critical_count ?? 0) > 0
                    ? "danger"
                    : (rulBoard.summary.alert_count ?? 0) > 0
                      ? "warn"
                      : "ok"
                }
              />
            </div>

            <Panel title="Sensor light board — operating range">
              <p className="kpi-hint" style={{ marginBottom: "0.75rem" }}>
                Green = in range · Yellow = near the operating limit (±10% edge) · Red = out of range · unit and operating value on each card
              </p>
              <div className="lamp-filter-row">
                {(
                  [
                    ["all", `All (${allSensors.length})`],
                    ["ok", `Green (${lampCounts.ok})`],
                    ["warning", `Yellow (${lampCounts.warning})`],
                    ["critical", `Red (${lampCounts.critical})`],
                  ] as const
                ).map(([id, label]) => (
                  <button
                    key={id}
                    type="button"
                    className={`btn ${sensorLampFilter === id ? "primary" : ""}`}
                    onClick={() => setSensorLampFilter(id)}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <div className="sensor-gauge-grid">
                {filteredSensors.map((s) => (
                  <SensorGaugeCard
                    key={`${s.equipment_id}-${s.key}`}
                    sensor={s}
                    equipmentName={s.equipment_name}
                    lineId={s.line_id}
                    onSelect={() => setSelectedEquipmentId(s.equipment_id)}
                  />
                ))}
              </div>
              {filteredSensors.length === 0 ? <div className="empty">No sensor matches this filter.</div> : null}
            </Panel>

            <Panel title="Carbon black production line equipment board">
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Code</th>
                      <th>Equipment</th>
                      <th>Area</th>
                      <th>Line</th>
                      <th>Sensors</th>
                      <th>Out of range</th>
                      <th>Run state</th>
                    </tr>
                  </thead>
                  <tbody>
                    {equipmentBoard.equipment.map((eq) => (
                      <tr
                        key={eq.id}
                        className={selectedEquipmentId === eq.id ? "row-active" : ""}
                        style={{ cursor: "pointer" }}
                        onClick={() => setSelectedEquipmentId(eq.id)}
                      >
                        <td>{eq.id}</td>
                        <td>
                          <strong>{eq.name_fa}</strong>
                          <div className="kpi-hint">{eq.location}</div>
                        </td>
                        <td>{eq.area}</td>
                        <td>{eq.line_id}</td>
                        <td>{formatNum(eq.sensors.length, 0)}</td>
                        <td>{formatNum(eq.breach_count, 0)}</td>
                        <td>
                          <span
                            className={`badge ${
                              eq.op_status === "critical"
                                ? "danger"
                                : eq.op_status === "warning"
                                  ? "warn"
                                  : "ok"
                            }`}
                          >
                            {opStatusLabel(eq.op_status)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {equipmentBoard.source ? <p className="source-note">Source: {equipmentBoard.source}</p> : null}
            </Panel>

            {selectedEquip ? (
              <Panel title={`Sensor details — ${selectedEquip.name_fa}`}>
                <div className="list-row">
                  <span>Run state</span>
                  <span
                    className={`badge ${
                      selectedEquip.op_status === "critical"
                        ? "danger"
                        : selectedEquip.op_status === "warning"
                          ? "warn"
                          : "ok"
                    }`}
                  >
                    {opStatusLabel(selectedEquip.op_status)}
                  </span>
                </div>
                <div className="list-row">
                  <span>Data collection source</span>
                  <strong>
                    {loggerKindLabel(selectedEquip.data_logger?.kind)} —{" "}
                    {selectedEquip.data_logger?.name_fa ?? selectedEquip.data_logger_id ?? "—"}
                  </strong>
                </div>
                <div className="list-row">
                  <span>Protocol / address</span>
                  <span>
                    {selectedEquip.data_logger?.protocol ?? "—"}
                    {selectedEquip.data_logger?.host ? ` · ${selectedEquip.data_logger.host}` : ""}
                  </span>
                </div>
                <div className="sensor-gauge-grid" style={{ marginTop: "0.85rem" }}>
                  {selectedEquip.sensors.map((s) => (
                    <SensorGaugeCard
                      key={s.key}
                      sensor={s}
                      equipmentName={selectedEquip.name_fa}
                      lineId={selectedEquip.line_id}
                    />
                  ))}
                </div>
              </Panel>
            ) : null}

            <Panel title="Data collection layers — PLC / SCADA / Data Logger">
              <p className="kpi-hint" style={{ marginBottom: "0.75rem" }}>
                A Data Logger can be a PLC gateway or a SCADA node; each sensor is connected to one of these sources.
              </p>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Code</th>
                      <th>Name</th>
                      <th>Type</th>
                      <th>Protocol</th>
                      <th>Host</th>
                      <th>Sampling interval</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(equipmentBoard.data_loggers ?? []).map((d) => (
                      <tr key={d.id}>
                        <td>{d.id}</td>
                        <td>
                          <strong>{d.name_fa}</strong>
                          <div className="kpi-hint">{(d.areas ?? []).join(", ")}</div>
                        </td>
                        <td>
                          <span className="badge ok">{loggerKindLabel(d.kind)}</span>
                        </td>
                        <td>{d.protocol}</td>
                        <td>{d.host ?? "—"}</td>
                        <td>{d.poll_interval_s != null ? `${d.poll_interval_s} seconds` : "—"}</td>
                        <td>
                          <span className={`badge ${d.status === "online" ? "ok" : "warn"}`}>
                            {d.status === "online" ? "Online" : d.status ?? "—"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="grid kpi" style={{ marginTop: "0.85rem" }}>
                <Kpi
                  label="PLC"
                  value={formatNum(equipmentBoard.summary.plc_count ?? 0, 0)}
                  hint="Logic controller"
                />
                <Kpi
                  label="SCADA"
                  value={formatNum(equipmentBoard.summary.scada_count ?? 0, 0)}
                  hint="Central supervisory"
                />
                <Kpi
                  label="Data Logger"
                  value={formatNum(equipmentBoard.summary.data_logger_count ?? 0, 0)}
                  hint="Edge recording and forwarding"
                />
              </div>
            </Panel>

            <Panel title="Out-of-range performance alert — smart suggestion">
              <div className="autopilot-bar">
                <div>
                  <strong>Auto Pilot</strong>
                  <div className="kpi-hint">
                    On: automatic execution of eligible actions for critical alerts · Off: suggestion only + manual execution
                  </div>
                </div>
                <button
                  type="button"
                  className={`btn autopilot-toggle ${autopilotOn ? "primary on" : ""}`}
                  onClick={() => void toggleAutopilot()}
                >
                  {autopilotOn ? "ON — Active" : "OFF — Off"}
                </button>
              </div>
              {equipmentBoard.autopilot?.message_fa ? (
                <p className="kpi-hint" style={{ marginBottom: "0.65rem" }}>
                  {equipmentBoard.autopilot.message_fa}
                </p>
              ) : null}

              {equipmentBoard.process_alerts.length === 0 ? (
                <div className="empty">All sensors are within the allowed range.</div>
              ) : (
                <div className="advice-stack">
                  {equipmentBoard.process_alerts.map((a, idx) => {
                    const primary = a.primary_recommendation ?? a.recommendations?.[0];
                    const busy = adviceBusyKey?.startsWith(`${a.equipment_id}-${a.sensor_key}`);
                    return (
                      <div
                        key={`${a.equipment_id}-${a.sensor_key}-${idx}`}
                        className={`advice-card ${a.severity === "critical" ? "crit" : "warn"}`}
                      >
                        <div className="advice-head">
                          <div>
                            <strong>
                              {a.equipment_name ?? a.equipment_id} — {a.sensor_name ?? a.sensor_key}
                            </strong>
                            <div className="kpi-hint">
                              {formatNum(Number(a.measured_value ?? a.value ?? 0), 2)} {a.unit ?? ""} · allowed{" "}
                              {formatNum(Number(a.min_op ?? 0), 2)}–{formatNum(Number(a.max_op ?? 0), 2)}
                              {a.breach_direction
                                ? ` · ${a.breach_direction === "high" ? "above the limit" : "below the limit"}`
                                : ""}
                              {a.overshoot_pct != null ? ` · deviation ${formatNum(a.overshoot_pct)}%` : ""}
                            </div>
                          </div>
                          <span className={`badge ${a.severity === "critical" ? "danger" : "warn"}`}>
                            {a.severity === "critical" ? "Critical" : "Warning"}
                          </span>
                        </div>

                        {primary ? (
                          <div className="advice-primary">
                            <div className="kpi-hint">Main suggestion</div>
                            <div className="advice-action">{primary.action_fa}</div>
                            <div className="kpi-hint">
                              {primary.expected_effect_fa}
                              {primary.risk_fa ? ` · Risk: ${primary.risk_fa}` : ""}
                              {primary.confidence != null
                                ? ` · confidence ${formatNum(primary.confidence * 100, 0)}%`
                                : ""}
                            </div>
                            <div className="advice-actions-row">
                              <span
                                className={`badge ${primary.auto_eligible || primary.mode === "auto_eligible" ? "ok" : "neutral"}`}
                              >
                                {primary.auto_eligible || primary.mode === "auto_eligible"
                                  ? "Auto Pilot eligible"
                                  : "Manual only"}
                              </span>
                              <button
                                type="button"
                                className="btn primary"
                                disabled={Boolean(busy)}
                                onClick={() => void applyProcessAdvice(a, primary.action_id, "manual")}
                              >
                                Manual execution
                              </button>
                              {(primary.auto_eligible || primary.mode === "auto_eligible") && !autopilotOn ? (
                                <button
                                  type="button"
                                  className="btn"
                                  disabled={Boolean(busy)}
                                  onClick={() => void applyProcessAdvice(a, primary.action_id, "auto")}
                                >
                                  One-time execution (auto simulation)
                                </button>
                              ) : null}
                            </div>
                          </div>
                        ) : null}

                        {(a.recommendations ?? []).length > 1 ? (
                          <details className="advice-more">
                            <summary>Other suggestions ({(a.recommendations ?? []).length - 1})</summary>
                            <ul>
                              {(a.recommendations ?? []).slice(1).map((r) => (
                                <li key={r.action_id}>
                                  <div className="advice-action">{r.action_fa}</div>
                                  <div className="kpi-hint">
                                    {r.mode === "manual_only" ? "Manual" : "Auto"} · {r.expected_effect_fa}
                                  </div>
                                  <button
                                    type="button"
                                    className="btn"
                                    style={{ marginTop: "0.35rem" }}
                                    disabled={Boolean(busy)}
                                    onClick={() => void applyProcessAdvice(a, r.action_id, "manual")}
                                  >
                                    Execute
                                  </button>
                                </li>
                              ))}
                            </ul>
                          </details>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              )}

              {processActions.length > 0 ? (
                <div style={{ marginTop: "1rem" }}>
                  <h4 style={{ margin: "0 0 0.5rem", fontSize: "0.95rem" }}>Action log (manual / Auto Pilot)</h4>
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Time</th>
                          <th>Mode</th>
                          <th>Equipment</th>
                          <th>Action</th>
                          <th>Operator</th>
                        </tr>
                      </thead>
                      <tbody>
                        {processActions.slice(0, 12).map((act) => (
                          <tr key={act.id}>
                            <td>{new Date(act.applied_at).toLocaleString("fa-IR")}</td>
                            <td>
                              <span className={`badge ${act.mode === "auto" ? "ok" : "neutral"}`}>
                                {act.mode === "auto" ? "Auto" : "Manual"}
                              </span>
                            </td>
                            <td>{act.equipment_name ?? act.equipment_id}</td>
                            <td>{act.action_fa ?? act.action_id}</td>
                            <td>{act.operator}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : null}
            </Panel>

            <div className="grid two">
              <Panel title="Range alert summary">
                {equipmentBoard.process_alerts.length === 0 ? (
                  <div className="empty">No open alerts.</div>
                ) : (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Equipment</th>
                          <th>Sensor</th>
                          <th>Value</th>
                          <th>Severity</th>
                        </tr>
                      </thead>
                      <tbody>
                        {equipmentBoard.process_alerts.map((a, idx) => (
                          <tr key={`sum-${a.equipment_id}-${a.sensor_key}-${idx}`}>
                            <td>{a.equipment_name ?? a.equipment_id}</td>
                            <td>{a.sensor_name ?? a.sensor_key}</td>
                            <td>
                              {formatNum(Number(a.measured_value ?? a.value ?? 0), 2)} {a.unit ?? ""}
                            </td>
                            <td>
                              <span className={`badge ${a.severity === "critical" ? "danger" : "warn"}`}>
                                {a.severity === "critical" ? "Critical" : "Warning"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Panel>

              <Panel title="Predictive maintenance alerts (RUL)">
                <p className="kpi-hint" style={{ marginBottom: "0.75rem" }}>
                  Remaining useful life for belt, oil, air, bearing, filter, seal and motor — alert threshold ≤{" "}
                  {formatNum(rulBoard.alert_threshold_days ?? 14, 0)} days
                </p>
                <div className="lamp-filter-row" style={{ marginBottom: "0.75rem" }}>
                  <button type="button" className="btn primary" disabled={rulScanBusy} onClick={() => void scanComponentRul()}>
                    {rulScanBusy ? "Scanning…" : "Scan RUL and record alerts"}
                  </button>
                  <button
                    type="button"
                    className={`btn ${!rulShowAll ? "primary" : ""}`}
                    onClick={() => setRulShowAll(false)}
                  >
                    Alerts only ({formatNum(rulBoard.summary.alert_count, 0)})
                  </button>
                  <button
                    type="button"
                    className={`btn ${rulShowAll ? "primary" : ""}`}
                    onClick={() => setRulShowAll(true)}
                  >
                    All components ({formatNum(rulBoard.summary.component_count, 0)})
                  </button>
                </div>
                {rulBoard.summary.types_fa?.length ? (
                  <p className="source-note" style={{ marginBottom: "0.75rem" }}>
                    Types: {rulBoard.summary.types_fa.join(" · ")}
                  </p>
                ) : null}
                {rulRows.length === 0 ? (
                  <div className="empty">No open RUL alerts.</div>
                ) : (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Type</th>
                          <th>Component</th>
                          <th>Equipment</th>
                          <th>RUL (days)</th>
                          <th>Failure probability</th>
                          <th>Failure mode</th>
                          <th>Suggested action</th>
                          <th>Severity</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rulRows.map((a) => (
                          <tr key={a.component_id}>
                            <td>{a.component_type_fa}</td>
                            <td>{a.name_fa}</td>
                            <td>
                              {a.equipment_name ?? a.equipment_id}
                              {a.line_id ? ` · ${a.line_id}` : ""}
                            </td>
                            <td>{formatNum(a.rul_days)}</td>
                            <td>{formatNum(a.failure_probability * 100, 1)}%</td>
                            <td>{a.failure_mode_fa ?? "—"}</td>
                            <td>{a.recommended_action_fa ?? "—"}</td>
                            <td>
                              <span className={`badge ${a.severity === "critical" ? "danger" : a.severity === "warning" ? "warn" : ""}`}>
                                {severityLabelFa(a.severity)}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                {energyAlerts.length > 0 ? (
                  <p className="source-note" style={{ marginTop: "0.75rem" }}>
                    Alerts recorded in DB / live: {energyAlerts.length}
                    {energyAlerts.some((a) => String(a.alert_type ?? "").startsWith("rul_"))
                      ? ` (including ${energyAlerts.filter((a) => String(a.alert_type ?? "").startsWith("rul_")).length} component RUL cases)`
                      : ""}
                  </p>
                ) : null}
                {rulBoard.source ? (
                  <p className="source-note" style={{ marginTop: "0.35rem" }}>
                    Source: {rulBoard.source}
                  </p>
                ) : null}
                {equipment.length > 0 ? (
                  <p className="source-note" style={{ marginTop: "0.35rem" }}>
                    Assets recorded in DB: {equipment.length}
                  </p>
                ) : null}
              </Panel>
            </div>
          </div>
        ) : null}

        {!error && tab === "quality" ? (
          <div className="stack">
            <div className="grid kpi">
              <Kpi
                label="Active batches"
                value={formatNum(Number(finance?.production?.open_batches ?? 0), 0)}
              />
              <Kpi
                label="Active grades"
                value={formatNum(Number(finance?.production?.active_grades ?? 0), 0)}
              />
              <Kpi
                label="Anomalies 24 hours"
                value={formatNum(Number(finance?.quality_anomalies_24h ?? 0), 0)}
                tone={(finance?.quality_anomalies_24h ?? 0) > 0 ? "warn" : "ok"}
              />
            </div>
            <Panel title="Quality anomaly events">
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Batch</th>
                    <th>Grade</th>
                    <th>Score</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {anomalyEvents.map((e) => (
                    <tr key={String(e.id)}>
                      <td>{String(e.detected_at)}</td>
                      <td>{String(e.batch_id)}</td>
                      <td>{String(e.grade)}</td>
                      <td>{formatNum(Number(e.anomaly_score), 3)}</td>
                      <td>
                        <span className={`badge ${e.is_anomaly ? "danger" : "ok"}`}>
                          {e.is_anomaly ? "Anomalous" : "Normal"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {anomalyEvents.length === 0 ? <div className="empty">No event has been recorded.</div> : null}
            </Panel>

            <Panel title="Current grades and quality control limits">
              <div className="table-scroll">
                <table className="spec-table">
                  <thead>
                    <tr>
                      <th>Grade</th>
                      <th>Trade name</th>
                      <th>Iodine number</th>
                      <th>DBP</th>
                      <th>N₂ surface area</th>
                      <th>Tint</th>
                    </tr>
                  </thead>
                  <tbody>
                    {catalog.products.map((p) => {
                      const byId = Object.fromEntries(p.quality_specs.map((s) => [s.id, s.spec]));
                      return (
                        <tr key={p.code}>
                          <td>
                            <strong>{p.code}</strong>
                          </td>
                          <td>
                            {p.trade_name}
                            {p.variant ? ` ${p.variant}` : ""}
                          </td>
                          <td>{byId.iodine_no}</td>
                          <td>{byId.oil_absorption_dbp}</td>
                          <td>{byId.n2_surface_area}</td>
                          <td>{byId.tint_strength}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Panel>
          </div>
        ) : null}

        {!error && tab === "demand" ? (
          <div className="stack">
            <div className="grid kpi">
              <Kpi
                label="Scenario balance score"
                value={formatNum(marketScenarios.summary.balance_score, 0)}
                hint={marketScenarios.selected_scenario.name_fa}
                tone={marketScenarios.summary.balance_score >= 85 ? "ok" : "warn"}
              />
              <Kpi
                label="Warehousing risk"
                value={marketScenarios.summary.warehouse_risk}
                hint={`${formatNum(marketScenarios.summary.total_excess_inventory_kg / 1000, 1)} tons surplus`}
                tone={riskTone(marketScenarios.summary.warehouse_risk)}
              />
              <Kpi
                label="Sales queue risk"
                value={marketScenarios.summary.sales_queue_risk}
                hint={`${formatNum(marketScenarios.summary.total_sales_queue_kg / 1000, 1)} tons in queue`}
                tone={riskTone(marketScenarios.summary.sales_queue_risk)}
              />
              <Kpi
                label="Material purchase queue risk"
                value={marketScenarios.summary.purchase_queue_risk}
                hint={`Feedstock ${formatNum(marketScenarios.macros.current.feedstock_basket_irr, 0)} rials`}
                tone={riskTone(marketScenarios.summary.purchase_queue_risk)}
              />
            </div>

            <Panel title="Grade production scenario — dollar · gold · oil · raw material volatility">
              <p className="kpi-hint" style={{ marginBottom: "0.65rem" }}>
                {(marketScenarios.objectives_fa ?? []).join(" · ")}
              </p>
              <div className="lamp-filter-row">
                {(marketScenarios.presets ?? []).map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    className={`btn ${scenarioId === p.id ? "primary" : ""}`}
                    disabled={scenarioLoading}
                    onClick={() => void loadMarketScenario(p.id)}
                  >
                    {p.name_fa}
                  </button>
                ))}
              </div>
              <p className="kpi-hint" style={{ marginBottom: "0.75rem" }}>
                {marketScenarios.selected_scenario.description_fa}
                {marketScenarios.source ? ` · ${marketScenarios.source}` : ""}
              </p>

              <div className="grid kpi" style={{ marginBottom: "0.85rem" }}>
                <Kpi
                  label="Dollar (rials)"
                  value={formatNum(marketScenarios.macros.current.usd_irr, 0)}
                  hint={`${formatNum(marketScenarios.macros.deltas_pct.usd_irr)}% vs. baseline`}
                  tone={marketScenarios.macros.deltas_pct.usd_irr > 5 ? "warn" : "neutral"}
                />
                <Kpi
                  label="Gold (rials/gram)"
                  value={formatNum(marketScenarios.macros.current.gold_irr_g, 0)}
                  hint={`${formatNum(marketScenarios.macros.deltas_pct.gold_irr_g)}%`}
                  tone={marketScenarios.macros.deltas_pct.gold_irr_g > 5 ? "warn" : "neutral"}
                />
                <Kpi
                  label="Brent oil (USD)"
                  value={formatNum(marketScenarios.macros.current.oil_usd, 1)}
                  hint={`${formatNum(marketScenarios.macros.deltas_pct.oil_usd)}%`}
                />
                <Kpi
                  label="Raw material basket"
                  value={formatNum(marketScenarios.macros.current.feedstock_basket_irr, 0)}
                  hint={`${formatNum(marketScenarios.macros.deltas_pct.feedstock_basket_irr)}% · pressure ${formatNum(marketScenarios.macros.indices.cost_pressure ?? 1, 2)}`}
                  tone={(marketScenarios.macros.indices.cost_pressure ?? 1) > 1.1 ? "danger" : "ok"}
                />
              </div>

              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Grade</th>
                      <th>Action</th>
                      <th>Production (tons)</th>
                      <th>Sales queue</th>
                      <th>Inventory</th>
                      <th>Warehouse surplus</th>
                      <th>Adjusted margin</th>
                      <th>Material purchase</th>
                      <th>Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {marketScenarios.grades.map((g) => (
                      <tr key={g.product_grade}>
                        <td>
                          <strong>{g.product_grade}</strong>
                          <div className="kpi-hint">{g.production_line}</div>
                        </td>
                        <td>
                          <span
                            className={`badge ${
                              g.action.includes("drawdown") || g.action.includes("hold")
                                ? "warn"
                                : g.action.includes("boost") || g.action.includes("sales")
                                  ? "ok"
                                  : "neutral"
                            }`}
                          >
                            {actionLabelFa(g.action)}
                          </span>
                        </td>
                        <td>{formatNum(g.planned_produce_kg / 1000, 1)}</td>
                        <td>{formatNum(g.sales_queue_kg / 1000, 1)}</td>
                        <td>
                          {formatNum(g.inventory_on_hand_kg / 1000, 1)}
                          <div className="kpi-hint">{formatNum(g.inventory_cover_days, 0)} days of coverage</div>
                        </td>
                        <td>{formatNum(g.excess_inventory_kg / 1000, 1)}</td>
                        <td>
                          {formatNum(g.adjusted_margin * 100)}%
                          <div className="kpi-hint">Base {formatNum(g.base_margin * 100)}%</div>
                        </td>
                        <td>
                          <span className="badge neutral">{buyAdviceLabelFa(g.feedstock_buy_advice)}</span>
                        </td>
                        <td style={{ maxWidth: "14rem", fontSize: "0.8rem" }}>{g.reason_fa}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="kpi-hint" style={{ marginTop: "0.55rem" }}>
                {marketScenarios.summary.policy_fa}
              </div>
            </Panel>

            <div className="grid two">
              <Panel title="Market scenario comparison">
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Scenario</th>
                        <th>Score</th>
                        <th>Warehouse</th>
                        <th>Sales queue</th>
                        <th>Purchase queue</th>
                        <th>Top grades</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(marketScenarios.comparisons ?? []).map((c) => (
                        <tr
                          key={c.id}
                          className={scenarioId === c.id ? "row-active" : ""}
                          style={{ cursor: "pointer" }}
                          onClick={() => void loadMarketScenario(c.id)}
                        >
                          <td>
                            <strong>{c.name_fa}</strong>
                            {c.recommended ? <span className="badge ok" style={{ marginRight: "0.35rem" }}>Suggested</span> : null}
                          </td>
                          <td>{formatNum(c.summary.balance_score, 0)}</td>
                          <td>
                            <span className={`badge ${riskTone(c.summary.warehouse_risk)}`}>
                              {c.summary.warehouse_risk}
                            </span>
                          </td>
                          <td>
                            <span className={`badge ${riskTone(c.summary.sales_queue_risk)}`}>
                              {c.summary.sales_queue_risk}
                            </span>
                          </td>
                          <td>
                            <span className={`badge ${riskTone(c.summary.purchase_queue_risk)}`}>
                              {c.summary.purchase_queue_risk}
                            </span>
                          </td>
                          <td>{(c.top_grades ?? []).join(" · ")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>
              <Panel title="Raw material purchase action (anti purchase-queue)">
                <table>
                  <thead>
                    <tr>
                      <th>Grade</th>
                      <th>Recommendation</th>
                      <th>Feedstock need (tons)</th>
                      <th>Note</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(marketScenarios.feedstock_actions ?? []).map((a, idx) => (
                      <tr key={`${a.product_grade}-${idx}`}>
                        <td>{a.product_grade}</td>
                        <td>
                          <span className="badge warn">{buyAdviceLabelFa(a.advice)}</span>
                        </td>
                        <td>{formatNum(a.feedstock_need_kg / 1000, 1)}</td>
                        <td style={{ fontSize: "0.8rem" }}>{a.note_fa}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {(marketScenarios.feedstock_actions ?? []).length === 0 ? (
                  <div className="empty">Material purchasing is on hold — no extra purchase queue is needed.</div>
                ) : null}
              </Panel>
            </div>

            <div className="grid kpi">
              <Kpi
                label="Total demand (tons)"
                value={formatNum(productionBoard.summary.total_demand_kg / 1000, 1)}
                hint={`Horizon ${formatNum(productionBoard.horizon_days, 0)} days`}
              />
              <Kpi
                label="Production plan (tons)"
                value={formatNum(productionBoard.summary.total_planned_kg / 1000, 1)}
                hint={`Capacity coverage ${formatNum(productionBoard.summary.coverage_pct)}%`}
                tone={productionBoard.summary.coverage_pct >= 85 ? "ok" : "warn"}
              />
              <Kpi
                label="Scheduled (tons)"
                value={formatNum(productionBoard.summary.total_scheduled_kg / 1000, 1)}
                hint={`${formatNum(productionBoard.summary.schedule_slots, 0)} slots · ${productionBoard.schedule_days} days`}
                tone="ok"
              />
              <Kpi
                label="Backlog (tons)"
                value={formatNum(productionBoard.summary.backlog_kg / 1000, 1)}
                hint={productionBoard.summary.lines_used.join(" · ") || "—"}
                tone={productionBoard.summary.backlog_kg > 0 ? "warn" : "ok"}
              />
            </div>

            <Panel title="Demand-driven production plan">
              <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "0.75rem" }}>
                <button
                  type="button"
                  className="btn primary"
                  disabled={planGenerating || loading}
                  onClick={() => void generateProductionPlan()}
                >
                  {planGenerating ? "Creating…" : "Create plan from demand"}
                </button>
                <span className="kpi-hint" style={{ alignSelf: "center" }}>
                  {productionBoard.source ?? "Base + sales queue + exports → line capacity"}
                </span>
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Grade</th>
                      <th>Base</th>
                      <th>Sales queue</th>
                      <th>Exports</th>
                      <th>Total demand</th>
                      <th>Safety</th>
                      <th>Plan</th>
                      <th>Line</th>
                      <th>Margin</th>
                    </tr>
                  </thead>
                  <tbody>
                    {productionBoard.demand_by_grade.map((r) => (
                      <tr key={r.product_grade}>
                        <td>
                          <strong>{r.product_grade}</strong>
                        </td>
                        <td>{formatNum(r.demand_baseline_kg / 1000, 1)}</td>
                        <td>{formatNum(r.demand_sales_queue_kg / 1000, 1)}</td>
                        <td>{formatNum(r.demand_export_kg / 1000, 1)}</td>
                        <td>{formatNum(r.demand_total_kg / 1000, 1)}</td>
                        <td>{formatNum(r.safety_stock_kg / 1000, 1)}</td>
                        <td>{formatNum(r.planned_quantity_kg / 1000, 1)}</td>
                        <td>{r.production_line}</td>
                        <td>{formatNum(r.margin_score * 100)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="kpi-hint" style={{ marginTop: "0.5rem" }}>
                Quantities in tons · demand mix: 55% historical base · 30% sales queue · 15% export share
              </div>
            </Panel>

            <div className="grid two">
              <Panel title={`Production schedule (${productionBoard.schedule_days} days)`}>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Grade</th>
                        <th>Line</th>
                        <th>Quantity (tons)</th>
                        <th>Utilization</th>
                        <th>Source</th>
                      </tr>
                    </thead>
                    <tbody>
                      {productionBoard.schedule
                        .filter((s) => s.demand_source !== "backlog")
                        .slice(0, 28)
                        .map((s, idx) => (
                          <tr key={`${s.date}-${s.product_grade}-${idx}`}>
                            <td>{s.date}</td>
                            <td>{s.product_grade}</td>
                            <td>{s.production_line}</td>
                            <td>{formatNum(s.quantity_kg / 1000, 1)}</td>
                            <td>{formatNum(s.line_utilization_pct)}%</td>
                            <td>{s.demand_source === "forecast+sales+export" ? "Demand" : s.demand_source}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
                {productionBoard.schedule.filter((s) => s.demand_source === "backlog").length > 0 ? (
                  <div className="kpi-hint" style={{ marginTop: "0.5rem" }}>
                    Backlog:{" "}
                    {productionBoard.schedule
                      .filter((s) => s.demand_source === "backlog")
                      .map((s) => `${s.product_grade} ${formatNum(s.quantity_kg / 1000, 1)}t`)
                      .join(" · ")}
                  </div>
                ) : null}
              </Panel>
              <Panel title="Inventory actions">
                <table>
                  <thead>
                    <tr>
                      <th>Grade</th>
                      <th>Action</th>
                      <th>Quantity</th>
                      <th>Estimated savings</th>
                    </tr>
                  </thead>
                  <tbody>
                    {inventoryActions.slice(0, 12).map((a, idx) => (
                      <tr key={`${a.product_grade}-${idx}`}>
                        <td>{String(a.product_grade)}</td>
                        <td>{String(a.action)}</td>
                        <td>{formatNum(Number(a.quantity_kg), 0)}</td>
                        <td>{formatIrr(Number(a.expected_saving_irr))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {inventoryActions.length === 0 ? <div className="empty">No action has been recorded.</div> : null}
              </Panel>
            </div>

            <div className="grid two">
              <Panel title="Saved plans">
                <table>
                  <thead>
                    <tr>
                      <th>Grade</th>
                      <th>Planned quantity</th>
                      <th>Safety stock</th>
                      <th>Line</th>
                    </tr>
                  </thead>
                  <tbody>
                    {plans.map((p, idx) => (
                      <tr key={`${p.product_grade}-${idx}`}>
                        <td>{String(p.product_grade)}</td>
                        <td>{formatNum(Number(p.planned_quantity_kg), 0)}</td>
                        <td>{formatNum(Number(p.safety_stock_kg), 0)}</td>
                        <td>{String(p.production_line)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {plans.length === 0 ? <div className="empty">No plan is available — press the create button.</div> : null}
              </Panel>
              <Panel title="Suggested high-margin grades">
                <div className="grid three">
                  {(portfolio?.high_margin_focus ?? productionBoard.demand_by_grade.slice(0, 3)).map((g) => (
                    <div className="panel" key={String(g.product_grade)} style={{ boxShadow: "none" }}>
                      <div className="kpi-value">{String(g.product_grade)}</div>
                      <div className="kpi-label">
                        Margin {formatNum(Number(g.margin_score) * 100)}%
                      </div>
                      <div className="kpi-hint">
                        {String(
                          "specialty_tag" in g && g.specialty_tag
                            ? g.specialty_tag
                            : "production_line" in g
                              ? String(g.production_line)
                              : "",
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </Panel>
            </div>
          </div>
        ) : null}

        {!error && tab === "commercial" ? (
          <div className="stack">
            <div className="grid kpi">
              <Kpi
                label="Active customers"
                value={formatNum(salesPipeline.summary.active_count, 0)}
                hint={`${formatNum(salesPipeline.summary.active_monthly_tonnage_kg / 1000, 1)} tons/month`}
                tone="ok"
              />
              <Kpi
                label="Potential customers"
                value={formatNum(salesPipeline.summary.potential_count, 0)}
                hint={`${formatNum(salesPipeline.summary.potential_monthly_tonnage_kg / 1000, 1)} tons/month`}
              />
              <Kpi
                label="Purchase queue (requested tons)"
                value={formatNum(salesPipeline.summary.queue_requested_tonnage_kg / 1000, 1)}
                hint={`${formatNum(salesPipeline.summary.queue_items, 0)} items · weighted ${formatNum(salesPipeline.summary.queue_weighted_tonnage_kg / 1000, 1)} tons`}
                tone="warn"
              />
              <Kpi
                label="Profit margin"
                value={`${formatNum(Number(finance?.finance?.profit_margin ?? 0) * 100)}%`}
              />
            </div>

            <div className="grid two">
              <Panel title="Active customers — monthly tonnage">
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Customer</th>
                        <th>Region</th>
                        <th>Monthly tonnage (kg)</th>
                        <th>Preferred grade</th>
                        <th>Contact</th>
                      </tr>
                    </thead>
                    <tbody>
                      {salesPipeline.active_customers.map((c) => (
                        <tr key={c.id}>
                          <td>
                            <strong>{c.name}</strong>
                            <div className="th-sub">{c.id}</div>
                          </td>
                          <td>{c.region ?? "—"}</td>
                          <td>
                            <strong>{formatNum(c.monthly_tonnage_kg, 0)}</strong>
                          </td>
                          <td>
                            {Array.isArray(c.preferred_grades)
                              ? c.preferred_grades.join(" · ")
                              : String(c.preferred_grades ?? "—")}
                          </td>
                          <td>{c.contact_person ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>

              <Panel title="Potential customers — target tonnage">
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Customer</th>
                        <th>Stage</th>
                        <th>Target tonnage (kg)</th>
                        <th>Grade</th>
                        <th>Contact</th>
                      </tr>
                    </thead>
                    <tbody>
                      {salesPipeline.potential_customers.map((c) => (
                        <tr key={c.id}>
                          <td>
                            <strong>{c.name}</strong>
                            <div className="th-sub">{c.id}</div>
                          </td>
                          <td>
                            <span className="badge warn">{c.pipeline_stage ?? "potential"}</span>
                          </td>
                          <td>
                            <strong>{formatNum(c.monthly_tonnage_kg, 0)}</strong>
                          </td>
                          <td>
                            {Array.isArray(c.preferred_grades)
                              ? c.preferred_grades.join(" · ")
                              : String(c.preferred_grades ?? "—")}
                          </td>
                          <td>{c.contact_person ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>
            </div>

            <Panel title="Purchase Queue">
              <div className="table-scroll">
                <table className="spec-table">
                  <thead>
                    <tr>
                      <th>Priority</th>
                      <th>Customer</th>
                      <th>Customer status</th>
                      <th>Grade</th>
                      <th>Requested tonnage</th>
                      <th>Probability</th>
                      <th>Weighted tonnage</th>
                      <th>Queue status</th>
                      <th>Unit price</th>
                    </tr>
                  </thead>
                  <tbody>
                    {salesPipeline.purchase_queue.map((q, idx) => (
                      <tr key={`${q.customer_id}-${q.grade}-${idx}`}>
                        <td>
                          <span className={`badge ${q.priority <= 2 ? "danger" : "warn"}`}>P{q.priority}</span>
                        </td>
                        <td>{q.customer_name ?? q.customer_id}</td>
                        <td>
                          <span className={`badge ${q.customer_status === "active" ? "ok" : "warn"}`}>
                            {q.customer_status === "active" ? "Active" : "Potential"}
                          </span>
                        </td>
                        <td>
                          <strong>{q.grade}</strong>
                        </td>
                        <td>{formatNum(q.requested_tonnage_kg, 0)}</td>
                        <td>{formatNum(q.probability * 100, 0)}%</td>
                        <td>{formatNum(q.weighted_tonnage_kg ?? q.requested_tonnage_kg * q.probability, 0)}</td>
                        <td>{q.status}</td>
                        <td>{formatIrr(q.unit_price_irr)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>

            <Panel title="Sales forecast (ML + purchase queue)">
              <div className="table-scroll">
                <table className="spec-table">
                  <thead>
                    <tr>
                      <th>Grade</th>
                      <th>ML base (kg)</th>
                      <th>Queue — requested</th>
                      <th>Queue — weighted</th>
                      <th>Combined forecast</th>
                      <th>Pipeline share</th>
                      <th>Forecast revenue</th>
                      <th>Suggested price</th>
                    </tr>
                  </thead>
                  <tbody>
                    {salesPipeline.sales_forecast_with_queue.map((f) => (
                      <tr key={f.grade}>
                        <td>
                          <strong>{f.grade}</strong>
                        </td>
                        <td>{formatNum(f.base_ml_quantity_kg, 0)}</td>
                        <td>{formatNum(f.queue_requested_kg, 0)}</td>
                        <td>{formatNum(f.queue_weighted_kg, 0)}</td>
                        <td>
                          <strong>{formatNum(f.forecast_quantity_kg, 0)}</strong>
                        </td>
                        <td>{formatNum(f.pipeline_share_pct ?? 0)}%</td>
                        <td>{formatIrr(f.forecast_revenue_irr)}</td>
                        <td>{formatIrr(f.recommended_unit_price)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {salesPipeline.source ? <p className="source-note">Source: {salesPipeline.source}</p> : null}
            </Panel>

            <div className="grid two">
              <Panel title="Saved forecasts">
                <table>
                  <thead>
                    <tr>
                      <th>Grade</th>
                      <th>Quantity</th>
                      <th>Revenue</th>
                      <th>Suggested price</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(finance?.sales_forecasts ?? []).map((f, idx) => (
                      <tr key={`${f.grade}-${idx}`}>
                        <td>{String(f.grade)}</td>
                        <td>{formatNum(Number(f.forecast_quantity_kg), 0)}</td>
                        <td>{formatIrr(Number(f.forecast_revenue_irr))}</td>
                        <td>{formatIrr(Number(f.recommended_unit_price))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Panel>
              <Panel title="CRM — customers at risk of churn">
                <table>
                  <thead>
                    <tr>
                      <th>Customer</th>
                      <th>Risk</th>
                      <th>Lifetime value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {customersAtRisk.map((c) => (
                      <tr key={String(c.id)}>
                        <td>{String(c.name)}</td>
                        <td>{formatNum(Number(c.churn_risk) * 100)}%</td>
                        <td>{formatIrr(Number(c.lifetime_value_irr))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {customersAtRisk.length === 0 ? <div className="empty">None.</div> : null}
              </Panel>
            </div>
          </div>
        ) : null}

        {!error && tab === "export" ? (
          <div className="stack">
            <div className="grid kpi">
              <Kpi
                label="Actual markets"
                value={formatNum(exportBoard.summary.actual_markets_count, 0)}
                hint={`Top: ${exportBoard.summary.top_market}`}
                tone="ok"
              />
              <Kpi
                label="Potential markets"
                value={formatNum(exportBoard.summary.potential_markets_count, 0)}
                hint={`Weighted ${formatNum(exportBoard.summary.potential_weighted_tonnage_kg / 1000, 0)} tons/year`}
              />
              <Kpi
                label="Exports YTD"
                value={`${formatNum(exportBoard.summary.ytd_export_tonnage_kg / 1000, 0)} tons`}
                hint={`Annual actual ${formatNum(exportBoard.summary.annual_actual_tonnage_kg / 1000, 0)} tons`}
                tone="ok"
              />
              <Kpi
                label="6-month forecast"
                value={`${formatNum(exportBoard.summary.six_month_forecast_kg / 1000, 0)} tons`}
                hint={`${formatNum(exportBoard.summary.six_month_revenue_usd, 0)} USD`}
              />
            </div>

            <Panel title={`${exportBoard.company ?? "Iran Carbon"} — HS ${exportBoard.hs_code ?? "280300"}`}>
              <p className="kpi-hint" style={{ marginBottom: "0.75rem" }}>
                {exportBoard.product} · average growth of actual markets{" "}
                {formatNum(exportBoard.summary.avg_growth_yoy_pct)}% per year
              </p>
              <ExportForecastChart rows={exportBoard.export_forecast} />
              {exportBoard.source ? <p className="source-note">Source: {exportBoard.source}</p> : null}
            </Panel>

            <div className="grid two">
              <Panel title="Actual export markets">
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Country</th>
                        <th>YTD (tons)</th>
                        <th>Annual (tons)</th>
                        <th>Share %</th>
                        <th>Growth %</th>
                        <th>FOB $</th>
                        <th>Grades</th>
                      </tr>
                    </thead>
                    <tbody>
                      {exportBoard.actual_markets.map((m) => (
                        <tr key={m.id}>
                          <td>
                            <strong>{m.country_fa}</strong>
                            <div className="kpi-hint">{m.buyers ?? m.region ?? ""}</div>
                          </td>
                          <td>{formatNum(m.ytd_tonnage_kg / 1000, 0)}</td>
                          <td>{formatNum(m.annual_tonnage_kg / 1000, 0)}</td>
                          <td>{formatNum(m.share_pct ?? 0)}</td>
                          <td>
                            <span
                              className={`badge ${(m.growth_yoy_pct ?? 0) >= 0 ? "ok" : "danger"}`}
                            >
                              {formatNum(m.growth_yoy_pct ?? 0)}%
                            </span>
                          </td>
                          <td>{formatNum(m.avg_fob_usd ?? 0, 0)}</td>
                          <td>{(m.main_grades ?? []).join(", ")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>

              <Panel title="Potential markets">
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Country</th>
                        <th>Annual target</th>
                        <th>Probability</th>
                        <th>Stage</th>
                        <th>Growth %</th>
                        <th>Risk</th>
                      </tr>
                    </thead>
                    <tbody>
                      {exportBoard.potential_markets.map((m) => (
                        <tr key={m.id}>
                          <td>
                            <strong>{m.country_fa}</strong>
                            <div className="kpi-hint">{(m.main_grades ?? []).join(", ")}</div>
                          </td>
                          <td>{formatNum(m.annual_tonnage_kg / 1000, 0)} tons</td>
                          <td>{formatNum((m.probability ?? 0) * 100, 0)}%</td>
                          <td>
                            <span className="badge">
                              {{
                                technical_eval: "Technical evaluation",
                                negotiation: "Negotiation",
                                lead: "Lead",
                                market_study: "Market study",
                              }[m.pipeline_stage ?? ""] ?? m.pipeline_stage ?? "—"}
                            </span>
                          </td>
                          <td>
                            <span className="badge ok">{formatNum(m.growth_yoy_pct ?? 0)}%</span>
                          </td>
                          <td>{m.risk ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>
            </div>

            <Panel title="Export forecast table (6 months)">
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Month</th>
                      <th>Actual baseline</th>
                      <th>Potential uplift</th>
                      <th>Total forecast</th>
                      <th>Revenue USD</th>
                      <th>Revenue rials</th>
                      <th>FOB</th>
                      <th>Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {exportBoard.export_forecast.map((f) => (
                      <tr key={f.month}>
                        <td>{f.month}</td>
                        <td>{formatNum(f.baseline_tonnage_kg / 1000, 1)} tons</td>
                        <td>{formatNum(f.pipeline_uplift_kg / 1000, 1)} tons</td>
                        <td>
                          <strong>{formatNum(f.forecast_tonnage_kg / 1000, 1)} tons</strong>
                        </td>
                        <td>{formatNum(f.forecast_revenue_usd, 0)}</td>
                        <td>{formatIrr(f.forecast_revenue_irr)}</td>
                        <td>{formatNum(f.avg_fob_usd, 0)}</td>
                        <td>{formatNum(f.confidence * 100, 0)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>

            <Panel title="Reference Iranian sources">
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Source</th>
                      <th>Role in the dashboard</th>
                      <th>Address</th>
                    </tr>
                  </thead>
                  <tbody>
                    {exportBoard.iranian_sources.map((s) => (
                      <tr key={s.id}>
                        <td>
                          <strong>{s.name_fa}</strong>
                        </td>
                        <td>{s.role}</td>
                        <td>
                          <a href={s.url} target="_blank" rel="noreferrer">
                            {s.url}
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          </div>
        ) : null}

        {!error && tab === "market" ? (
          <div className="stack">
            <div className="grid kpi">
              <Kpi
                label={`Last price ${stock.ticker.symbol_fa}`}
                value={formatNum(stock.quote.last_price, 0)}
                hint={stock.ticker.isin}
                tone={stock.quote.trend === "up" ? "ok" : "danger"}
              />
              <Kpi
                label="Change today"
                value={`${stock.quote.day_change_pct > 0 ? "+" : ""}${formatNum(stock.quote.day_change_pct)}%`}
                hint={`${stock.quote.day_change > 0 ? "+" : ""}${formatNum(stock.quote.day_change, 0)} rials`}
                tone={stock.quote.day_change_pct >= 0 ? "ok" : "danger"}
              />
              <Kpi
                label="Week / month"
                value={`${formatNum(stock.quote.week_change_pct)}%`}
                hint={`Monthly ${formatNum(stock.quote.month_change_pct)}%`}
                tone={stock.quote.month_change_pct >= 0 ? "ok" : "danger"}
              />
              <Kpi
                label="Trading volume"
                value={formatNum(stock.quote.volume, 0)}
                hint={`${formatNum(stock.quote.trade_count, 0)} trades`}
              />
            </div>

            <Panel title={`${stock.ticker.company_fa} — ${stock.ticker.symbol_fa} (${stock.ticker.symbol_en})`}>
              <div className="list-row">
                <span>Market</span>
                <strong>{stock.ticker.market}</strong>
              </div>
              <div className="list-row">
                <span>Industry</span>
                <strong>{stock.ticker.industry}</strong>
              </div>
              <div className="list-row">
                <span>Status</span>
                <span className={`badge ${stock.quote.trend === "up" ? "ok" : "danger"}`}>
                  {stock.quote.status}
                </span>
              </div>
              <div className="list-row">
                <span>Update</span>
                <span>{stock.quote.as_of}</span>
              </div>
              <div className="actions" style={{ marginTop: "0.85rem" }}>
                <button
                  type="button"
                  className={`btn ${stockMode === "intraday" ? "primary" : ""}`}
                  onClick={() => setStockMode("intraday")}
                >
                  Today's live chart
                </button>
                <button
                  type="button"
                  className={`btn ${stockMode === "daily" ? "primary" : ""}`}
                  onClick={() => setStockMode("daily")}
                >
                  Daily history
                </button>
                <button type="button" className="btn" onClick={() => void loadStock()}>
                  Refresh price
                </button>
              </div>
              <div style={{ marginTop: "1rem" }}>
                <StockChart
                  points={stockMode === "intraday" ? stock.intraday : stock.history_daily}
                  mode={stockMode}
                  up={stock.quote.trend === "up"}
                />
              </div>
              {stock.source ? <p className="source-note">Source: {stock.source}</p> : null}
            </Panel>

            <div className="grid two">
              <Panel title="Buy and sell details (recent trades)">
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Side</th>
                        <th>Price</th>
                        <th>Volume</th>
                        <th>Value</th>
                        <th>Broker</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stock.recent_trades.map((t, idx) => (
                        <tr key={`${t.id ?? idx}-${t.time}`}>
                          <td>{String(t.time).replace("T", " ").slice(0, 19)}</td>
                          <td>
                            <span className={`badge ${t.side === "buy" ? "ok" : "danger"}`}>
                              {t.side === "buy" ? "Buy" : "Sell"}
                            </span>
                          </td>
                          <td>
                            <strong>{formatNum(t.price, 0)}</strong>
                          </td>
                          <td>{formatNum(t.volume, 0)}</td>
                          <td>{formatIrr(t.value_irr)}</td>
                          <td>{t.broker ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>

              <Panel title="Market depth (Order Book)">
                <div className="grid two">
                  <div>
                    <h3 style={{ fontSize: "0.95rem" }}>Buy queue</h3>
                    <table>
                      <thead>
                        <tr>
                          <th>Price</th>
                          <th>Volume</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(stock.order_book?.bids ?? []).map((b, i) => (
                          <tr key={`bid-${i}`}>
                            <td className="badge ok" style={{ display: "table-cell" }}>
                              {formatNum(b.price, 0)}
                            </td>
                            <td>{formatNum(b.volume, 0)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div>
                    <h3 style={{ fontSize: "0.95rem" }}>Sell queue</h3>
                    <table>
                      <thead>
                        <tr>
                          <th>Price</th>
                          <th>Volume</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(stock.order_book?.asks ?? []).map((a, i) => (
                          <tr key={`ask-${i}`}>
                            <td>
                              <span className="badge danger">{formatNum(a.price, 0)}</span>
                            </td>
                            <td>{formatNum(a.volume, 0)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
                <div className="list-row" style={{ marginTop: "0.75rem" }}>
                  <span>Open / High / Low</span>
                  <strong>
                    {formatNum(stock.quote.open_price, 0)} / {formatNum(stock.quote.high_price, 0)} /{" "}
                    {formatNum(stock.quote.low_price, 0)}
                  </strong>
                </div>
                <div className="list-row">
                  <span>Today's trading value</span>
                  <strong>{formatIrr(stock.quote.value_irr)}</strong>
                </div>
              </Panel>
            </div>

            <Panel title="Daily gain / loss history">
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Open</th>
                      <th>High</th>
                      <th>Low</th>
                      <th>Close</th>
                      <th>Change %</th>
                      <th>Volume</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...stock.history_daily].reverse().slice(0, 20).map((d) => (
                      <tr key={d.date}>
                        <td>{d.date}</td>
                        <td>{formatNum(d.open, 0)}</td>
                        <td>{formatNum(d.high, 0)}</td>
                        <td>{formatNum(d.low, 0)}</td>
                        <td>
                          <strong>{formatNum(d.close, 0)}</strong>
                        </td>
                        <td>
                          <span
                            className={`badge ${(d.change_pct ?? 0) >= 0 ? "ok" : "danger"}`}
                          >
                            {formatNum(d.change_pct ?? 0)}%
                          </span>
                        </td>
                        <td>{formatNum(d.volume, 0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          </div>
        ) : null}

        {!error && tab === "maturity" ? (
          <div className="stack">
            <div className="grid kpi">
              <Kpi
                label="Production models"
                value={formatNum(maturity?.production_models?.length ?? 0, 0)}
              />
              <Kpi
                label="Annual benefit target"
                value={formatIrr(Number(maturity?.targets?.annual_benefits_irr ?? 200e9))}
              />
              <Kpi
                label="Approximate NPV"
                value={formatIrr(Number(maturity?.latest_roi?.npv_proxy_irr ?? 0))}
              />
              <Kpi
                label="Payback target"
                value={`${formatNum(maturity?.targets?.payback_months ?? 24, 0)} months`}
              />
            </div>
            <div className="grid two">
              <Panel title="Model registry">
                <table>
                  <thead>
                    <tr>
                      <th>Domain</th>
                      <th>Version</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(maturity?.production_models ?? []).map((m) => (
                      <tr key={`${m.domain}-${m.version}`}>
                        <td>{m.domain}</td>
                        <td>{m.version}</td>
                        <td>
                          <span className="badge ok">{m.status}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Panel>
              <Panel title="7-day inventory actions">
                <table>
                  <thead>
                    <tr>
                      <th>Action</th>
                      <th>Count</th>
                      <th>Savings</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(maturity?.inventory_actions_7d ?? []).map((a) => (
                      <tr key={a.action}>
                        <td>{a.action}</td>
                        <td>{formatNum(a.n, 0)}</td>
                        <td>{formatIrr(Number(a.saving))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Panel>
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
}
