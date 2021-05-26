import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter


def get_start_end(path):
    with open(path, 'r') as f:
        lines = f.readlines()
        start_time = float(lines[4].split(sep=' ')[-1])
        end_time = float(lines[5].split(sep=' ')[-1])
    return int(start_time / 1000), int(end_time / 1000)


def get_events(df: pd.DataFrame):
    workload_df = df[
        df['process name'].isin(['ferret', 'dedup', 'canneal', 'freqmine', 'splash2x-fft', 'blackscholes'])]
    # workload_df = workload_df[
    #     workload_df['event'].isin(['START', 'FINISH', ''])
    # ]
    return workload_df


def main():
    for run in range(1, 4):
        latency_path = f'../results_part4/Q4/latency/mcperf_out_{run}.txt'
        df_lat = pd.read_csv(latency_path, delim_whitespace=True,
                             skiprows=7, skipfooter=11, engine='python')  # maybe skipfooter=9
        time_start, time_end = get_start_end(latency_path)
        df_lat["p95"] = df_lat["p95"].divide(1000.0)  # convert to ms
        timestamps = list(range(0, time_end - time_start, 10))

        log_df = pd.read_csv(f'../results_part4/Q4/log/log-{run}.txt', skipinitialspace=True)
        controller_time_end = log_df.iloc[-1]['timestamp']
        controller_time_start = log_df.iloc[0]['timestamp']
        log_df['timestamp'] -= controller_time_start
        df_lat['timestamp'] = list(map(lambda x: x - controller_time_start + time_start, timestamps[:len(df_lat)]))

        memcached_df = log_df[log_df['process name'] == 'memchached']

        events = get_events(log_df)

        fig = plt.figure(figsize=(16, 12))
        axA_95p, ax_events, axB_CPU_cores = fig.subplots(3, 1, gridspec_kw={'height_ratios': [3, 1, 3]})

        def draw_events(ax):
            ax.set_xticks(events['timestamp'])
            ax.set_xticklabels(event_labels, rotation=90)
            ax.set_xlabel("Time [s]")

        def config_QPS_ax(ax):
            ax.set_ylabel("Queries per second")
            ax.set_ylim([0, 100000])
            ax.set_yticks(np.arange(0, 100001, 10000))
            ax.yaxis.set_major_formatter(
                FuncFormatter(lambda x_val, tick_pos: "{:.0f}k".format(x_val / 1000)))
            ax.tick_params(axis='y', labelcolor='tab:orange')
            ax.scatter(df_lat['timestamp'], df_lat['QPS'], color='tab:orange')
            ax.grid(True)
        event_labels = [row['process name'] + ": " + row['event'] for _, row in events.iterrows()]

        length = int(controller_time_end - controller_time_start)
        # Events plot.

        workloads = ['ferret', 'dedup', 'canneal', 'freqmine', 'splash2x-fft', 'blackscholes']
        ax_events.set_yticks(range(6))
        ax_events.set_yticklabels(workloads)
        ax_events.set_ylim([-1, 6])
        ax_events.set_xlim([0, length])
        ax_events.set_xticks(range(0, length + 1, 100))
        ax_events.grid(True)

        for idx, name in enumerate(workloads):
            entries = events[events['process name'] == name]
            color = f'C{idx}'
            for i in range(0, len(entries), 2):
                ax_events.plot([entries.iloc[i]['timestamp'], entries.iloc[i+1]['timestamp']],
                               [idx, idx], color=color, linewidth=3)
            ax_events.scatter([entries.iloc[0]['timestamp']], [idx], c=color, marker='o')
            ax_events.scatter([entries.iloc[-1]['timestamp']], [idx], c=color, marker='x')


        # Plot A
        fig.suptitle(f'Run {run} visualization')
        axA_95p.set_title(f"Plot A")
        axA_95p.set_xlim([0, length])
        axA_95p.set_xlabel("Time [s]")
        axA_95p.set_xticks(range(0, length, 100))
        axA_95p.grid(True)
        # draw_events(axA_95p)
        axA_95p.set_ylabel("95th Percentile Latency [ms]")
        axA_95p.tick_params(axis='y', labelcolor='tab:blue')
        axA_95p.set_ylim([0, 4.0])
        axA_95p.set_yticks(np.arange(0, 4.0, 0.4))

        axA_95p.plot(df_lat['timestamp'], df_lat['p95'], 'o-', color='tab:blue')
        axA_QPS = axA_95p.twinx()
        config_QPS_ax(axA_QPS)

        # Plot B
        # axB_CPU_cores.set_title(f"Plot B")
        axB_CPU_cores.set_xlim([0, length])
        axB_CPU_cores.set_xlabel("Time [s]\nPlot B")
        axB_CPU_cores.set_xticks(range(0, length, 100))
        axB_CPU_cores.grid(True)
        # draw_events(axB_CPU_cores)

        axB_CPU_cores.set_ylabel('Memcached CPU cores')
        axB_CPU_cores.tick_params(axis='y', labelcolor='tab:green')

        axB_CPU_cores.plot(memcached_df['timestamp'], memcached_df['event'], drawstyle='steps-post', color='tab:green')
        axB_QPS = axB_CPU_cores.twinx()
        config_QPS_ax(axB_QPS)

        fig.legend(labels=['95th perc. latency', 'Memcached cores', 'QPS'],
                   loc='upper right'
                   )
        plt.subplots_adjust(hspace=0.2, bottom=0.2)
        # plt.subplots_adjust(hspace=1.0, bottom=0.2)
        fig.tight_layout()

        # plt.show()
        plt.savefig(f'plots/task4question4-{run}.pdf', bbox_inches='tight')


if __name__ == "__main__":
    main()
