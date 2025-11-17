"""
visualize.py: Tạo 9 biểu đồ trực quan để phân tích lưu lượng giao thông
- Line chart: Xu hướng lượng xe theo thời gian
- Bar chart: So sánh từng loại xe theo khoảng thời gian
- Area chart: Phân bố tích lũy các loại xe
- Pie chart: Tỷ lệ % mỗi loại xe (% lớn trên pie, tất cả % trong chú giải)
- Histogram: Phân phối tần số lượng xe tổng
- Boxplot: Biến động mỗi loại xe
- Rolling average: Xu hướng mượt (trung bình động)
- Peak detection: Phát hiện đỉnh lưu lượng
- Stacked bar: Tỷ lệ % mỗi loại theo thời gian
"""
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from pathlib import Path

sns.set(style="darkgrid", rc={"figure.figsize": (12, 5)})

def prepare_time_index(df: pd.DataFrame) -> pd.DataFrame:
    """Chuyển cột timestamp/time thành index dạng datetime để slicing dễ dàng."""
    d = df.copy()
    if "timestamp" in d.columns:
        d["timestamp"] = pd.to_datetime(d["timestamp"])
        d = d.set_index("timestamp")
    elif "time" in d.columns:
        d["time"] = pd.to_datetime(d["time"])
        d = d.set_index("time")
    return d

def ensure_dir(out_path: str):
    """Tạo thư mục nếu không tồn tại, trả về Path object."""
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

# 1. Biểu đồ đường - xu hướng lượng xe theo thời gian
def plot_line_chart(df, classes, out_path="data/figures/line_chart.png"):
    """Vẽ line chart theo từng loại xe, giúp thấy xu hướng theo thời gian."""
    d = prepare_time_index(df)
    p = ensure_dir(out_path)
    d[classes].plot()
    plt.title("Line Chart - Vehicle counts over time")
    plt.xlabel("Time")
    plt.ylabel("Count")
    plt.legend()
    plt.tight_layout()
    plt.savefig(p, dpi=150)
    plt.close()
    return str(p)


# 2. Biểu đồ cột nhóm - so sánh từng loại xe theo khoảng thời gian
def plot_grouped_bar_minute(df, classes, out_path="data/figures/grouped_bar_minute.png"):
    """Vẽ grouped bar chart, mỗi cột là một khoảng thời gian (phút)."""
    d = prepare_time_index(df)
    p = ensure_dir(out_path)
    d[classes].plot(kind="bar", figsize=(14,5))
    plt.title("Grouped Bar - Per minute")
    plt.xlabel("Time")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(p, dpi=150)
    plt.close()
    return str(p)


# 3. Area chart - phân bố tích lũy các loại xe
def plot_area_chart(df, classes, out_path="data/figures/area_chart.png"):
    """Vẽ area chart stacked để thấy tổng và thành phần từng loại."""
    d = prepare_time_index(df)
    p = ensure_dir(out_path)
    d[classes].plot(kind="area", stacked=True, alpha=0.7)
    plt.title("Area Chart - Vehicle counts")
    plt.tight_layout()
    plt.savefig(p, dpi=150)
    plt.close()
    return str(p)


# 4. Pie chart - tỷ lệ phần trăm loại xe
def plot_pie_chart(df, classes, out_path="data/figures/pie_chart.png", **kwargs):
    """
    Vẽ pie chart với các loại xe.
    - % >= 3%: hiển thị trên pie
    - % < 3%: ẩn trên pie (để tránh lộn xộn)
    - Tất cả % (kể cả nhỏ) hiển thị trong chú giải (legend)
    """
    
    def autopct_format(value):
        # Ẩn % nhỏ trên pie để tránh chồng chéo
        if value < 3.0:
            return '' 
        return f'{value:.1f}%'
            
    d = prepare_time_index(df)
    p = ensure_dir(out_path)
    
    # Tính tổng cho từng loại (bỏ các cột có tổng 0)
    sums = {c: int(d[c].sum()) for c in classes if c in d.columns and d[c].sum() > 0}
    sorted_sums = dict(sorted(sums.items(), key=lambda item: item[1], reverse=True))

    values = list(sorted_sums.values())
    total_sum = sum(values)
    
    # Tạo nhãn chú giải kèm % cho tất cả loại (kể cả nhỏ)
    legend_labels = []
    for cls, val in sorted_sums.items():
        percent = (val / total_sum) * 100
        legend_labels.append(f"{cls}: {percent:.1f}%")

    fig, ax = plt.subplots(figsize=(10, 8)) 
    
    # Vẽ pie với autopct_format ẩn % nhỏ
    wedges, texts, autotexts = ax.pie(values, 
                                      autopct=autopct_format, 
                                      startangle=90,
                                      pctdistance=0.6)

    # % hiển thị trên pie dùng màu trắng
    for text in autotexts:
        text.set_color("white") 
        
    # Legend bên ngoài kèm % đầy đủ
    ax.legend(wedges,  
              legend_labels,
              title="Loại xe",
              loc="center left", 
              bbox_to_anchor=(1, 0, 0.5, 1))
        
    ax.set_title("Vehicle Type Distribution")
    plt.tight_layout()
    plt.savefig(p, dpi=150)
    plt.close() 
    return str(p)


# 5. Histogram - phân phối tần số lượng xe tổng
def plot_hist_total(df, out_path="data/figures/hist_total.png"):
    """Vẽ histogram để thấy phân phối tần số lượng xe tổng cộng."""
    d = prepare_time_index(df)
    p = ensure_dir(out_path)
    d["total"].plot(kind="hist", bins=20)
    plt.title("Histogram - Total vehicle counts")
    plt.xlabel("Total")
    plt.tight_layout()
    plt.savefig(p, dpi=150)
    plt.close()
    return str(p)

# 6. Boxplot - biến động mỗi loại xe
def plot_boxplot(df, classes, out_path="data/figures/boxplot.png"):
    """Vẽ boxplot để so sánh phân phối (quartile, median) của từng loại."""
    d = prepare_time_index(df)
    p = ensure_dir(out_path)
    d_melt = d[classes].melt(var_name="Vehicle", value_name="Count")
    sns.boxplot(data=d_melt, x="Vehicle", y="Count")
    plt.title("Boxplot - Distribution per vehicle type")
    plt.tight_layout()
    plt.savefig(p, dpi=150)
    plt.close()
    return str(p)

# 7. Rolling average - xu hướng mượt (trung bình động)
def plot_rolling_avg(df, classes, window=5, out_path="data/figures/rolling_avg.png"):
    """Vẽ đường xu hướng mượt bằng rolling average để loại bỏ nhiễu."""
    d = prepare_time_index(df)
    p = ensure_dir(out_path)
    d[classes].rolling(window=window).mean().plot()
    plt.title(f"Rolling average (window={window})")
    plt.tight_layout()
    plt.savefig(p, dpi=150)
    plt.close()
    return str(p)

# 8. Peak detection - phát hiện đỉnh lưu lượng
def plot_peak_detection(df, out_path="data/figures/total_line_peak.png"):
    """Vẽ tổng xe theo thời gian, đánh dấu các đỉnh (peaks) được phát hiện tự động."""
    d = prepare_time_index(df)
    p = ensure_dir(out_path)
    sns.lineplot(data=d, x=d.index, y="total", label="Total Traffic")
    peak_data = d[d["is_peak_auto"]]
    plt.scatter(peak_data.index, peak_data["total"], color='red', s=50, label="Auto Peak Detected", zorder=5)
    plt.title("Total Traffic Over Time with Peak Detection")
    plt.xlabel("Time")
    plt.ylabel("Total Count")
    plt.legend()
    plt.tight_layout()
    plt.savefig(p, dpi=150)
    plt.close()
    return str(p)

# 9. Stacked bar - tỷ lệ % mỗi loại theo thời gian
def plot_stacked_bar_percentage(df, classes, out_path="data/figures/stacked_bar_pct.png"):
    """Vẽ stacked bar 100% để thấy tỷ lệ thành phần từng loại theo thời gian."""
    d = prepare_time_index(df)
    p = ensure_dir(out_path)
    pct_cols = [c + "_pct" for c in classes if c + "_pct" in d.columns]
    d[pct_cols].plot(kind="bar", stacked=True, figsize=(14, 5))
    plt.title("100% Stacked Bar - Percentage Composition Over Time")
    plt.xlabel("Time")
    plt.ylabel("Percentage (%)")
    plt.legend(classes)
    plt.tight_layout()
    plt.savefig(p, dpi=150)
    plt.close()
    return str(p)

# ============ MAIN ============
if __name__ == "__main__":
    import argparse
    from analyze import analyze_pipeline_realtime

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/runtime/stats.json")
    parser.add_argument("--freq", default="1min")
    parser.add_argument("--classes", nargs="+", default=["car","motor","bus","truck"])
    args = parser.parse_args()

    # Nạp và xử lý dữ liệu
    merged = analyze_pipeline_realtime(args.input, out_dir="data/processed", agg_freq=args.freq)
    if merged is None or merged.empty:
        print("No data.")
        exit(0)

    # Vẽ tất cả biểu đồ
    print("Generating 9 visualizations...")
    outs = [
        plot_line_chart(merged, args.classes),
        plot_grouped_bar_minute(merged, args.classes),
        plot_area_chart(merged, args.classes),
        plot_pie_chart(merged, args.classes),
        plot_hist_total(merged),
        plot_boxplot(merged, args.classes),
        plot_rolling_avg(merged, args.classes, window=5),
        plot_peak_detection(merged),
        plot_stacked_bar_percentage(merged, args.classes),
    ]

    for o in outs:
        print("✅ Saved:", o)