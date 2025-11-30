/**
 * Cấu hình ngưỡng giao thông cho từng tuyến đường
 *
 * - v: Ngưỡng vận tốc trung bình (km/h) - Lớn hơn hoặc bằng v thì nhanh chóng, ngược lại là chậm
 * - c1: Ngưỡng số lượng phương tiện thấp - Lớn hơn c1 là đông đúc
 * - c2: Ngưỡng số lượng phương tiện cao - Lớn hơn c2 là tắc nghẽn
 *
 * Quy tắc phân loại:
 * - Tắc nghẽn: Tổng số phương tiện > c2
 * - Đông đúc: Tổng số phương tiện > c1 và <= c2
 * - Thông thoáng: Tổng số phương tiện <= c1
 */

export interface RoadThreshold {
  v: number; // Ngưỡng vận tốc trung bình
  c1: number; // Ngưỡng đông đúc
  c2: number; // Ngưỡng tắc nghẽn
}

export const TRAFFIC_THRESHOLDS: Record<string, RoadThreshold> = {
  "Đường Láng": {
    v: 6,
    c1: 17,
    c2: 26,
  },
  "Ngã Tư Sở": {
    v: 17,
    c1: 45,
    c2: 57,
  },
  "Nguyễn Trãi": {
    v: 30,
    c1: 25,
    c2: 35,
  },
  "Văn Quán": {
    v: 10,
    c1: 10,
    c2: 17,
  },
  "Văn Phú": {
    v: 13,
    c1: 18,
    c2: 26,
  },
};

/**
 * Ngưỡng mặc định cho các tuyến đường chưa được cấu hình
 */
export const DEFAULT_THRESHOLD: RoadThreshold = {
  v: 15,
  c1: 15,
  c2: 25,
};

/**
 * Lấy ngưỡng cho một tuyến đường cụ thể
 * @param roadName - Tên tuyến đường
 * @returns Ngưỡng cho tuyến đường hoặc ngưỡng mặc định
 */
export const getThresholdForRoad = (roadName: string): RoadThreshold => {
  return TRAFFIC_THRESHOLDS[roadName] || DEFAULT_THRESHOLD;
};
