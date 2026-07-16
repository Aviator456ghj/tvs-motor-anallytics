"use client";

import { useMemo, useState } from "react";

export interface TrendPoint {
  date: string;
  value: number;
}

const WIDTH = 640;
const HEIGHT = 200;
const PAD_TOP = 16;
const PAD_BOTTOM = 28;
const PAD_X = 8;

function formatShortDate(iso: string) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function TrendChart({
  data,
  valueFormatter = (v: number) => v.toLocaleString(),
  emptyLabel = "No data yet for this period.",
}: {
  data: TrendPoint[];
  valueFormatter?: (v: number) => string;
  emptyLabel?: string;
}) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const { points, maxVal, gridLines, areaPath, linePath } = useMemo(() => {
    const maxVal = Math.max(1, ...data.map((d) => d.value));
    const innerW = WIDTH - PAD_X * 2;
    const innerH = HEIGHT - PAD_TOP - PAD_BOTTOM;
    const step = data.length > 1 ? innerW / (data.length - 1) : 0;

    const points = data.map((d, i) => ({
      x: PAD_X + i * step,
      y: PAD_TOP + innerH - (d.value / maxVal) * innerH,
      ...d,
    }));

    const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
    const areaPath =
      points.length > 0
        ? `${linePath} L ${points[points.length - 1].x.toFixed(1)} ${PAD_TOP + innerH} L ${points[0].x.toFixed(1)} ${PAD_TOP + innerH} Z`
        : "";

    const gridLines = [0, 0.5, 1].map((frac) => PAD_TOP + innerH * (1 - frac));

    return { points, maxVal, gridLines, areaPath, linePath };
  }, [data]);

  if (data.length === 0 || data.every((d) => d.value === 0)) {
    return <div className="flex h-[200px] items-center justify-center text-sm text-slate-400">{emptyLabel}</div>;
  }

  const active = hoverIdx !== null ? points[hoverIdx] : points[points.length - 1];

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full"
        role="img"
        aria-label="Trend over time"
        onMouseLeave={() => setHoverIdx(null)}
        onMouseMove={(e) => {
          const svg = e.currentTarget;
          const rect = svg.getBoundingClientRect();
          const xRatio = (e.clientX - rect.left) / rect.width;
          const idx = Math.round(xRatio * (points.length - 1));
          setHoverIdx(Math.max(0, Math.min(points.length - 1, idx)));
        }}
      >
        <defs>
          <linearGradient id="trend-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#1c6fef" stopOpacity="0.16" />
            <stop offset="100%" stopColor="#1c6fef" stopOpacity="0" />
          </linearGradient>
        </defs>

        {gridLines.map((y, i) => (
          <line key={i} x1={PAD_X} x2={WIDTH - PAD_X} y1={y} y2={y} stroke="#eef2f7" strokeWidth={1} />
        ))}

        <path d={areaPath} fill="url(#trend-fill)" />
        <path d={linePath} fill="none" stroke="#1c6fef" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />

        {points.length > 0 && (
          <circle cx={points[points.length - 1].x} cy={points[points.length - 1].y} r={4} fill="#1c6fef" stroke="white" strokeWidth={1.5} />
        )}

        {hoverIdx !== null && (
          <>
            <line x1={points[hoverIdx].x} x2={points[hoverIdx].x} y1={PAD_TOP} y2={HEIGHT - PAD_BOTTOM} stroke="#cbd5e1" strokeWidth={1} strokeDasharray="3,3" />
            <circle cx={points[hoverIdx].x} cy={points[hoverIdx].y} r={4} fill="#1c6fef" stroke="white" strokeWidth={1.5} />
          </>
        )}

        <text x={PAD_X} y={HEIGHT - 8} fontSize={10} fill="#94a3b8">
          {formatShortDate(data[0].date)}
        </text>
        <text x={WIDTH - PAD_X} y={HEIGHT - 8} fontSize={10} fill="#94a3b8" textAnchor="end">
          {formatShortDate(data[data.length - 1].date)}
        </text>
      </svg>

      {active && (
        <div className="pointer-events-none absolute right-2 top-0 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs shadow-sm">
          <div className="font-medium text-slate-800">{formatShortDate(active.date)}</div>
          <div className="font-variant-numeric-tabular text-slate-500">{valueFormatter(active.value)}</div>
        </div>
      )}
    </div>
  );
}
