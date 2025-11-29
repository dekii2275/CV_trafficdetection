import time
import argparse
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from load_data import DEFAULT_CLASSES
from analyze import analyze_pipeline_realtime

def interactive_loop(stats_path, classes, interval=30, agg_freq="1T", minutes_window=10):
    plt.ion()
    from visualize import (
        plot_line_chart,
        plot_grouped_bar_minute,
        plot_area_chart,
        plot_pie_chart,
        plot_hist_total,
        plot_boxplot,
        plot_rolling_avg,
        plot_peak_detection,
        plot_stacked_bar_percentage,
    )
    figs = {}
    inited = False
    try:
        while True:
            df = analyze_pipeline_realtime(stats_path, out_dir="data/processed", agg_freq=agg_freq,
                                           minutes_window=minutes_window)
            if df is None or df.empty:
                print(f"[{datetime.now()}] No data, sleeping {interval}s...")
                time.sleep(interval)
                continue
            try:
                if not inited:
                    figs['line'] = plot_line_chart(df, classes, save=False)
                    figs['grouped'] = plot_grouped_bar_minute(df, classes, save=False)
                    figs['area'] = plot_area_chart(df, classes, save=False)
                    figs['pie'] = plot_pie_chart(df, classes, save=False)
                    figs['hist'] = plot_hist_total(df, save=False)
                    figs['box'] = plot_boxplot(df, classes, save=False)
                    figs['roll'] = plot_rolling_avg(df, classes, window=5, save=False)
                    figs['peak'] = plot_peak_detection(df, save=False)
                    figs['stack'] = plot_stacked_bar_percentage(df, classes, save=False)
                    inited = True
                else:
                    for key, fn in [
                        ('line', plot_line_chart),
                        ('grouped', plot_grouped_bar_minute),
                        ('area', plot_area_chart),
                        ('pie', plot_pie_chart),
                        ('hist', plot_hist_total),
                        ('box', plot_boxplot),
                        ('roll', plot_rolling_avg),
                        ('peak', plot_peak_detection),
                        ('stack', plot_stacked_bar_percentage),
                    ]:
                        fig_ax = figs.get(key)
                        if not fig_ax:
                            continue
                        fig_obj, ax_obj = fig_ax
                        if key == 'roll':
                            fn(df, classes, window=5, fig=fig_obj, ax=ax_obj, save=False)
                        elif key in ('line','grouped','area','box','stack'):
                            fn(df, classes, fig=fig_obj, ax=ax_obj, save=False)
                        elif key in ('hist','peak'):
                            fn(df, fig=fig_obj, ax=ax_obj, save=False)
                        elif key == 'pie':
                            fn(df, classes, fig=fig_obj, ax=ax_obj, save=False)
                for fig_obj, ax_obj in figs.values():
                    fig_obj.canvas.draw()
                    fig_obj.canvas.flush_events()
            except Exception as e:
                print(f"Error updating charts: {e}")
    except KeyboardInterrupt:
        print("Stopped by user")
    finally:
        plt.ioff()


def headless_loop(stats_path, classes, interval=30, agg_freq="1T", minutes_window=10):
    from visualize import (
        plot_line_chart,
        plot_grouped_bar_minute,
        plot_area_chart,
        plot_pie_chart,
        plot_hist_total,
        plot_boxplot,
        plot_rolling_avg,
        plot_peak_detection,
        plot_stacked_bar_percentage,
    )
    try:
        while True:
            df = analyze_pipeline_realtime(stats_path, out_dir="data/processed", agg_freq=agg_freq,
                                           minutes_window=minutes_window)
            if df is None or df.empty:
                print(f"[{datetime.now()}] No data, sleeping {interval}s...")
                time.sleep(interval)
                continue
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            out_prefix = f"data/figures/realtime_{ts}"
            plot_line_chart(df, classes, out_path=out_prefix + "_line.png")
            plot_grouped_bar_minute(df, classes, out_path=out_prefix + "_grouped.png")
            plot_area_chart(df, classes, out_path=out_prefix + "_area.png")
            plot_pie_chart(df, classes, out_path=out_prefix + "_pie.png")
            plot_hist_total(df, out_path=out_prefix + "_hist.png")
            plot_boxplot(df, classes, out_path=out_prefix + "_box.png")
            plot_rolling_avg(df, classes, window=5, out_path=out_prefix + "_roll.png")
            plot_peak_detection(df, out_path=out_prefix + "_peak.png")
            plot_stacked_bar_percentage(df, classes, out_path=out_prefix + "_stack.png")
            print(f"[{datetime.now()}] Saved snapshots with prefix {out_prefix}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Stopped by user")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/runtime/stats.json", help="path to stats.json")
    parser.add_argument("--interval", type=int, default=30, help="seconds between updates")
    parser.add_argument("--headless", action="store_true", help="run in headless mode (save PNGs)")
    parser.add_argument("--freq", default="1T", help="aggregation freq passed to pipeline")
    parser.add_argument("--minutes", type=int, default=10, help="how many minutes of data to load")
    parser.add_argument("--classes", nargs="+", default=DEFAULT_CLASSES)
    args = parser.parse_args()
    if args.headless:
        headless_loop(args.input, args.classes, interval=args.interval, agg_freq=args.freq, minutes_window=args.minutes)
    else:
        interactive_loop(args.input, args.classes, interval=args.interval, agg_freq=args.freq, minutes_window=args.minutes)


if __name__ == "__main__":
    main()
