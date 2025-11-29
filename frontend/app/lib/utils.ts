const numberFormatter = new Intl.NumberFormat("en-US");
const compactFormatter = new Intl.NumberFormat("en-US", { notation: "compact" });

export function formatNumber(value: number): string {
    return numberFormatter.format(value);
}

export function formatCompactNumber(value: number): string {
    return compactFormatter.format(value);
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