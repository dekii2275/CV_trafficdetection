export type VehicleType = "car" | "truck" | "bike" | "bus";

export interface VehicleStats {
    timestamp: number;
    total: number;
    ratePerMinute: number;
    breakdown: Record<VehicleType, number>;
}

export interface ChartPoint {
    label: string;
    value: number;
}

export interface CameraSummary {
    camera: string;
    vehicles: number;
    dominantType: VehicleType;
}
