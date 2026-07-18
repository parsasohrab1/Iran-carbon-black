import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { apiGet, apiPost, formatIrr, formatNum } from "./api";
import { buildLocalCatalog, type CatalogResponse, type ProductGrade } from "./data/grades";

type TabId = "overview" | "products" | "energy" | "quality" | "demand" | "commercial" | "maturity";

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
  { id: "energy", label: "انرژی و نگهداری" },
  { id: "quality", label: "کیفیت" },
  { id: "demand", label: "تقاضا و تولید" },
  { id: "commercial", label: "فروش و مالی" },
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

export default function App() {
  const [tab, setTab] = useState<TabId>("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [finance, setFinance] = useState<FinanceDash | null>(null);
  const [ops, setOps] = useState<OpsStatus | null>(null);
  const [maturity, setMaturity] = useState<MaturityDash | null>(null);
  const [energyAlerts, setEnergyAlerts] = useState<Array<Record<string, unknown>>>([]);
  const [equipment, setEquipment] = useState<Array<Record<string, unknown>>>([]);
  const [anomalyEvents, setAnomalyEvents] = useState<Array<Record<string, unknown>>>([]);
  const [plans, setPlans] = useState<Array<Record<string, unknown>>>([]);
  const [portfolio, setPortfolio] = useState<{ high_margin_focus?: Array<Record<string, unknown>> } | null>(
    null,
  );
  const [inventoryActions, setInventoryActions] = useState<Array<Record<string, unknown>>>([]);
  const [customersAtRisk, setCustomersAtRisk] = useState<Array<Record<string, unknown>>>([]);
  const [catalog, setCatalog] = useState<CatalogResponse>(() => buildLocalCatalog());
  const [selectedGrade, setSelectedGrade] = useState<string>("N-220");
  const [updatedAt, setUpdatedAt] = useState<string>("");

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
        anomalies,
        prodPlans,
        port,
        invOpt,
        crm,
        products,
      ] = await Promise.all([
        apiGet<FinanceDash>("/api/v1/finance/dashboard").catch(() => null),
        apiGet<OpsStatus>("/api/v1/ops/status").catch(() => null),
        apiGet<MaturityDash>("/api/v1/maturity/dashboard").catch(() => null),
        apiGet<Array<Record<string, unknown>>>("/api/v1/energy/alerts?open_only=true").catch(() => []),
        apiGet<Array<Record<string, unknown>>>("/api/v1/energy/equipment").catch(() => []),
        apiGet<Array<Record<string, unknown>>>("/api/v1/quality/anomaly/events?limit=12").catch(() => []),
        apiGet<Array<Record<string, unknown>>>("/api/v1/demand/production/plans?limit=12").catch(() => []),
        apiGet<{ high_margin_focus?: Array<Record<string, unknown>> }>("/api/v1/maturity/portfolio").catch(
          () => null,
        ),
        apiPost<{ actions?: Array<Record<string, unknown>> }>("/api/v1/maturity/inventory/optimize").catch(
          () => ({ actions: [] }),
        ),
        apiGet<Array<Record<string, unknown>>>("/api/v1/sales/crm/at-risk").catch(() => []),
        apiGet<CatalogResponse>("/api/v1/quality/products").catch(() => buildLocalCatalog()),
      ]);

      setFinance(financeDash);
      setOps(opsStatus);
      setMaturity(maturityDash);
      setEnergyAlerts(alerts);
      setEquipment(equip);
      setAnomalyEvents(anomalies);
      setPlans(prodPlans);
      setPortfolio(port);
      setInventoryActions(invOpt.actions ?? []);
      setCustomersAtRisk(crm);
      setCatalog(products);
      setUpdatedAt(new Date().toLocaleString("fa-IR"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "خطا در بارگذاری داشبورد");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const id = window.setInterval(() => void load(), 60000);
    return () => window.clearInterval(id);
  }, [load]);

  const serviceRows = useMemo(() => {
    if (!ops?.services) return [];
    return Object.entries(ops.services).map(([name, meta]) => ({ name, ...meta }));
  }, [ops]);

  const selectedProduct: ProductGrade | undefined = useMemo(
    () => catalog.products.find((p) => p.code === selectedGrade) ?? catalog.products[0],
    [catalog, selectedGrade],
  );

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

        {!error && tab === "energy" ? (
          <div className="stack">
            <div className="grid kpi">
              <Kpi label="تجهیزات پایلوت" value={formatNum(equipment.length, 0)} hint="ثبت‌شده در سیستم" />
              <Kpi
                label="هشدار باز"
                value={formatNum(energyAlerts.length, 0)}
                tone={energyAlerts.length ? "warn" : "ok"}
                hint="نگهداری پیش‌بینی‌کننده"
              />
            </div>
            <div className="grid two">
              <Panel title="تجهیزات">
                <table>
                  <thead>
                    <tr>
                      <th>شناسه</th>
                      <th>نام</th>
                      <th>نوع</th>
                      <th>وضعیت</th>
                    </tr>
                  </thead>
                  <tbody>
                    {equipment.map((eq) => (
                      <tr key={String(eq.id)}>
                        <td>{String(eq.id)}</td>
                        <td>{String(eq.name)}</td>
                        <td>{String(eq.equipment_type)}</td>
                        <td>{String(eq.status)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Panel>
              <Panel title="هشدارهای نگهداری">
                {energyAlerts.length === 0 ? (
                  <div className="empty">هشدار بازی وجود ندارد.</div>
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
            <div className="grid two">
              <Panel title="برنامه تولید">
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
                {plans.length === 0 ? <div className="empty">برنامه‌ای موجود نیست.</div> : null}
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
              </Panel>
            </div>
            <Panel title="گریدهای پرمارژین پیشنهادی">
              <div className="grid three">
                {(portfolio?.high_margin_focus ?? []).map((g) => (
                  <div className="panel" key={String(g.product_grade)} style={{ boxShadow: "none" }}>
                    <div className="kpi-value">{String(g.product_grade)}</div>
                    <div className="kpi-label">مارژین {formatNum(Number(g.margin_score) * 100)}٪</div>
                    <div className="kpi-hint">{String(g.specialty_tag ?? "")}</div>
                  </div>
                ))}
              </div>
            </Panel>
          </div>
        ) : null}

        {!error && tab === "commercial" ? (
          <div className="stack">
            <div className="grid kpi">
              <Kpi label="فروش ماهانه (kg)" value={formatNum(Number(finance?.sales_mtd?.month_qty ?? 0), 0)} />
              <Kpi label="درآمد ماهانه" value={formatIrr(Number(finance?.sales_mtd?.month_revenue ?? 0))} />
              <Kpi
                label="مشتریان در ریسک"
                value={formatNum(customersAtRisk.length, 0)}
                tone={customersAtRisk.length ? "warn" : "ok"}
              />
              <Kpi
                label="حاشیه سود"
                value={`${formatNum(Number(finance?.finance?.profit_margin ?? 0) * 100)}٪`}
              />
            </div>
            <div className="grid two">
              <Panel title="پیش‌بینی فروش اخیر">
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
            <Panel title="سیگنال‌های تامین">
              <table>
                <thead>
                  <tr>
                    <th>ماده</th>
                    <th>روند</th>
                    <th>پیشنهاد</th>
                    <th>قیمت پیش‌بینی</th>
                  </tr>
                </thead>
                <tbody>
                  {(finance?.supply_signals ?? []).map((s, idx) => (
                    <tr key={`${s.material}-${idx}`}>
                      <td>{String(s.material)}</td>
                      <td>{String(s.trend)}</td>
                      <td>{String(s.recommendation)}</td>
                      <td>{formatIrr(Number(s.predicted_price_irr))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
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
