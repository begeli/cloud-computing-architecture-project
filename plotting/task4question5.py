import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

INTERVAL_SECONDS = 8


def get_start_end(path):
    with open(path, 'r') as f:
        lines = f.readlines()
        start_time = float(lines[3].split(sep=' ')[-1])
        end_time = float(lines[4].split(sep=' ')[-1])
    return int(start_time / 1000), int(end_time / 1000)


def get_events(df: pd.DataFrame):
    workload_df = df[
        df['process name'].isin(['ferret', 'dedup', 'canneal', 'freqmine', 'splash2x-fft', 'blackscholes'])]
    return workload_df


def make_stats_entry(name, mean, std):
    return f'{name} & {mean:.2f} & {std:.2f} \\\\ \\hline'


def get_time_for_job(df, name):
    start_time = df[(df['process name'] == name) & (df['event'] == 'START')]['timestamp']
    end_time = df[(df['process name'] == name) & (df['event'] == 'FINISH')]['timestamp']
    return end_time.item() - start_time.item()


def main():
    jobs = ['dedup', 'blackscholes', 'ferret', 'freqmine', 'canneal', 'splash2x-fft', 'controller']
    runtimes = {name: [] for name in jobs}

    total_violations = []
    total_datapoints = []
    for run in range(1, 4):
        latency_path = f'../results_part4/Q5/latency/memcached_{INTERVAL_SECONDS}s_{run}.txt'
        df_lat = pd.read_csv(latency_path, delim_whitespace=True,
                             skiprows=6, skipfooter=11, engine='python')
        time_start, time_end = get_start_end(latency_path)
        df_lat["p95"] = df_lat["p95"].divide(1000.0)  # convert to ms
        total_datapoints += [len(df_lat)]
        total_violations += [sum(df_lat['p95'] > 2.0)]
        timestamps = list(range(0, time_end - time_start, INTERVAL_SECONDS))

        log_df = pd.read_csv(f'../results_part4/Q5/log/log_{INTERVAL_SECONDS}s_{run}.csv', skipinitialspace=True)
        controller_time_end = log_df.iloc[-1]['timestamp']
        controller_time_start = log_df.iloc[0]['timestamp']
        log_df['timestamp'] -= controller_time_start
        for name in jobs:
            runtimes[name].append(get_time_for_job(log_df, name))

        df_lat['timestamp'] = list(map(lambda x: x - controller_time_start + time_start, timestamps[:len(df_lat)]))

        memcached_df = log_df[log_df['process name'] == 'memchached']

        events = get_events(log_df)

        fig = plt.figure(figsize=(16, 12))
        axA_95p, ax_events, axB_CPU_cores = fig.subplots(3, 1, gridspec_kw={'height_ratios': [3, 1, 3]})

        def config_QPS_ax(ax):
            ax.set_ylabel("Queries per second")
            ax.set_ylim([0, 100000])
            ax.set_yticks(np.arange(0, 100001, 10000))
            ax.yaxis.set_major_formatter(
                FuncFormatter(lambda x_val, tick_pos: "{:.0f}k".format(x_val / 1000)))
            ax.tick_params(axis='y', labelcolor='tab:orange')
            ax.grid(True)
            return ax.scatter(df_lat['timestamp'], df_lat['QPS'], color='tab:orange')

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
            if len(entries) % 2 == 1:
                print(f"Something weird happened...: \n{entries.iloc[-2]}\n but no matching action. Skipping.")

            for i in range(0, len(entries), 2):
                if len(entries) % 2 == 1 and i == len(entries) - 3:
                    ax_events.plot([entries.iloc[i]['timestamp'], entries.iloc[i + 2]['timestamp']],
                                   [idx, idx], color=color, linewidth=3)
                    break
                else:
                    ax_events.plot([entries.iloc[i]['timestamp'], entries.iloc[i + 1]['timestamp']],
                                   [idx, idx], color=color, linewidth=3)
            ax_events.scatter([entries.iloc[0]['timestamp']], [idx], c=color, marker='o')
            ax_events.scatter([entries.iloc[-1]['timestamp']], [idx], c=color, marker='x')

        # Plot A
        fig.suptitle(f'Run {run} visualization')
        axA_95p.set_title(f"Plot {run}A")
        axA_95p.set_xlim([0, length])
        axA_95p.set_xlabel("Time [s]")
        axA_95p.set_xticks(range(0, length, 100))
        # axA_95p.grid(True)
        # draw_events(axA_95p)
        axA_95p.set_ylabel("95th Percentile Latency [ms]")
        axA_95p.tick_params(axis='y', labelcolor='tab:blue')
        axA_95p.set_ylim([0, 4.0])
        axA_95p.set_yticks(np.arange(0, 4.0, 0.4))

        artistA_95p, = axA_95p.plot(df_lat['timestamp'], df_lat['p95'], 'o-', color='tab:blue')
        axA_QPS = axA_95p.twinx()
        artistA_QPS = config_QPS_ax(axA_QPS)
        axA_QPS.legend([artistA_QPS, artistA_95p], ['QPS', '95 percentile latency'], loc='upper right')

        # Plot B
        axB_CPU_cores.set_xlim([0, length])
        axB_CPU_cores.set_xlabel(f"Time [s]\nPlot {run}B")
        axB_CPU_cores.set_xticks(range(0, length, 100))
        axB_CPU_cores.grid(True)

        axB_CPU_cores.set_ylabel('Memcached CPU cores')
        axB_CPU_cores.tick_params(axis='y', labelcolor='tab:green')

        artistB_CPU_cores, = axB_CPU_cores.plot(memcached_df['timestamp'], memcached_df['event'], drawstyle='steps-post', color='tab:green')
        axB_QPS = axB_CPU_cores.twinx()
        artistB_QPS = config_QPS_ax(axB_QPS)
        axB_QPS.legend([artistB_QPS, artistB_CPU_cores], ['QPS', 'Memcached CPU cores'], loc='upper right')

        plt.subplots_adjust(hspace=0.2, bottom=0.2)
        fig.tight_layout()

        # plt.show()
        plt.savefig(f'plots/task4question5-{run}.pdf', bbox_inches='tight')

    name_map = {'splash2x-fft': 'fft', 'controller': 'total time'}
    print(runtimes)
    for name in jobs:
        arr = np.array(runtimes[name])
        print(make_stats_entry(name_map.get(name, name), arr.mean(), arr.std()))

    for idx, v in enumerate(total_violations):
        print(f"{idx}: {(100*v / total_datapoints[idx]):.2f}%")
    print(f'TOTAL SLO VIOLATION RATE: {sum(total_violations) / sum(total_datapoints)}')


if __name__ == "__main__":
    main()
