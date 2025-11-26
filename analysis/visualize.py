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
from typing import Optional, Tuple

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
def plot_line_chart(df, classes, out_path: str = "data/figures/line_chart.png", fig: Optional[plt.Figure] = None,
                    ax: Optional[plt.Axes] = None, save: bool = True) -> Optional[Tuple[plt.Figure, plt.Axes]]:
    """Vẽ line chart theo từng loại xe.

    Thay đổi để hỗ trợ realtime:
    - Nếu `ax` được truyền vào, hàm chỉ cập nhật `ax` (không đóng figure).
    - Nếu `save` = True, kết quả được lưu ra `out_path` và trả về đường dẫn.
    - Nếu `save` = False, trả về `(fig, ax)` để caller có thể dùng lại.
    """
    d = prepare_time_index(df)

    created_fig = False
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 5))
        created_fig = True

    ax.clear()
    if len(d) > 0:
        d[classes].plot(ax=ax)
    ax.set_title("Line Chart - Vehicle counts over time")
    ax.set_xlabel("Time")
    ax.set_ylabel("Count")
    ax.legend()
    fig.tight_layout()

    if save:
        p = ensure_dir(out_path)
        fig.savefig(p, dpi=150)
        if created_fig:
            plt.close(fig)
        return str(p)
    return fig, ax


# 2. Biểu đồ cột nhóm - so sánh từng loại xe theo khoảng thời gian
def plot_grouped_bar_minute(df, classes, out_path: str = "data/figures/grouped_bar_minute.png",
                            fig: Optional[plt.Figure] = None, ax: Optional[plt.Axes] = None, save: bool = True):
    """Vẽ grouped bar chart; hỗ trợ reuse `ax` để update realtime."""
    d = prepare_time_index(df)
    created_fig = False
    if ax is None:
        fig, ax = plt.subplots(figsize=(14, 5))
        created_fig = True

    ax.clear()
    if len(d) > 0:
        # remove bar outlines to avoid dark edges and speed up rendering
        d[classes].plot(kind="bar", ax=ax, edgecolor='none', linewidth=0)
        # reduce x-tick labels density to improve redraw speed
        try:
            labels = ax.get_xticklabels()
            if len(labels) > 12:
                step = max(1, len(labels) // 12)
                for i, lab in enumerate(labels):
                    if i % step != 0:
                        lab.set_visible(False)
        except Exception:
            pass
    # ensure white background and avoid clipping when legend outside
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    ax.set_title("Grouped Bar - Per minute")
    ax.set_xlabel("Time")
    ax.set_ylabel("Count")
    # if a legend exists from previous draw, remove it before adding a new one
    old_leg = ax.get_legend()
    if old_leg:
        old_leg.remove()
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
    fig.tight_layout()

    if save:
        p = ensure_dir(out_path)
        fig.savefig(p, dpi=150)
        if created_fig:
            plt.close(fig)
        return str(p)
    return fig, ax


# 3. Area chart - phân bố tích lũy các loại xe
def plot_area_chart(df, classes, out_path: str = "data/figures/area_chart.png", fig: Optional[plt.Figure] = None,
                    ax: Optional[plt.Axes] = None, save: bool = True):
    """Vẽ area chart stacked; hỗ trợ reuse `ax` để update realtime."""
    d = prepare_time_index(df)
    created_fig = False
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 5))
        created_fig = True

    ax.clear()
    if len(d) > 0:
        # remove area borders to avoid dark lines between stacked areas
        d[classes].plot(kind="area", stacked=True, alpha=0.7, ax=ax, linewidth=0)
    ax.set_title("Area Chart - Vehicle counts")
    fig.tight_layout()

    if save:
        p = ensure_dir(out_path)
        fig.savefig(p, dpi=150)
        if created_fig:
            plt.close(fig)
        return str(p)
    return fig, ax


# 4. Pie chart - tỷ lệ phần trăm loại xe
def plot_pie_chart(df, classes, out_path: str = "data/figures/pie_chart.png", fig: Optional[plt.Figure] = None,
                   ax: Optional[plt.Axes] = None, save: bool = True, show_percent_threshold: float = 3.0):
    """
    Vẽ pie chart với các loại xe.
    - % >= 3%: hiển thị trên pie
    - % < 3%: ẩn trên pie (để tránh lộn xộn)
    - Tất cả % (kể cả nhỏ) hiển thị trong chú giải (legend)
    """
    
    def autopct_format(value):
        # Ẩn % nhỏ trên pie để tránh chồng chéo
        if value < show_percent_threshold:
            return '' 
        return f'{value:.1f}%'
            
    d = prepare_time_index(df)
    created_fig = False
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))
        created_fig = True

    # Tính tổng theo snapshot (mặc định dùng giá trị hiện tại nếu có index),
    # nhưng nếu muốn tổng trên toàn bộ window, caller có thể supply aggregated df.
    if len(d) == 0:
        ax.text(0.5, 0.5, "No data", ha='center')
        if save:
            p = ensure_dir(out_path)
            fig.savefig(p, dpi=150)
            if created_fig:
                plt.close(fig)
            return str(p)
        return fig, ax

    # Sử dụng tổng trên window (tổng các giá trị) để hiển thị tỷ lệ phần trăm (theo yêu cầu realtime)
    total_series = d[classes].sum()
    sums = {c: int(total_series.get(c, 0)) for c in classes if c in d.columns and total_series.get(c, 0) > 0}
    sorted_items = sorted(sums.items(), key=lambda item: item[1], reverse=True)
    labels = [it[0] for it in sorted_items]
    values = [it[1] for it in sorted_items]
    total_sum = sum(values)

    legend_labels = [f"{lbl}: {val} ({(val/total_sum*100):.1f}%)" for lbl, val in zip(labels, values)]

    # draw pie with white edges and white percent text for readability
    wedges, texts, autotexts = ax.pie(
        values,
        autopct=autopct_format,
        startangle=90,
        pctdistance=0.6,
        wedgeprops={"edgecolor": "white", "linewidth": 1},
        textprops={"color": "white", "weight": "bold"},
    )

    ax.legend(wedges,
              legend_labels,
              title="Loại xe",
              loc="center left",
              bbox_to_anchor=(1, 0, 0.5, 1))
    ax.set_title("Vehicle Type Distribution")
    fig.tight_layout()

    if save:
        p = ensure_dir(out_path)
        fig.savefig(p, dpi=150)
        if created_fig:
            plt.close(fig)
        return str(p)
    return fig, ax


# 5. Histogram - phân phối tần số lượng xe tổng
def plot_hist_total(df, out_path: str = "data/figures/hist_total.png", fig: Optional[plt.Figure] = None,
                    ax: Optional[plt.Axes] = None, save: bool = True):
    """Vẽ histogram của total; hỗ trợ reuse `ax`."""
    d = prepare_time_index(df)
    created_fig = False
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 5))
        created_fig = True

    ax.clear()
    if "total" in d.columns and len(d) > 0:
        # draw histogram with small gaps between bars (rwidth<1) and light edges
        # rwidth controls the relative width of the bars (0-1); 0.85 gives small separation
        d["total"].plot(kind="hist", bins=20, ax=ax, edgecolor='white', linewidth=0.5, rwidth=0.85, alpha=0.95)
    ax.set_title("Histogram - Total vehicle counts")
    ax.set_xlabel("Total")
    fig.tight_layout()

    if save:
        p = ensure_dir(out_path)
        fig.savefig(p, dpi=150)
        if created_fig:
            plt.close(fig)
        return str(p)
    return fig, ax

# 6. Boxplot - biến động mỗi loại xe
def plot_boxplot(df, classes, out_path: str = "data/figures/boxplot.png", fig: Optional[plt.Figure] = None,
                 ax: Optional[plt.Axes] = None, save: bool = True):
    """Vẽ boxplot; hỗ trợ reuse `ax`."""
    d = prepare_time_index(df)
    created_fig = False
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 5))
        created_fig = True

    ax.clear()
    if len(d) > 0:
        d_melt = d[classes].melt(var_name="Vehicle", value_name="Count")
        # lighten boxplot outlines to avoid heavy black lines
        sns.boxplot(data=d_melt, x="Vehicle", y="Count", ax=ax, fliersize=3)
    ax.set_title("Boxplot - Distribution per vehicle type")
    fig.tight_layout()

    if save:
        p = ensure_dir(out_path)
        fig.savefig(p, dpi=150)
        if created_fig:
            plt.close(fig)
        return str(p)
    return fig, ax

# 7. Rolling average - xu hướng mượt (trung bình động)
def plot_rolling_avg(df, classes, window=5, out_path: str = "data/figures/rolling_avg.png",
                     fig: Optional[plt.Figure] = None, ax: Optional[plt.Axes] = None, save: bool = True):
    """Vẽ rolling average; hỗ trợ reuse `ax`."""
    d = prepare_time_index(df)
    created_fig = False
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 5))
        created_fig = True

    ax.clear()
    if len(d) > 0:
        d[classes].rolling(window=window).mean().plot(ax=ax)
    ax.set_title(f"Rolling average (window={window})")
    fig.tight_layout()

    if save:
        p = ensure_dir(out_path)
        fig.savefig(p, dpi=150)
        if created_fig:
            plt.close(fig)
        return str(p)
    return fig, ax

# 8. Peak detection - phát hiện đỉnh lưu lượng
def plot_peak_detection(df, out_path: str = "data/figures/total_line_peak.png", fig: Optional[plt.Figure] = None,
                        ax: Optional[plt.Axes] = None, save: bool = True):
    """Vẽ tổng xe theo thời gian, đánh dấu các đỉnh (peaks) được phát hiện tự động."""
    d = prepare_time_index(df)
    created_fig = False
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 5))
        created_fig = True

    ax.clear()
    if len(d) > 0:
        sns.lineplot(data=d, x=d.index, y="total", label="Total Traffic", ax=ax)
        peak_data = d[d.get("is_peak_auto", False)]
        if not peak_data.empty:
            ax.scatter(peak_data.index, peak_data["total"], color='red', s=50, label="Auto Peak Detected", zorder=5)
    ax.set_title("Total Traffic Over Time with Peak Detection")
    ax.set_xlabel("Time")
    ax.set_ylabel("Total Count")
    ax.legend()
    fig.tight_layout()

    if save:
        p = ensure_dir(out_path)
        fig.savefig(p, dpi=150)
        if created_fig:
            plt.close(fig)
        return str(p)
    return fig, ax

# 9. Stacked bar - tỷ lệ % mỗi loại theo thời gian
def plot_stacked_bar_percentage(df, classes, out_path: str = "data/figures/stacked_bar_pct.png", fig: Optional[plt.Figure] = None,
                                ax: Optional[plt.Axes] = None, save: bool = True):
    """Vẽ stacked bar 100% để thấy tỷ lệ thành phần từng loại theo thời gian."""
    d = prepare_time_index(df)
    created_fig = False
    if ax is None:
        fig, ax = plt.subplots(figsize=(14, 5))
        created_fig = True

    ax.clear()
    pct_cols = [c + "_pct" for c in classes if c + "_pct" in d.columns]
    if pct_cols:
        # remove bar outlines and set legend labels to vehicle names
        d[pct_cols].plot(kind="bar", stacked=True, ax=ax, edgecolor='none', linewidth=0)
        ax.set_title("100% Stacked Bar - Percentage Composition Over Time")
        ax.set_xlabel("Time")
        ax.set_ylabel("Percentage (%)")
        legend_labels = [c.replace("_pct", "") for c in pct_cols]
        ax.legend(legend_labels)
        # reduce x-tick label density
        try:
            labels = ax.get_xticklabels()
            if len(labels) > 12:
                step = max(1, len(labels) // 12)
                for i, lab in enumerate(labels):
                    if i % step != 0:
                        lab.set_visible(False)
        except Exception:
            pass
    fig.tight_layout()

    if save:
        p = ensure_dir(out_path)
        fig.savefig(p, dpi=150)
        if created_fig:
            plt.close(fig)
        return str(p)
    return fig, ax

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