import type { ExportForecastRow } from "./data/export_markets";

type Props = {
  rows: ExportForecastRow[];
  height?: number;
};

export function ExportForecastChart({ rows, height = 200 }: Props) {
  if (!rows.length) {
    return <div className="empty">داده‌ای برای پیش‌بینی نیست.</div>;
  }

  const w = 720;
  const h = height;
  const pad = { top: 16, right: 12, bottom: 28, left: 52 };
  const vals = rows.map((r) => r.forecast_tonnage_kg / 1000);
  const baselines = rows.map((r) => r.baseline_tonnage_kg / 1000);
  const min = Math.min(...baselines, ...vals) * 0.92;
  const max = Math.max(...vals) * 1.05;
  const span = Math.max(max - min, 1);

  const toXY = (arr: number[]) =>
    arr.map((v, i) => {
      const x = pad.left + (i / Math.max(arr.length - 1, 1)) * (w - pad.left - pad.right);
      const y = pad.top + (1 - (v - min) / span) * (h - pad.top - pad.bottom);
      return { x, y, v };
    });

  const forecastPts = toXY(vals);
  const basePts = toXY(baselines);
  const line = (pts: Array<{ x: number; y: number }>) =>
    pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
  const area =
    `${line(forecastPts)} L${forecastPts[forecastPts.length - 1].x},${h - pad.bottom} L${forecastPts[0].x},${h - pad.bottom} Z`;

  return (
    <div className="stock-chart">
      <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label="نمودار پیش‌بینی صادرات">
        <defs>
          <linearGradient id="exportFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0f766e" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#0f766e" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {[min, min + span / 2, max].map((v) => {
          const y = pad.top + (1 - (v - min) / span) * (h - pad.top - pad.bottom);
          return (
            <g key={v}>
              <line x1={pad.left} x2={w - pad.right} y1={y} y2={y} stroke="rgba(20,18,16,0.08)" />
              <text x={pad.left - 8} y={y + 4} textAnchor="end" className="chart-label">
                {Math.round(v).toLocaleString("fa-IR")}
              </text>
            </g>
          );
        })}
        <path d={area} fill="url(#exportFill)" />
        <path d={line(basePts)} fill="none" stroke="#a8a29e" strokeWidth="1.8" strokeDasharray="5 4" />
        <path d={line(forecastPts)} fill="none" stroke="#0f766e" strokeWidth="2.6" strokeLinejoin="round" />
        {forecastPts.map((p, i) => (
          <g key={rows[i].month}>
            <circle cx={p.x} cy={p.y} r="3.5" fill="#0f766e" />
            <text x={p.x} y={h - 8} textAnchor="middle" className="chart-label">
              {rows[i].month.slice(5)}
            </text>
          </g>
        ))}
      </svg>
      <div className="chart-legend">
        خط ممتد: پیش‌بینی کل (تن) · خط‌چین: پایه بازارهای بالفعل · محور: تن در ماه
      </div>
    </div>
  );
}
