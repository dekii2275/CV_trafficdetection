const numberFormatter = new Intl.NumberFormat("en-US");
const compactFormatter = new Intl.NumberFormat("en-US", { notation: "compact" });

export function formatNumber(num: number): string {
  return new Intl.NumberFormat('vi-VN').format(num);
}

export function formatCompactNumber(num: number): string {
  return new Intl.NumberFormat('vi-VN', { 
    notation: "compact", 
    compactDisplay: "short" 
  }).format(num);
}

export function formatRatePerMinute(value: number): string {
    return `${value}/min`;
}

export function calculatePercentage(part: number, total: number): number {
    if (total === 0) {
        return 0;
    }
    return Math.round((part / total) * 100);
}