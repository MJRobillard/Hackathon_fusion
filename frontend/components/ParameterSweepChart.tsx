'use client';

import { useMemo } from 'react';
import type { ParameterSweepData } from '@/lib/types';

interface ParameterSweepChartProps {
  data: ParameterSweepData;
  width?: number;
  height?: number;
}

export function ParameterSweepChart({
  data,
  width = 500,
  height = 350,
}: ParameterSweepChartProps) {
  const { parameter_name, parameter_values, keff_values, keff_stds, trend_line } = data;

  // Calculate chart dimensions and scaling
  const padding = { top: 20, right: 50, bottom: 50, left: 60 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Find min/max for both axes
  const paramMin = Math.min(...parameter_values);
  const paramMax = Math.max(...parameter_values);
  const paramRange = paramMax - paramMin || 1; // Avoid division by zero

  const keffMin = Math.min(...keff_values) - Math.max(...keff_stds) - 0.02;
  const keffMax = Math.max(...keff_values) + Math.max(...keff_stds) + 0.02;
  const keffRange = keffMax - keffMin;

  // Scale functions
  const scaleX = (param: number) => {
    return ((param - paramMin) / paramRange) * chartWidth;
  };

  const scaleY = (keff: number) => {
    return chartHeight - ((keff - keffMin) / keffRange) * chartHeight;
  };

  // Format parameter name for display
  const paramLabel = parameter_name
    .replace(/_/g, ' ')
    .replace(/pct/g, '%')
    .replace(/\b\w/g, (l) => l.toUpperCase());

  // Criticality zones
  const criticalY = scaleY(1.0);

  return (
    <div className="w-full bg-[#14161B] border border-[#1F2937] rounded p-4">
      <div className="mb-3">
        <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">
          Parameter Sweep: {paramLabel}
        </h3>
        {trend_line && (
          <p className="text-[10px] text-gray-500 mt-1">
            Slope: {trend_line.slope.toFixed(6)} Δk/Δ{paramLabel.split(' ')[0].toLowerCase()}
            {trend_line.slope > 0 ? ' (positive)' : trend_line.slope < 0 ? ' (negative)' : ' (neutral)'}
          </p>
        )}
      </div>

      <svg width={width} height={height} className="overflow-visible">
        <defs>
          <linearGradient id="sweepGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.05" />
          </linearGradient>
        </defs>

        <g transform={`translate(${padding.left}, ${padding.top})`}>
          {/* Criticality line (k=1.0) */}
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
          <text
            x={chartWidth + 5}
            y={criticalY + 4}
            className="text-[9px] fill-red-400 font-mono font-semibold"
          >
            k=1.0 (Critical)
          </text>

          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1.0].map((t) => {
            const param = paramMin + t * paramRange;
            const keff = keffMin + t * keffRange;
            return (
              <g key={`grid-${t}`}>
                {/* Vertical grid */}
                <line
                  x1={scaleX(param)}
                  y1={0}
                  x2={scaleX(param)}
                  y2={chartHeight}
                  stroke="#1F2937"
                  strokeWidth="1"
                  strokeDasharray="2,2"
                />
                {/* Horizontal grid */}
                <line
                  x1={0}
                  y1={scaleY(keff)}
                  x2={chartWidth}
                  y2={scaleY(keff)}
                  stroke="#1F2937"
                  strokeWidth="1"
                  strokeDasharray="2,2"
                />
              </g>
            );
          })}

          {/* Trend line */}
          {trend_line && trend_line.values.length > 0 && (
            <path
              d={parameter_values
                .map((param, idx) => {
                  const x = scaleX(param);
                  const y = scaleY(trend_line.values[idx]);
                  return idx === 0 ? `M ${x} ${y}` : `L ${x} ${y}`;
                })
                .join(' ')}
              fill="none"
              stroke="#10b981"
              strokeWidth="2"
              strokeDasharray="4,2"
              opacity="0.7"
            />
          )}

          {/* Error bars and data points */}
          {parameter_values.map((param, idx) => {
            const x = scaleX(param);
            const y = scaleY(keff_values[idx]);
            const errorHeight = (keff_stds[idx] / keffRange) * chartHeight;

            // Determine color based on criticality
            const keff = keff_values[idx];
            const color = keff > 1.01 ? '#ef4444' : keff < 0.99 ? '#3b82f6' : '#10b981';

            return (
              <g key={idx}>
                {/* Error bar */}
                <line
                  x1={x}
                  y1={y - errorHeight}
                  x2={x}
                  y2={y + errorHeight}
                  stroke={color}
                  strokeWidth="1.5"
                  opacity="0.6"
                />
                {/* Error bar caps */}
                <line
                  x1={x - 4}
                  y1={y - errorHeight}
                  x2={x + 4}
                  y2={y - errorHeight}
                  stroke={color}
                  strokeWidth="1.5"
                  opacity="0.6"
                />
                <line
                  x1={x - 4}
                  y1={y + errorHeight}
                  x2={x + 4}
                  y2={y + errorHeight}
                  stroke={color}
                  strokeWidth="1.5"
                  opacity="0.6"
                />
                {/* Data point */}
                <circle
                  cx={x}
                  cy={y}
                  r="4"
                  fill={color}
                  stroke="#0A0B0D"
                  strokeWidth="1.5"
                />
              </g>
            );
          })}

          {/* Labels */}
          <text
            x={chartWidth / 2}
            y={chartHeight + 35}
            textAnchor="middle"
            className="text-[10px] fill-gray-400 font-mono"
          >
            {paramLabel}
          </text>
          <text
            x={-chartHeight / 2}
            y={-35}
            textAnchor="middle"
            transform="rotate(-90)"
            className="text-[10px] fill-gray-400 font-mono"
          >
            k-effective
          </text>

          {/* Parameter value labels */}
          {parameter_values.map((param, idx) => {
            if (idx % Math.ceil(parameter_values.length / 5) === 0 || idx === parameter_values.length - 1) {
              return (
                <text
                  key={idx}
                  x={scaleX(param)}
                  y={chartHeight + 20}
                  textAnchor="middle"
                  className="text-[9px] fill-gray-500 font-mono"
                >
                  {typeof param === 'number' ? param.toFixed(1) : param}
                </text>
              );
            }
            return null;
          })}

          {/* k-effective value labels */}
          {[0, 0.25, 0.5, 0.75, 1.0].map((t) => {
            const keff = keffMin + t * keffRange;
            return (
              <text
                key={`keff-label-${t}`}
                x={-10}
                y={scaleY(keff) + 4}
                textAnchor="end"
                className="text-[9px] fill-gray-600 font-mono"
              >
                {keff.toFixed(4)}
              </text>
            );
          })}
        </g>
      </svg>

      {/* Legend */}
      <div className="mt-3 flex items-center gap-4 text-[10px] text-gray-400 flex-wrap">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500"></div>
          <span>Supercritical (k &gt; 1.01)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500"></div>
          <span>Critical (0.99 &lt; k &lt; 1.01)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-blue-500"></div>
          <span>Subcritical (k &lt; 0.99)</span>
        </div>
        {trend_line && (
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-emerald-500 border-dashed"></div>
            <span>Trend line</span>
          </div>
        )}
      </div>
    </div>
  );
}

