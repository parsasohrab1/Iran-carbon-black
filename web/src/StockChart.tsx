import type { StockDaily, StockTick } from "./data/stock";

type Props = {
  points: Array<StockTick | StockDaily>;
  mode?: "intraday" | "daily";
  height?: number;
  up?: boolean;
};

function valueOf(p: StockTick | StockDaily, mode: "intraday" | "daily"): number {
  if (mode === "daily") return Number((p as StockDaily).close);
  return Number((p as StockTick).price);
}

function labelOf(p: StockTick | StockDaily, mode: "intraday" | "daily"): string {
  if (mode === "daily") return String((p as StockDaily).date).slice(5);
  const t = String((p as StockTick).time);
  try {
    return new Date(t).toLocaleTimeString("fa-IR", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return t.slice(11, 16);
  }
}

export function StockChart({ points, mode = "intraday", height = 220, up = true }: Props) {
  if (!points.length) {
    return <div className="empty">داده‌ای برای نمودار نیست.</div>;
  }

  const w = 720;
  const h = height;
  const pad = { top: 16, right: 12, bottom: 28, left: 48 };
  const vals = points.map((p) => valueOf(p, mode));
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const span = Math.max(max - min, 1);

  const coords = points.map((p, i) => {
    const x = pad.left + (i / Math.max(points.length - 1, 1)) * (w - pad.left - pad.right);
    const y = pad.top + (1 - (valueOf(p, mode) - min) / span) * (h - pad.top - pad.bottom);
    return { x, y, label: labelOf(p, mode), value: valueOf(p, mode) };
  });

  const line = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x},${c.y}`).join(" ");
  const area =
    `${line} L${coords[coords.length - 1].x},${h - pad.bottom} L${coords[0].x},${h - pad.bottom} Z`;

  const stroke = up ? "#047857" : "#b91c1c";
  const fill = up ? "rgba(4, 120, 87, 0.18)" : "rgba(185, 28, 28, 0.16)";
  const yTicks = [min, min + span / 2, max];

  return (
    <div className="stock-chart">
      <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label="نمودار قیمت سهام شکربن">
        <defs>
          <linearGradient id="stockFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={stroke} stopOpacity="0.35" />
            <stop offset="100%" stopColor={stroke} stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {yTicks.map((v) => {
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
        <path d={area} fill="url(#stockFill)" />
        <path d={line} fill="none" stroke={stroke} strokeWidth="2.5" strokeLinejoin="round" />
        {coords.filter((_, i) => i % Math.ceil(coords.length / 6) === 0 || i === coords.length - 1).map((c) => (
          <g key={`${c.x}-${c.label}`}>
            <circle cx={c.x} cy={c.y} r="3.2" fill={stroke} />
            <text x={c.x} y={h - 8} textAnchor="middle" className="chart-label">
              {c.label}
            </text>
          </g>
        ))}
        <circle
          cx={coords[coords.length - 1].x}
          cy={coords[coords.length - 1].y}
          r="5"
          fill={stroke}
          className="pulse-dot"
        />
      </svg>
      <div className="chart-legend" style={{ color: stroke }}>
        آخرین: {Math.round(coords[coords.length - 1].value).toLocaleString("fa-IR")} ریال
      </div>
    </div>
  );
}
