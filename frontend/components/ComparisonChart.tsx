'use client';

import { useMemo } from 'react';
import type { ComparisonData } from '@/lib/types';

interface ComparisonChartProps {
  data: ComparisonData;
  width?: number;
  height?: number;
}

export function ComparisonChart({
  data,
  width = 500,
  height = 350,
}: ComparisonChartProps) {
  const { num_runs, keff_values, keff_mean, keff_min, keff_max, runs } = data;

  // Calculate chart dimensions and scaling
  const padding = { top: 20, right: 50, bottom: 60, left: 60 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Find min/max for k-effective
  const keffMin = Math.min(keff_min, ...keff_values) - 0.05;
  const keffMax = Math.max(keff_max, ...keff_values) + 0.05;
  const keffRange = keffMax - keffMin;

  // Scale function
  const scaleY = (keff: number) => {
    return chartHeight - ((keff - keffMin) / keffRange) * chartHeight;
  };

  const barWidth = Math.max(20, Math.min(60, chartWidth / num_runs - 10));

  // Criticality zones
  const criticalY = scaleY(1.0);
  const supercriticalY = scaleY(1.01);
  const subcriticalY = scaleY(0.99);

  return (
    <div className="w-full bg-[#14161B] border border-[#1F2937] rounded p-4">
      <div className="mb-3">
        <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">
          Run Comparison ({num_runs} runs)
        </h3>
        <div className="mt-1 text-[10px] text-gray-500">
          Mean: {keff_mean.toFixed(5)} | Range: [{keff_min.toFixed(5)}, {keff_max.toFixed(5)}]
        </div>
      </div>

      <svg width={width} height={height} className="overflow-visible">
        <g transform={`translate(${padding.left}, ${padding.top})`}>
          {/* Criticality zones */}
          <rect
            x={0}
            y={supercriticalY}
            width={chartWidth}
            height={criticalY - supercriticalY}
            fill="#ef4444"
            opacity="0.1"
          />
          <rect
            x={0}
            y={subcriticalY}
            width={chartWidth}
            height={criticalY - subcriticalY}
            fill="#10b981"
            opacity="0.1"
          />
          <rect
            x={0}
            y={0}
            width={chartWidth}
            height={subcriticalY}
            fill="#3b82f6"
            opacity="0.1"
          />

          {/* Criticality lines */}
          <line
            x1={0}
            y1={criticalY}
            x2={chartWidth}
            y2={criticalY}
            stroke="#ef4444"
            strokeWidth="2"
            strokeDasharray="4,2"
            opacity="0.6"
          />
          <line
            x1={0}
            y1={supercriticalY}
            x2={chartWidth}
            y2={supercriticalY}
            stroke="#ef4444"
            strokeWidth="1"
            strokeDasharray="2,2"
            opacity="0.4"
          />
          <line
            x1={0}
            y1={subcriticalY}
            x2={chartWidth}
            y2={subcriticalY}
            stroke="#3b82f6"
            strokeWidth="1"
            strokeDasharray="2,2"
            opacity="0.4"
          />

          {/* Mean line */}
          <line
            x1={0}
            y1={scaleY(keff_mean)}
            x2={chartWidth}
            y2={scaleY(keff_mean)}
            stroke="#fbbf24"
            strokeWidth="2"
            strokeDasharray="4,2"
            opacity="0.7"
          />

          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1.0].map((t) => {
            const keff = keffMin + t * keffRange;
            return (
              <g key={`grid-${t}`}>
                <line
                  x1={0}
                  y1={scaleY(keff)}
                  x2={chartWidth}
                  y2={scaleY(keff)}
                  stroke="#1F2937"
                  strokeWidth="1"
                  strokeDasharray="2,2"
                />
                <text
                  x={-10}
                  y={scaleY(keff) + 4}
                  textAnchor="end"
                  className="text-[9px] fill-gray-600 font-mono"
                >
                  {keff.toFixed(4)}
                </text>
              </g>
            );
          })}

          {/* Bars with error bars */}
          {runs.map((run: any, idx: number) => {
            const x = (idx * chartWidth) / num_runs + (chartWidth / num_runs - barWidth) / 2;
            const y = scaleY(run.keff);
            const errorHeight = ((run.keff_std || 0) / keffRange) * chartHeight;

            // Determine color based on criticality
            const keff = run.keff;
            const color = keff > 1.01 ? '#ef4444' : keff < 0.99 ? '#3b82f6' : '#10b981';

            const barHeight = chartHeight - y;

            return (
              <g key={idx}>
                {/* Bar */}
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={barHeight}
                  fill={color}
                  opacity="0.7"
                  stroke="#0A0B0D"
                  strokeWidth="1"
                />
                {/* Error bar */}
                {errorHeight > 0 && (
                  <>
                    <line
                      x1={x + barWidth / 2}
                      y1={y - errorHeight}
                      x2={x + barWidth / 2}
                      y2={y + errorHeight}
                      stroke={color}
                      strokeWidth="2"
                      opacity="0.9"
                    />
                    <line
                      x1={x + barWidth / 2 - 4}
                      y1={y - errorHeight}
                      x2={x + barWidth / 2 + 4}
                      y2={y - errorHeight}
                      stroke={color}
                      strokeWidth="2"
                      opacity="0.9"
                    />
                    <line
                      x1={x + barWidth / 2 - 4}
                      y1={y + errorHeight}
                      x2={x + barWidth / 2 + 4}
                      y2={y + errorHeight}
                      stroke={color}
                      strokeWidth="2"
                      opacity="0.9"
                    />
                  </>
                )}
                {/* Value label */}
                <text
                  x={x + barWidth / 2}
                  y={y - 8}
                  textAnchor="middle"
                  className="text-[9px] fill-gray-300 font-mono font-semibold"
                >
                  {run.keff.toFixed(4)}
                </text>
                {/* Run ID label */}
                <text
                  x={x + barWidth / 2}
                  y={chartHeight + 20}
                  textAnchor="middle"
                  className="text-[8px] fill-gray-500 font-mono"
                  transform={`rotate(-45 ${x + barWidth / 2} ${chartHeight + 20})`}
                >
                  {run.run_id?.substring(0, 8) || `Run ${idx + 1}`}
                </text>
              </g>
            );
          })}

          {/* Labels */}
          <text
            x={-chartHeight / 2}
            y={-35}
            textAnchor="middle"
            transform="rotate(-90)"
            className="text-[10px] fill-gray-400 font-mono"
          >
            k-effective
          </text>

          {/* Mean label */}
          <text
            x={chartWidth + 5}
            y={scaleY(keff_mean) + 4}
            className="text-[9px] fill-amber-400 font-mono font-semibold"
          >
            Mean: {keff_mean.toFixed(5)}
          </text>
        </g>
      </svg>

      {/* Legend */}
      <div className="mt-4 flex items-center gap-4 text-[10px] text-gray-400 flex-wrap">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-red-500 opacity-70"></div>
          <span>Supercritical</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-500 opacity-70"></div>
          <span>Critical</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-blue-500 opacity-70"></div>
          <span>Subcritical</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 bg-amber-400 border-dashed"></div>
          <span>Mean</span>
        </div>
      </div>
    </div>
  );
}

