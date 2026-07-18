import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { apiGet, apiPost, formatIrr, formatNum } from "./api";
import { buildLocalCatalog, type CatalogResponse, type ProductGrade } from "./data/grades";
import {
  buildLocalProcurementBoard,
  resolveSupplierCity,
  resolveSupplierName,
  sanitizeProcurementBoard,
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
} from "./data/equipment";
import { buildLocalStockBoard, type StockBoard } from "./data/stock";
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
  { id: "overview", label: "نمای مدیریتی" },
  { id: "products", label: "محصولات و گرید" },
  { id: "supply", label: "تأمین و خرید" },
  { id: "energy", label: "تجهیزات و انرژی" },
  { id: "quality", label: "کیفیت" },
  { id: "demand", label: "تقاضا و تولید" },
  { id: "commercial", label: "فروش و مالی" },
  { id: "export", label: "صادرات" },
  { id: "market", label: "بورس شکربن" },
  { id: "maturity", label: "بلوغ و MLOps" },
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
      setError(err instanceof Error ? err.message : "خطا در بارگذاری داشبورد");
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
      setError(err instanceof Error ? err.message : "خطا در ایجاد برنامه تولید");
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

  const title = TABS.find((t) => t.id === tab)?.label ?? "";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">Shokrban · AI Platform</div>
          <h1>کربن ایران</h1>
          <p>داشبورد یکپارچه هوش مصنوعی برای تولید دوده صنعتی</p>
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
          به‌روزرسانی خودکار هر ۶۰ ثانیه
          <br />
          آخرین بار: {updatedAt || "—"}
        </div>
      </aside>

      <main className="main">
        <div className="topbar">
          <div>
            <h2>{title}</h2>
            <p className="subtitle">نمای آنلاین عملیات، کیفیت، بازار و بلوغ محصول</p>
          </div>
          <div className="actions">
            <button className="btn" type="button" onClick={() => void load()}>
              تازه‌سازی
            </button>
            <a className="btn primary" href="/api/v1/finance/dashboard" target="_blank" rel="noreferrer">
              API زنده
            </a>
          </div>
        </div>

        {loading && !finance && !ops ? <div className="loading">در حال اتصال به سرویس‌ها…</div> : null}
        {error ? (
          <div className="error">
            {error}
            <div style={{ marginTop: "0.75rem" }}>
              Backend را محلی بالا بیاورید: <code>.\scripts\dev-backend.ps1</code>
              <br />
              یا کل داشبورد: <code>.\scripts\dev-dashboard.ps1</code>
              <br />
              راهنما: <code>docs/OFFLINE_DASHBOARD.fa.md</code>
            </div>
          </div>
        ) : null}

        {!error && tab === "overview" ? (
          <div className="stack">
            <div className="grid kpi">
              <Kpi
                label="درآمد ماه جاری"
                value={formatIrr(Number(finance?.sales_mtd?.month_revenue ?? 0))}
                hint="فروش MTD"
                tone="ok"
              />
              <Kpi
                label="هشدار نگهداری باز"
                value={formatNum(finance?.maintenance_alerts_open ?? 0, 0)}
                hint="RUL ≤ ۳ روز"
                tone={(finance?.maintenance_alerts_open ?? 0) > 0 ? "warn" : "ok"}
              />
              <Kpi
                label="ناهنجاری کیفیت ۲۴س"
                value={formatNum(finance?.quality_anomalies_24h ?? 0, 0)}
                hint="کنترل فرآیند"
                tone={(finance?.quality_anomalies_24h ?? 0) > 0 ? "warn" : "ok"}
              />
              <Kpi
                label="در دسترس بودن سیستم"
                value={`${formatNum(ops?.availability_pct ?? 0)}٪`}
                hint={ops?.sla_met ? "SLA برقرار" : "زیر هدف ۹۹.۹٪"}
                tone={ops?.sla_met ? "ok" : "danger"}
              />
            </div>

            <div className="grid kpi">
              <Kpi
                label={`بورس ${stock.ticker.symbol_fa}`}
                value={formatNum(stock.quote.last_price, 0)}
                hint={`${stock.quote.day_change_pct > 0 ? "+" : ""}${formatNum(stock.quote.day_change_pct)}٪ امروز`}
                tone={stock.quote.day_change_pct >= 0 ? "ok" : "danger"}
              />
              <Kpi
                label="حجم معاملات امروز"
                value={formatNum(stock.quote.volume, 0)}
                hint={stock.quote.status}
              />
              <Kpi
                label="تغییر هفته / ماه"
                value={`${formatNum(stock.quote.week_change_pct)}٪`}
                hint={`ماهانه ${formatNum(stock.quote.month_change_pct)}٪`}
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
                مشاهده تابلو و نمودار لحظه‌ای شکربن
              </button>
              <button type="button" className="btn" onClick={() => setTab("export")}>
                بازارهای صادراتی و پیش‌بینی
              </button>
            </div>

            <Panel title="تولیدات فعلی کربن ایران">
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
                    <span className="badge ok">در تولید</span>
                  </button>
                ))}
              </div>
            </Panel>

            <Panel title="قیمت مواد اولیه و بهترین منبع خرید">
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>ماده</th>
                      <th>قیمت جاری</th>
                      <th>بهترین تأمین‌کننده</th>
                      <th>روند</th>
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
                            {m.trend === "up" ? "صعودی" : m.trend === "down" ? "نزولی" : "پایدار"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>

            <div className="grid two">
              <Panel title="جریان نقدی و ریسک نقدینگی">
                <div className="list-row">
                  <span>خالص پیش‌بینی‌شده</span>
                  <strong>{formatIrr(Number(finance?.cashflow?.net_cashflow ?? 0))}</strong>
                </div>
                <div className="list-row">
                  <span>ورود / خروج</span>
                  <span>
                    {formatIrr(Number(finance?.cashflow?.projected_inflow ?? 0))} /{" "}
                    {formatIrr(Number(finance?.cashflow?.projected_outflow ?? 0))}
                  </span>
                </div>
                <div className="list-row">
                  <span>سطح ریسک</span>
                  <span className={`badge ${finance?.cashflow?.liquidity_risk === "low" ? "ok" : "warn"}`}>
                    {finance?.cashflow?.liquidity_risk ?? "—"}
                  </span>
                </div>
              </Panel>

              <Panel title="بلوغ و بازگشت سرمایه">
                <div className="list-row">
                  <span>بلوغ محصول</span>
                  <strong>{formatNum(maturity?.latest_roi?.maturity_pct ?? 0)}٪</strong>
                </div>
                <div className="bar-track" style={{ margin: "0.4rem 0 0.9rem" }}>
                  <div
                    className="bar-fill"
                    style={{ width: `${Math.min(100, Number(maturity?.latest_roi?.maturity_pct ?? 0))}%` }}
                  />
                </div>
                <div className="list-row">
                  <span>منافع سالانه</span>
                  <strong>{formatIrr(Number(maturity?.latest_roi?.annual_benefits_irr ?? 0))}</strong>
                </div>
                <div className="list-row">
                  <span>دوره بازگشت</span>
                  <span>
                    {formatNum(maturity?.latest_roi?.payback_months ?? 0)} ماه
                    {maturity?.latest_roi?.on_track ? (
                      <span className="badge ok" style={{ marginRight: "0.4rem" }}>
                        در مسیر
                      </span>
                    ) : null}
                  </span>
                </div>
              </Panel>
            </div>

            <div className="grid two">
              <Panel title="وضعیت سرویس‌ها">
                <table>
                  <thead>
                    <tr>
                      <th>سرویس</th>
                      <th>وضعیت</th>
                      <th>تأخیر (ms)</th>
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

              <Panel title="برنامه تولید پرمارژین">
                <table>
                  <thead>
                    <tr>
                      <th>گرید</th>
                      <th>مقدار (kg)</th>
                      <th>مارژین</th>
                      <th>خط</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(finance?.high_margin_production ?? []).map((row, idx) => (
                      <tr key={`${row.product_grade}-${idx}`}>
                        <td>{String(row.product_grade)}</td>
                        <td>{formatNum(Number(row.planned_quantity_kg), 0)}</td>
                        <td>{formatNum(Number(row.margin_score) * 100)}٪</td>
                        <td>{String(row.production_line ?? "—")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {(finance?.high_margin_production?.length ?? 0) === 0 ? (
                  <div className="empty">هنوز برنامه تولیدی ثبت نشده است.</div>
                ) : null}
              </Panel>
            </div>
          </div>
        ) : null}

        {!error && tab === "products" ? (
          <div className="stack">
            <div className="grid kpi">
              <Kpi label="گرید در تولید" value={formatNum(catalog.count, 0)} hint="برگه مشخصات کیفیت" tone="ok" />
              <Kpi
                label="خانواده‌ها"
                value={formatNum(catalog.classifications?.length ?? new Set(catalog.products.map((p) => p.classification)).size, 0)}
                hint={(catalog.classifications ?? [...new Set(catalog.products.map((p) => p.classification))]).join(" · ")}
              />
              <Kpi
                label="گرید انتخاب‌شده"
                value={selectedProduct?.code ?? "—"}
                hint={selectedProduct?.classification ?? ""}
                tone="ok"
              />
              <Kpi label="روش‌های ASTM" value={formatNum(catalog.comparison.length, 0)} hint="شاخص کنترل کیفیت" />
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
                  <span className="badge ok">در تولید</span>
                </button>
              ))}
            </div>

            {selectedProduct ? (
              <div className="grid two">
                <Panel title={`شناسنامه محصول — ${selectedProduct.code}`}>
                  <div className="list-row">
                    <span>کد ASTM</span>
                    <strong>{selectedProduct.astm_code}</strong>
                  </div>
                  <div className="list-row">
                    <span>نام تجاری</span>
                    <strong>{selectedProduct.trade_name}</strong>
                  </div>
                  <div className="list-row">
                    <span>نسخه / واریانت</span>
                    <strong>{selectedProduct.variant ?? "—"}</strong>
                  </div>
                  <div className="list-row">
                    <span>طبقه‌بندی</span>
                    <strong>{selectedProduct.classification}</strong>
                  </div>
                  <div className="list-row">
                    <span>وضعیت</span>
                    <span className="badge ok">تولید جاری</span>
                  </div>
                  <p className="grade-desc" style={{ marginTop: "0.85rem" }}>
                    {selectedProduct.description_fa}
                  </p>
                </Panel>

                <Panel title="مشخصات کیفیت کامل (Quality Specification)">
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>شاخص</th>
                          <th>ASTM</th>
                          <th>مشخصات</th>
                          <th>واحد</th>
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

            <Panel title="جدول مقایسه‌ای مشخصات کیفیت (Quality Specification)">
              <div className="table-scroll">
                <table className="spec-table">
                  <thead>
                    <tr>
                      <th>شاخص / آزمون</th>
                      <th>ASTM</th>
                      <th>واحد</th>
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
              {catalog.source ? <p className="source-note">منبع: {catalog.source}</p> : null}
            </Panel>
          </div>
        ) : null}

        {!error && tab === "supply" ? (
          <div className="stack">
            <div className="grid kpi">
              <Kpi
                label="منابع خرید"
                value={formatNum(procurement.summary?.supplier_count ?? procurement.suppliers.length, 0)}
                hint="تأمین‌کنندگان فعال"
                tone="ok"
              />
              <Kpi
                label="مواد اولیه"
                value={formatNum(procurement.summary?.material_count ?? procurement.materials.length, 0)}
                hint="خوراک و انرژی فرآیند"
              />
              <Kpi
                label="بهترین قیمت CBFS"
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
                label="منبع داده"
                value={procurement.materials[0]?.price_source === "database" ? "زنده" : "کاتالوگ"}
                hint={procurement.updated_label ?? ""}
              />
            </div>

            <Panel title="تابلوی قیمت به‌روز مواد اولیه">
              <div className="table-scroll">
                <table className="spec-table">
                  <thead>
                    <tr>
                      <th>ماده</th>
                      <th>دسته</th>
                      <th>قیمت جاری</th>
                      <th>میانگین پیشنهادها</th>
                      <th>تغییر ۷ روز</th>
                      <th>روند</th>
                      <th>بهترین تأمین‌کننده</th>
                      <th>واحد</th>
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
                            : `${m.change_pct_7d > 0 ? "+" : ""}${formatNum(m.change_pct_7d)}٪`}
                        </td>
                        <td>
                          <span
                            className={`badge ${
                              m.trend === "up" ? "danger" : m.trend === "down" ? "ok" : "neutral"
                            }`}
                          >
                            {m.trend === "up" ? "صعودی" : m.trend === "down" ? "نزولی" : "پایدار"}
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
              {procurement.source ? <p className="source-note">منبع: {procurement.source}</p> : null}
            </Panel>

            {selectedMat ? (
              <div className="grid two">
                <Panel title={`پیشنهادهای خرید — ${selectedMat.name_fa}`}>
                  <table>
                    <thead>
                      <tr>
                        <th>تأمین‌کننده</th>
                        <th>شهر</th>
                        <th>قیمت</th>
                        <th>تحویل (روز)</th>
                        <th>امتیاز</th>
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
                        <span>پیش‌بینی قیمت</span>
                        <strong>{formatIrr(selectedMat.forecast.predicted_price_irr)}</strong>
                      </div>
                      <div className="list-row">
                        <span>توصیه خرید</span>
                        <span className="badge warn">{selectedMat.forecast.recommendation}</span>
                      </div>
                    </div>
                  ) : null}
                </Panel>

                <Panel title="شناسنامه ماده">
                  <div className="list-row">
                    <span>اهمیت</span>
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
                    <span>سهم تقریبی هزینه</span>
                    <strong>{formatNum(selectedMat.typical_share_pct, 0)}٪</strong>
                  </div>
                  <div className="list-row">
                    <span>دسته</span>
                    <strong>{selectedMat.category}</strong>
                  </div>
                  <div className="list-row">
                    <span>آخرین به‌روزرسانی بازار</span>
                    <span>{selectedMat.market_as_of ?? "کاتالوگ"}</span>
                  </div>
                </Panel>
              </div>
            ) : null}

            <Panel title="منابع خرید (تأمین‌کنندگان)">
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>کد</th>
                      <th>نام</th>
                      <th>نوع</th>
                      <th>موقعیت</th>
                      <th>امتیاز</th>
                      <th>قابلیت تحویل</th>
                      <th>کیفیت</th>
                      <th>شرایط پرداخت</th>
                      <th>توضیح</th>
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
                        <td>{formatNum(s.delivery_reliability * 100, 0)}٪</td>
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
                label="کل سنسورها"
                value={formatNum(allSensors.length, 0)}
                hint={`${formatNum(equipmentBoard.summary.equipment_count, 0)} تجهیز`}
                tone="ok"
              />
              <Kpi
                label="چراغ سبز"
                value={formatNum(lampCounts.ok, 0)}
                hint="در محدوده عملیاتی"
                tone="ok"
              />
              <Kpi
                label="چراغ زرد"
                value={formatNum(lampCounts.warning, 0)}
                hint="نزدیک حد / هشدار"
                tone={lampCounts.warning ? "warn" : "ok"}
              />
              <Kpi
                label="چراغ قرمز"
                value={formatNum(lampCounts.critical, 0)}
                hint={`${formatNum(equipmentBoard.summary.open_process_alerts, 0)} هشدار فرآیند`}
                tone={lampCounts.critical ? "danger" : "ok"}
              />
            </div>

            <Panel title="تابلوی چراغی سنسورها — محدوده عملکردی">
              <p className="kpi-hint" style={{ marginBottom: "0.75rem" }}>
                سبز = در محدوده · زرد = نزدیک حد عملیاتی (±۱۰٪ لبه) · قرمز = خارج از محدوده · واحد و مقدار عملکردی روی هر کارت
              </p>
              <div className="lamp-filter-row">
                {(
                  [
                    ["all", `همه (${allSensors.length})`],
                    ["ok", `سبز (${lampCounts.ok})`],
                    ["warning", `زرد (${lampCounts.warning})`],
                    ["critical", `قرمز (${lampCounts.critical})`],
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
              {filteredSensors.length === 0 ? <div className="empty">سنسوری با این فیلتر نیست.</div> : null}
            </Panel>

            <Panel title="تابلوی تجهیزات خط تولید کربن بلک">
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>کد</th>
                      <th>تجهیز</th>
                      <th>ناحیه</th>
                      <th>خط</th>
                      <th>سنسورها</th>
                      <th>خارج از رنج</th>
                      <th>وضعیت کارکرد</th>
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
              {equipmentBoard.source ? <p className="source-note">منبع: {equipmentBoard.source}</p> : null}
            </Panel>

            {selectedEquip ? (
              <Panel title={`جزئیات سنسورها — ${selectedEquip.name_fa}`}>
                <div className="list-row">
                  <span>وضعیت کارکرد</span>
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
                  <span>منبع جمع‌آوری داده</span>
                  <strong>
                    {loggerKindLabel(selectedEquip.data_logger?.kind)} —{" "}
                    {selectedEquip.data_logger?.name_fa ?? selectedEquip.data_logger_id ?? "—"}
                  </strong>
                </div>
                <div className="list-row">
                  <span>پروتکل / آدرس</span>
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

            <Panel title="لایه‌های جمع‌آوری داده — PLC / SCADA / Data Logger">
              <p className="kpi-hint" style={{ marginBottom: "0.75rem" }}>
                Data Logger می‌تواند دروازه PLC یا نود SCADA باشد؛ هر سنسور به یکی از این منابع متصل است.
              </p>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>کد</th>
                      <th>نام</th>
                      <th>نوع</th>
                      <th>پروتکل</th>
                      <th>میزبان</th>
                      <th>بازه نمونه‌برداری</th>
                      <th>وضعیت</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(equipmentBoard.data_loggers ?? []).map((d) => (
                      <tr key={d.id}>
                        <td>{d.id}</td>
                        <td>
                          <strong>{d.name_fa}</strong>
                          <div className="kpi-hint">{(d.areas ?? []).join("، ")}</div>
                        </td>
                        <td>
                          <span className="badge ok">{loggerKindLabel(d.kind)}</span>
                        </td>
                        <td>{d.protocol}</td>
                        <td>{d.host ?? "—"}</td>
                        <td>{d.poll_interval_s != null ? `${d.poll_interval_s} ثانیه` : "—"}</td>
                        <td>
                          <span className={`badge ${d.status === "online" ? "ok" : "warn"}`}>
                            {d.status === "online" ? "آنلاین" : d.status ?? "—"}
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
                  hint="کنترل‌گر منطقی"
                />
                <Kpi
                  label="SCADA"
                  value={formatNum(equipmentBoard.summary.scada_count ?? 0, 0)}
                  hint="نظارتی مرکزی"
                />
                <Kpi
                  label="Data Logger"
                  value={formatNum(equipmentBoard.summary.data_logger_count ?? 0, 0)}
                  hint="ثبت و ارسال لبه"
                />
              </div>
            </Panel>

            <div className="grid two">
              <Panel title="هشدار عملکرد خارج از محدوده عملیاتی">
                {equipmentBoard.process_alerts.length === 0 ? (
                  <div className="empty">همه سنسورها در محدوده مجاز هستند.</div>
                ) : (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>تجهیز</th>
                          <th>سنسور</th>
                          <th>مقدار</th>
                          <th>رنج مجاز</th>
                          <th>شدت</th>
                        </tr>
                      </thead>
                      <tbody>
                        {equipmentBoard.process_alerts.map((a, idx) => (
                          <tr key={`${a.equipment_id}-${a.sensor_key}-${idx}`}>
                            <td>{a.equipment_name ?? a.equipment_id}</td>
                            <td>{a.sensor_name ?? a.sensor_key}</td>
                            <td>
                              <strong>
                                {formatNum(Number(a.measured_value ?? a.value ?? 0), 2)} {a.unit ?? ""}
                              </strong>
                            </td>
                            <td>
                              {formatNum(Number(a.min_op ?? 0), 2)} – {formatNum(Number(a.max_op ?? 0), 2)}
                            </td>
                            <td>
                              <span className={`badge ${a.severity === "critical" ? "danger" : "warn"}`}>
                                {a.severity === "critical" ? "بحرانی" : "هشدار"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Panel>

              <Panel title="هشدارهای نگهداری پیش‌بینانه (RUL)">
                {energyAlerts.length === 0 ? (
                  <div className="empty">هشدار RUL بازی نیست.</div>
                ) : (
                  <table>
                    <thead>
                      <tr>
                        <th>تجهیز</th>
                        <th>شدت</th>
                        <th>RUL (روز)</th>
                        <th>پیام</th>
                      </tr>
                    </thead>
                    <tbody>
                      {energyAlerts.map((a) => (
                        <tr key={String(a.id)}>
                          <td>{String(a.equipment_id)}</td>
                          <td>
                            <span className={`badge ${a.severity === "critical" ? "danger" : "warn"}`}>
                              {String(a.severity)}
                            </span>
                          </td>
                          <td>{formatNum(Number(a.rul_days))}</td>
                          <td>{String(a.message)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                {equipment.length > 0 ? (
                  <p className="source-note" style={{ marginTop: "0.75rem" }}>
                    دارایی‌های ثبت‌شده در DB: {equipment.length}
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
                label="بچ‌های فعال"
                value={formatNum(Number(finance?.production?.open_batches ?? 0), 0)}
              />
              <Kpi
                label="گریدهای فعال"
                value={formatNum(Number(finance?.production?.active_grades ?? 0), 0)}
              />
              <Kpi
                label="ناهنجاری ۲۴ ساعت"
                value={formatNum(Number(finance?.quality_anomalies_24h ?? 0), 0)}
                tone={(finance?.quality_anomalies_24h ?? 0) > 0 ? "warn" : "ok"}
              />
            </div>
            <Panel title="رویدادهای ناهنجاری کیفیت">
              <table>
                <thead>
                  <tr>
                    <th>زمان</th>
                    <th>بچ</th>
                    <th>گرید</th>
                    <th>امتیاز</th>
                    <th>وضعیت</th>
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
                          {e.is_anomaly ? "ناهنجار" : "نرمال"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {anomalyEvents.length === 0 ? <div className="empty">رویدادی ثبت نشده است.</div> : null}
            </Panel>

            <Panel title="گریدهای جاری و حدود کنترل کیفیت">
              <div className="table-scroll">
                <table className="spec-table">
                  <thead>
                    <tr>
                      <th>گرید</th>
                      <th>نام تجاری</th>
                      <th>عدد ید</th>
                      <th>DBP</th>
                      <th>سطح ویژه N₂</th>
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
                label="امتیاز تعادل سناریو"
                value={formatNum(marketScenarios.summary.balance_score, 0)}
                hint={marketScenarios.selected_scenario.name_fa}
                tone={marketScenarios.summary.balance_score >= 85 ? "ok" : "warn"}
              />
              <Kpi
                label="ریسک انبارداری"
                value={marketScenarios.summary.warehouse_risk}
                hint={`${formatNum(marketScenarios.summary.total_excess_inventory_kg / 1000, 1)} تن مازاد`}
                tone={riskTone(marketScenarios.summary.warehouse_risk)}
              />
              <Kpi
                label="ریسک صف فروش"
                value={marketScenarios.summary.sales_queue_risk}
                hint={`${formatNum(marketScenarios.summary.total_sales_queue_kg / 1000, 1)} تن در صف`}
                tone={riskTone(marketScenarios.summary.sales_queue_risk)}
              />
              <Kpi
                label="ریسک صف خرید مواد"
                value={marketScenarios.summary.purchase_queue_risk}
                hint={`خوراک ${formatNum(marketScenarios.macros.current.feedstock_basket_irr, 0)} ریال`}
                tone={riskTone(marketScenarios.summary.purchase_queue_risk)}
              />
            </div>

            <Panel title="سناریوی تولید گریدها — نوسان دلار · طلا · نفت · مواد خام">
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
                  label="دلار (ریال)"
                  value={formatNum(marketScenarios.macros.current.usd_irr, 0)}
                  hint={`${formatNum(marketScenarios.macros.deltas_pct.usd_irr)}٪ نسبت به پایه`}
                  tone={marketScenarios.macros.deltas_pct.usd_irr > 5 ? "warn" : "neutral"}
                />
                <Kpi
                  label="طلا (ریال/گرم)"
                  value={formatNum(marketScenarios.macros.current.gold_irr_g, 0)}
                  hint={`${formatNum(marketScenarios.macros.deltas_pct.gold_irr_g)}٪`}
                  tone={marketScenarios.macros.deltas_pct.gold_irr_g > 5 ? "warn" : "neutral"}
                />
                <Kpi
                  label="نفت برنت (USD)"
                  value={formatNum(marketScenarios.macros.current.oil_usd, 1)}
                  hint={`${formatNum(marketScenarios.macros.deltas_pct.oil_usd)}٪`}
                />
                <Kpi
                  label="سبد مواد خام"
                  value={formatNum(marketScenarios.macros.current.feedstock_basket_irr, 0)}
                  hint={`${formatNum(marketScenarios.macros.deltas_pct.feedstock_basket_irr)}٪ · فشار ${formatNum(marketScenarios.macros.indices.cost_pressure ?? 1, 2)}`}
                  tone={(marketScenarios.macros.indices.cost_pressure ?? 1) > 1.1 ? "danger" : "ok"}
                />
              </div>

              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>گرید</th>
                      <th>اقدام</th>
                      <th>تولید (تن)</th>
                      <th>صف فروش</th>
                      <th>موجودی</th>
                      <th>مازاد انبار</th>
                      <th>مارژین تعدیل‌شده</th>
                      <th>خرید مواد</th>
                      <th>دلیل</th>
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
                          <div className="kpi-hint">{formatNum(g.inventory_cover_days, 0)} روز پوشش</div>
                        </td>
                        <td>{formatNum(g.excess_inventory_kg / 1000, 1)}</td>
                        <td>
                          {formatNum(g.adjusted_margin * 100)}٪
                          <div className="kpi-hint">پایه {formatNum(g.base_margin * 100)}٪</div>
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
              <Panel title="مقایسه سناریوهای بازار">
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>سناریو</th>
                        <th>امتیاز</th>
                        <th>انبار</th>
                        <th>صف فروش</th>
                        <th>صف خرید</th>
                        <th>گریدهای اول</th>
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
                            {c.recommended ? <span className="badge ok" style={{ marginRight: "0.35rem" }}>پیشنهادی</span> : null}
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
              <Panel title="اقدام خرید مواد خام (ضد صف خرید)">
                <table>
                  <thead>
                    <tr>
                      <th>گرید</th>
                      <th>توصیه</th>
                      <th>نیاز خوراک (تن)</th>
                      <th>یادداشت</th>
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
                  <div className="empty">خرید مواد در حالت نگهداری — صف خرید اضافی لازم نیست.</div>
                ) : null}
              </Panel>
            </div>

            <div className="grid kpi">
              <Kpi
                label="تقاضای کل (تن)"
                value={formatNum(productionBoard.summary.total_demand_kg / 1000, 1)}
                hint={`افق ${formatNum(productionBoard.horizon_days, 0)} روز`}
              />
              <Kpi
                label="برنامه تولید (تن)"
                value={formatNum(productionBoard.summary.total_planned_kg / 1000, 1)}
                hint={`پوشش ظرفیت ${formatNum(productionBoard.summary.coverage_pct)}٪`}
                tone={productionBoard.summary.coverage_pct >= 85 ? "ok" : "warn"}
              />
              <Kpi
                label="زمان‌بندی‌شده (تن)"
                value={formatNum(productionBoard.summary.total_scheduled_kg / 1000, 1)}
                hint={`${formatNum(productionBoard.summary.schedule_slots, 0)} نوبت · ${productionBoard.schedule_days} روز`}
                tone="ok"
              />
              <Kpi
                label="عقب‌افتادگی (تن)"
                value={formatNum(productionBoard.summary.backlog_kg / 1000, 1)}
                hint={productionBoard.summary.lines_used.join(" · ") || "—"}
                tone={productionBoard.summary.backlog_kg > 0 ? "warn" : "ok"}
              />
            </div>

            <Panel title="برنامه تولید مبتنی بر تقاضا">
              <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "0.75rem" }}>
                <button
                  type="button"
                  className="btn primary"
                  disabled={planGenerating || loading}
                  onClick={() => void generateProductionPlan()}
                >
                  {planGenerating ? "در حال ایجاد…" : "ایجاد برنامه از تقاضا"}
                </button>
                <span className="kpi-hint" style={{ alignSelf: "center" }}>
                  {productionBoard.source ?? "پایه + صف فروش + صادرات → ظرفیت خط"}
                </span>
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>گرید</th>
                      <th>پایه</th>
                      <th>صف فروش</th>
                      <th>صادرات</th>
                      <th>تقاضای کل</th>
                      <th>ایمنی</th>
                      <th>برنامه</th>
                      <th>خط</th>
                      <th>مارژین</th>
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
                        <td>{formatNum(r.margin_score * 100)}٪</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="kpi-hint" style={{ marginTop: "0.5rem" }}>
                مقادیر به تن · ترکیب تقاضا: ۵۵٪ پایه تاریخی · ۳۰٪ صف فروش · ۱۵٪ سهم صادرات
              </div>
            </Panel>

            <div className="grid two">
              <Panel title={`زمان‌بندی تولید (${productionBoard.schedule_days} روز)`}>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>تاریخ</th>
                        <th>گرید</th>
                        <th>خط</th>
                        <th>مقدار (تن)</th>
                        <th>بهره‌برداری</th>
                        <th>منبع</th>
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
                            <td>{formatNum(s.line_utilization_pct)}٪</td>
                            <td>{s.demand_source === "forecast+sales+export" ? "تقاضا" : s.demand_source}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
                {productionBoard.schedule.filter((s) => s.demand_source === "backlog").length > 0 ? (
                  <div className="kpi-hint" style={{ marginTop: "0.5rem" }}>
                    عقب‌افتادگی:{" "}
                    {productionBoard.schedule
                      .filter((s) => s.demand_source === "backlog")
                      .map((s) => `${s.product_grade} ${formatNum(s.quantity_kg / 1000, 1)}ت`)
                      .join(" · ")}
                  </div>
                ) : null}
              </Panel>
              <Panel title="اقدامات موجودی">
                <table>
                  <thead>
                    <tr>
                      <th>گرید</th>
                      <th>اقدام</th>
                      <th>مقدار</th>
                      <th>صرفه‌جویی برآوردی</th>
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
                {inventoryActions.length === 0 ? <div className="empty">اقدامی ثبت نشده.</div> : null}
              </Panel>
            </div>

            <div className="grid two">
              <Panel title="برنامه‌های ذخیره‌شده">
                <table>
                  <thead>
                    <tr>
                      <th>گرید</th>
                      <th>مقدار برنامه‌ای</th>
                      <th>موجودی ایمنی</th>
                      <th>خط</th>
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
                {plans.length === 0 ? <div className="empty">برنامه‌ای موجود نیست — دکمه ایجاد را بزنید.</div> : null}
              </Panel>
              <Panel title="گریدهای پرمارژین پیشنهادی">
                <div className="grid three">
                  {(portfolio?.high_margin_focus ?? productionBoard.demand_by_grade.slice(0, 3)).map((g) => (
                    <div className="panel" key={String(g.product_grade)} style={{ boxShadow: "none" }}>
                      <div className="kpi-value">{String(g.product_grade)}</div>
                      <div className="kpi-label">
                        مارژین {formatNum(Number(g.margin_score) * 100)}٪
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
                label="مشتریان فعال"
                value={formatNum(salesPipeline.summary.active_count, 0)}
                hint={`${formatNum(salesPipeline.summary.active_monthly_tonnage_kg / 1000, 1)} تن/ماه`}
                tone="ok"
              />
              <Kpi
                label="مشتریان بالقوه"
                value={formatNum(salesPipeline.summary.potential_count, 0)}
                hint={`${formatNum(salesPipeline.summary.potential_monthly_tonnage_kg / 1000, 1)} تن/ماه`}
              />
              <Kpi
                label="صف خرید (تن درخواستی)"
                value={formatNum(salesPipeline.summary.queue_requested_tonnage_kg / 1000, 1)}
                hint={`${formatNum(salesPipeline.summary.queue_items, 0)} قلم · وزن‌دار ${formatNum(salesPipeline.summary.queue_weighted_tonnage_kg / 1000, 1)} تن`}
                tone="warn"
              />
              <Kpi
                label="حاشیه سود"
                value={`${formatNum(Number(finance?.finance?.profit_margin ?? 0) * 100)}٪`}
              />
            </div>

            <div className="grid two">
              <Panel title="مشتریان فعال — تناژ ماهانه">
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>مشتری</th>
                        <th>منطقه</th>
                        <th>تناژ ماهانه (kg)</th>
                        <th>گرید ترجیحی</th>
                        <th>رابط</th>
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

              <Panel title="مشتریان بالقوه — تناژ هدف">
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>مشتری</th>
                        <th>مرحله</th>
                        <th>تناژ هدف (kg)</th>
                        <th>گرید</th>
                        <th>رابط</th>
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

            <Panel title="صف خرید (Purchase Queue)">
              <div className="table-scroll">
                <table className="spec-table">
                  <thead>
                    <tr>
                      <th>اولویت</th>
                      <th>مشتری</th>
                      <th>وضعیت مشتری</th>
                      <th>گرید</th>
                      <th>تناژ درخواستی</th>
                      <th>احتمال</th>
                      <th>تناژ وزن‌دار</th>
                      <th>وضعیت صف</th>
                      <th>قیمت واحد</th>
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
                            {q.customer_status === "active" ? "فعال" : "بالقوه"}
                          </span>
                        </td>
                        <td>
                          <strong>{q.grade}</strong>
                        </td>
                        <td>{formatNum(q.requested_tonnage_kg, 0)}</td>
                        <td>{formatNum(q.probability * 100, 0)}٪</td>
                        <td>{formatNum(q.weighted_tonnage_kg ?? q.requested_tonnage_kg * q.probability, 0)}</td>
                        <td>{q.status}</td>
                        <td>{formatIrr(q.unit_price_irr)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>

            <Panel title="پیش‌بینی فروش (ML + صف خرید)">
              <div className="table-scroll">
                <table className="spec-table">
                  <thead>
                    <tr>
                      <th>گرید</th>
                      <th>پایه ML (kg)</th>
                      <th>صف — درخواستی</th>
                      <th>صف — وزن‌دار</th>
                      <th>پیش‌بینی ترکیبی</th>
                      <th>سهم پایپ‌لاین</th>
                      <th>درآمد پیش‌بینی</th>
                      <th>قیمت پیشنهادی</th>
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
                        <td>{formatNum(f.pipeline_share_pct ?? 0)}٪</td>
                        <td>{formatIrr(f.forecast_revenue_irr)}</td>
                        <td>{formatIrr(f.recommended_unit_price)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {salesPipeline.source ? <p className="source-note">منبع: {salesPipeline.source}</p> : null}
            </Panel>

            <div className="grid two">
              <Panel title="پیش‌بینی‌های ذخیره‌شده">
                <table>
                  <thead>
                    <tr>
                      <th>گرید</th>
                      <th>مقدار</th>
                      <th>درآمد</th>
                      <th>قیمت پیشنهادی</th>
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
              <Panel title="CRM — مشتریان در معرض ریزش">
                <table>
                  <thead>
                    <tr>
                      <th>مشتری</th>
                      <th>ریسک</th>
                      <th>ارزش طول عمر</th>
                    </tr>
                  </thead>
                  <tbody>
                    {customersAtRisk.map((c) => (
                      <tr key={String(c.id)}>
                        <td>{String(c.name)}</td>
                        <td>{formatNum(Number(c.churn_risk) * 100)}٪</td>
                        <td>{formatIrr(Number(c.lifetime_value_irr))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {customersAtRisk.length === 0 ? <div className="empty">موردی نیست.</div> : null}
              </Panel>
            </div>
          </div>
        ) : null}

        {!error && tab === "export" ? (
          <div className="stack">
            <div className="grid kpi">
              <Kpi
                label="بازارهای بالفعل"
                value={formatNum(exportBoard.summary.actual_markets_count, 0)}
                hint={`برتر: ${exportBoard.summary.top_market}`}
                tone="ok"
              />
              <Kpi
                label="بازارهای بالقوه"
                value={formatNum(exportBoard.summary.potential_markets_count, 0)}
                hint={`وزن‌دار ${formatNum(exportBoard.summary.potential_weighted_tonnage_kg / 1000, 0)} تن/سال`}
              />
              <Kpi
                label="صادرات YTD"
                value={`${formatNum(exportBoard.summary.ytd_export_tonnage_kg / 1000, 0)} تن`}
                hint={`سالانه بالفعل ${formatNum(exportBoard.summary.annual_actual_tonnage_kg / 1000, 0)} تن`}
                tone="ok"
              />
              <Kpi
                label="پیش‌بینی ۶ ماه"
                value={`${formatNum(exportBoard.summary.six_month_forecast_kg / 1000, 0)} تن`}
                hint={`${formatNum(exportBoard.summary.six_month_revenue_usd, 0)} USD`}
              />
            </div>

            <Panel title={`${exportBoard.company ?? "کربن ایران"} — HS ${exportBoard.hs_code ?? "280300"}`}>
              <p className="kpi-hint" style={{ marginBottom: "0.75rem" }}>
                {exportBoard.product} · رشد میانگین بازارهای بالفعل{" "}
                {formatNum(exportBoard.summary.avg_growth_yoy_pct)}٪ سالانه
              </p>
              <ExportForecastChart rows={exportBoard.export_forecast} />
              {exportBoard.source ? <p className="source-note">منبع: {exportBoard.source}</p> : null}
            </Panel>

            <div className="grid two">
              <Panel title="بازارهای بالفعل صادراتی">
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>کشور</th>
                        <th>YTD (تن)</th>
                        <th>سالانه (تن)</th>
                        <th>سهم٪</th>
                        <th>رشد٪</th>
                        <th>FOB $</th>
                        <th>گریدها</th>
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
                              {formatNum(m.growth_yoy_pct ?? 0)}٪
                            </span>
                          </td>
                          <td>{formatNum(m.avg_fob_usd ?? 0, 0)}</td>
                          <td>{(m.main_grades ?? []).join("، ")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>

              <Panel title="بازارهای بالقوه">
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>کشور</th>
                        <th>هدف سالانه</th>
                        <th>احتمال</th>
                        <th>مرحله</th>
                        <th>رشد٪</th>
                        <th>ریسک</th>
                      </tr>
                    </thead>
                    <tbody>
                      {exportBoard.potential_markets.map((m) => (
                        <tr key={m.id}>
                          <td>
                            <strong>{m.country_fa}</strong>
                            <div className="kpi-hint">{(m.main_grades ?? []).join("، ")}</div>
                          </td>
                          <td>{formatNum(m.annual_tonnage_kg / 1000, 0)} تن</td>
                          <td>{formatNum((m.probability ?? 0) * 100, 0)}٪</td>
                          <td>
                            <span className="badge">
                              {{
                                technical_eval: "ارزیابی فنی",
                                negotiation: "مذاکره",
                                lead: "سرنخ",
                                market_study: "مطالعه بازار",
                              }[m.pipeline_stage ?? ""] ?? m.pipeline_stage ?? "—"}
                            </span>
                          </td>
                          <td>
                            <span className="badge ok">{formatNum(m.growth_yoy_pct ?? 0)}٪</span>
                          </td>
                          <td>{m.risk ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>
            </div>

            <Panel title="جدول پیش‌بینی صادرات (۶ ماه)">
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>ماه</th>
                      <th>پایه بالفعل</th>
                      <th>افزایش بالقوه</th>
                      <th>جمع پیش‌بینی</th>
                      <th>درآمد USD</th>
                      <th>درآمد ریال</th>
                      <th>FOB</th>
                      <th>اطمینان</th>
                    </tr>
                  </thead>
                  <tbody>
                    {exportBoard.export_forecast.map((f) => (
                      <tr key={f.month}>
                        <td>{f.month}</td>
                        <td>{formatNum(f.baseline_tonnage_kg / 1000, 1)} تن</td>
                        <td>{formatNum(f.pipeline_uplift_kg / 1000, 1)} تن</td>
                        <td>
                          <strong>{formatNum(f.forecast_tonnage_kg / 1000, 1)} تن</strong>
                        </td>
                        <td>{formatNum(f.forecast_revenue_usd, 0)}</td>
                        <td>{formatIrr(f.forecast_revenue_irr)}</td>
                        <td>{formatNum(f.avg_fob_usd, 0)}</td>
                        <td>{formatNum(f.confidence * 100, 0)}٪</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>

            <Panel title="منابع ایرانی مرجع">
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>منبع</th>
                      <th>نقش در داشبورد</th>
                      <th>آدرس</th>
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
                label={`آخرین قیمت ${stock.ticker.symbol_fa}`}
                value={formatNum(stock.quote.last_price, 0)}
                hint={stock.ticker.isin}
                tone={stock.quote.trend === "up" ? "ok" : "danger"}
              />
              <Kpi
                label="تغییر امروز"
                value={`${stock.quote.day_change_pct > 0 ? "+" : ""}${formatNum(stock.quote.day_change_pct)}٪`}
                hint={`${stock.quote.day_change > 0 ? "+" : ""}${formatNum(stock.quote.day_change, 0)} ریال`}
                tone={stock.quote.day_change_pct >= 0 ? "ok" : "danger"}
              />
              <Kpi
                label="هفته / ماه"
                value={`${formatNum(stock.quote.week_change_pct)}٪`}
                hint={`ماهانه ${formatNum(stock.quote.month_change_pct)}٪`}
                tone={stock.quote.month_change_pct >= 0 ? "ok" : "danger"}
              />
              <Kpi
                label="حجم معاملات"
                value={formatNum(stock.quote.volume, 0)}
                hint={`${formatNum(stock.quote.trade_count, 0)} معامله`}
              />
            </div>

            <Panel title={`${stock.ticker.company_fa} — ${stock.ticker.symbol_fa} (${stock.ticker.symbol_en})`}>
              <div className="list-row">
                <span>بازار</span>
                <strong>{stock.ticker.market}</strong>
              </div>
              <div className="list-row">
                <span>صنعت</span>
                <strong>{stock.ticker.industry}</strong>
              </div>
              <div className="list-row">
                <span>وضعیت</span>
                <span className={`badge ${stock.quote.trend === "up" ? "ok" : "danger"}`}>
                  {stock.quote.status}
                </span>
              </div>
              <div className="list-row">
                <span>به‌روزرسانی</span>
                <span>{stock.quote.as_of}</span>
              </div>
              <div className="actions" style={{ marginTop: "0.85rem" }}>
                <button
                  type="button"
                  className={`btn ${stockMode === "intraday" ? "primary" : ""}`}
                  onClick={() => setStockMode("intraday")}
                >
                  نمودار لحظه‌ای امروز
                </button>
                <button
                  type="button"
                  className={`btn ${stockMode === "daily" ? "primary" : ""}`}
                  onClick={() => setStockMode("daily")}
                >
                  تاریخچه روزانه
                </button>
                <button type="button" className="btn" onClick={() => void loadStock()}>
                  تازه‌سازی قیمت
                </button>
              </div>
              <div style={{ marginTop: "1rem" }}>
                <StockChart
                  points={stockMode === "intraday" ? stock.intraday : stock.history_daily}
                  mode={stockMode}
                  up={stock.quote.trend === "up"}
                />
              </div>
              {stock.source ? <p className="source-note">منبع: {stock.source}</p> : null}
            </Panel>

            <div className="grid two">
              <Panel title="جزئیات خرید و فروش (معاملات اخیر)">
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>زمان</th>
                        <th>سمت</th>
                        <th>قیمت</th>
                        <th>حجم</th>
                        <th>ارزش</th>
                        <th>کارگزار</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stock.recent_trades.map((t, idx) => (
                        <tr key={`${t.id ?? idx}-${t.time}`}>
                          <td>{String(t.time).replace("T", " ").slice(0, 19)}</td>
                          <td>
                            <span className={`badge ${t.side === "buy" ? "ok" : "danger"}`}>
                              {t.side === "buy" ? "خرید" : "فروش"}
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

              <Panel title="عمق بازار (Order Book)">
                <div className="grid two">
                  <div>
                    <h3 style={{ fontSize: "0.95rem" }}>صف خرید</h3>
                    <table>
                      <thead>
                        <tr>
                          <th>قیمت</th>
                          <th>حجم</th>
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
                    <h3 style={{ fontSize: "0.95rem" }}>صف فروش</h3>
                    <table>
                      <thead>
                        <tr>
                          <th>قیمت</th>
                          <th>حجم</th>
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
                  <span>باز / بالا / پایین</span>
                  <strong>
                    {formatNum(stock.quote.open_price, 0)} / {formatNum(stock.quote.high_price, 0)} /{" "}
                    {formatNum(stock.quote.low_price, 0)}
                  </strong>
                </div>
                <div className="list-row">
                  <span>ارزش معاملات امروز</span>
                  <strong>{formatIrr(stock.quote.value_irr)}</strong>
                </div>
              </Panel>
            </div>

            <Panel title="تاریخچه رشد / نزول روزانه">
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>تاریخ</th>
                      <th>باز</th>
                      <th>بالا</th>
                      <th>پایین</th>
                      <th>پایانی</th>
                      <th>تغییر٪</th>
                      <th>حجم</th>
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
                            {formatNum(d.change_pct ?? 0)}٪
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
                label="مدل‌های Production"
                value={formatNum(maturity?.production_models?.length ?? 0, 0)}
              />
              <Kpi
                label="هدف منافع سالانه"
                value={formatIrr(Number(maturity?.targets?.annual_benefits_irr ?? 200e9))}
              />
              <Kpi
                label="NPV تقریبی"
                value={formatIrr(Number(maturity?.latest_roi?.npv_proxy_irr ?? 0))}
              />
              <Kpi
                label="هدف Payback"
                value={`${formatNum(maturity?.targets?.payback_months ?? 24, 0)} ماه`}
              />
            </div>
            <div className="grid two">
              <Panel title="رجیستری مدل">
                <table>
                  <thead>
                    <tr>
                      <th>دامنه</th>
                      <th>نسخه</th>
                      <th>وضعیت</th>
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
              <Panel title="اقدامات موجودی ۷ روز">
                <table>
                  <thead>
                    <tr>
                      <th>اقدام</th>
                      <th>تعداد</th>
                      <th>صرفه‌جویی</th>
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
