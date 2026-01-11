'use client';

import { useMemo } from 'react';
import type { BatchConvergenceData } from '@/lib/types';

interface BatchConvergenceChartProps {
  data: BatchConvergenceData;
  width?: number;
  height?: number;
  showEntropy?: boolean;
}

export function BatchConvergenceChart({
  data,
  width = 400,
  height = 300,
  showEntropy = false,
}: BatchConvergenceChartProps) {
  const { batch_numbers, batch_keff, entropy, n_inactive, final_keff, final_keff_std } = data;

  const chartData = useMemo(() => {
    return batch_numbers.map((batch, idx) => ({
      batch,
      keff: batch_keff[idx],
      entropy: entropy?.[idx],
      isActive: batch > n_inactive,
    }));
  }, [batch_numbers, batch_keff, entropy, n_inactive]);

  // Calculate chart dimensions and scaling
  const padding = { top: 20, right: 30, bottom: 40, left: 50 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Find min/max for k-effective
  const keffMin = Math.min(...batch_keff) - 0.05;
  const keffMax = Math.max(...batch_keff) + 0.05;
  const keffRange = keffMax - keffMin;

  // Scale functions
  const scaleX = (batch: number) => {
    const maxBatch = Math.max(...batch_numbers);
    return ((batch - 1) / (maxBatch - 1)) * chartWidth;
  };

  const scaleY = (keff: number) => {
    return chartHeight - ((keff - keffMin) / keffRange) * chartHeight;
  };

  // Generate path for batch convergence line
  const pathData = chartData
    .map((d, idx) => {
      const x = scaleX(d.batch);
      const y = scaleY(d.keff);
      return idx === 0 ? `M ${x} ${y}` : `L ${x} ${y}`;
    })
    .join(' ');

  // Final k-effective line (horizontal)
  const finalY = scaleY(final_keff);
  const uncertaintyY = (final_keff_std / keffRange) * chartHeight;

  return (
    <div className="w-full bg-[#14161B] border border-[#1F2937] rounded p-4">
      <div className="mb-3">
        <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">
          Batch Convergence
        </h3>
        {data.note && (
          <p className="text-[10px] text-gray-500 mt-1 italic">{data.note}</p>
        )}
      </div>

      <svg width={width} height={height} className="overflow-visible">
        <defs>
          <linearGradient id="keffGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.05" />
          </linearGradient>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="10"
            refX="9"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 10 3, 0 6" fill="#6b7280" />
          </marker>
        </defs>

        {/* Grid lines */}
        <g transform={`translate(${padding.left}, ${padding.top})`}>
          {/* Horizontal grid lines (k-effective) */}
          {[0, 0.25, 0.5, 0.75, 1.0].map((t) => {
            const keff = keffMin + t * keffRange;
            const y = scaleY(keff);
            return (
              <g key={`grid-h-${t}`}>
                <line
                  x1={0}
                  y1={y}
                  x2={chartWidth}
                  y2={y}
                  stroke="#1F2937"
                  strokeWidth="1"
                  strokeDasharray="2,2"
                />
                <text
                  x={-10}
                  y={y + 4}
                  textAnchor="end"
                  className="text-[9px] fill-gray-600 font-mono"
                >
                  {keff.toFixed(4)}
                </text>
              </g>
            );
          })}

          {/* Vertical grid line at inactive/active boundary */}
          {n_inactive > 0 && (
            <line
              x1={scaleX(n_inactive)}
              y1={0}
              x2={scaleX(n_inactive)}
              y2={chartHeight}
              stroke="#ef4444"
              strokeWidth="1.5"
              strokeDasharray="4,2"
              opacity="0.5"
            />
          )}

          {/* Fill area under curve */}
          <path
            d={`${pathData} L ${chartWidth} ${chartHeight} L 0 ${chartHeight} Z`}
            fill="url(#keffGradient)"
          />

          {/* Batch convergence line */}
          <path
            d={pathData}
            fill="none"
            stroke="#3b82f6"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Final k-effective line with uncertainty band */}
          <line
            x1={0}
            y1={finalY}
            x2={chartWidth}
            y2={finalY}
            stroke="#10b981"
            strokeWidth="2"
            strokeDasharray="4,2"
          />
          <rect
            x={0}
            y={finalY - uncertaintyY}
            width={chartWidth}
            height={uncertaintyY * 2}
            fill="#10b981"
            opacity="0.2"
          />

          {/* Data points */}
          {chartData.map((d, idx) => (
            <circle
              key={idx}
              cx={scaleX(d.batch)}
              cy={scaleY(d.keff)}
              r={d.isActive ? 2.5 : 2}
              fill={d.isActive ? '#3b82f6' : '#6b7280'}
              stroke="#0A0B0D"
              strokeWidth="1"
            />
          ))}

          {/* Labels */}
          <text
            x={chartWidth / 2}
            y={chartHeight + 30}
            textAnchor="middle"
            className="text-[10px] fill-gray-400 font-mono"
          >
            Batch Number
          </text>
          <text
            x={-chartHeight / 2}
            y={-25}
            textAnchor="middle"
            transform="rotate(-90)"
            className="text-[10px] fill-gray-400 font-mono"
          >
            k-effective
          </text>

          {/* Inactive/Active label */}
          {n_inactive > 0 && (
            <>
              <text
                x={scaleX(n_inactive / 2)}
                y={-5}
                textAnchor="middle"
                className="text-[8px] fill-gray-500 font-semibold"
              >
                Inactive
              </text>
              <text
                x={scaleX(n_inactive + (Math.max(...batch_numbers) - n_inactive) / 2)}
                y={-5}
                textAnchor="middle"
                className="text-[8px] fill-blue-400 font-semibold"
              >
                Active
              </text>
            </>
          )}

          {/* Final value label */}
          <text
            x={chartWidth + 5}
            y={finalY + 4}
            className="text-[9px] fill-emerald-400 font-mono font-semibold"
          >
            {final_keff.toFixed(5)} ± {final_keff_std.toFixed(6)}
          </text>
        </g>
      </svg>

      {/* Legend */}
      <div className="mt-3 flex items-center gap-4 text-[10px] text-gray-400">
        <div className="flex items-center gap-2">
          <div className="w-3 h-0.5 bg-blue-500"></div>
          <span>k-effective</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-0.5 bg-emerald-500 border-dashed"></div>
          <span>Final: {final_keff.toFixed(5)}</span>
        </div>
        {n_inactive > 0 && (
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-gray-500"></div>
            <span>Inactive batches</span>
          </div>
        )}
      </div>
    </div>
  );
}

