// Utility functions for formatting data

import { CRITICALITY_STATUS } from './constants';

export function formatKeff(keff: number, keff_std?: number): string {
  if (keff_std) {
    return `${keff.toFixed(5)} ± ${keff_std.toFixed(6)}`;
  }
  return keff.toFixed(5);
}

export function getCriticalityStatus(keff: number) {
  if (keff < CRITICALITY_STATUS.subcritical.threshold) {
    return CRITICALITY_STATUS.subcritical;
  }
  if (keff <= CRITICALITY_STATUS.critical.threshold) {
    return CRITICALITY_STATUS.critical;
  }
  return CRITICALITY_STATUS.supercritical;
}

export function formatTimeAgo(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', { 
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function truncateQuery(query: string, maxLength: number = 50): string {
  if (query.length <= maxLength) return query;
  return query.substring(0, maxLength) + '...';
}

export function formatNumber(num: number, decimals: number = 0): string {
  return num.toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

