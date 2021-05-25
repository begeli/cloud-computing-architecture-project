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


def get_cores(timestamps, log_df):
    memcached_df = log_df[log_df['process name'] == 'memchached']
    # last_event_index = np.searchsorted(memcached_df.timestamp, timestamps, side='left')
    # memcached_cores = pd.concat([pd.Series([1]), memcached_df['event'].astype(int)])  # We add 1 in the beginning because we start with 1
    # return memcached_cores.iloc[last_event_index].reset_index(drop=True)


def main():
    labels = []

    for run in range(1, 2):
        latency_path = f'../results_part4/Q4/latency/sample_{run}.txt'
        df_lat = pd.read_csv(latency_path, delim_whitespace=True,
                             skiprows=7, skipfooter=11)  # maybe skipfooter=9
        time_start, time_end = get_start_end(latency_path)
        df_lat["p95"] = df_lat["p95"].divide(1000.0)  # convert to ms
        timestamps = list(range(0, time_end - time_start, 10))
        df_lat["timestamp"] = timestamps[:len(df_lat)]

        log_df = pd.read_csv(f'../results_part4/Q4/log/log.log', skipinitialspace=True)
        log_df['timestamp'] -= time_start
        memcached_df = log_df[log_df['process name'] == 'memchached']
        fig = plt.figure(figsize=(16, 8))
        axA_95p, axB_CPU_cores = fig.subplots(2, 1)
        # axA_95p, axB_CPU_cores = fig.subplots(2, 1, sharex=False)

        def config_QPS_ax(ax):
            ax.set_ylabel("Queries per second")
            ax.set_ylim([0, 100000])
            ax.set_yticks(np.arange(0, 100001, 10000))
            ax.yaxis.set_major_formatter(
                FuncFormatter(lambda x_val, tick_pos: "{:.0f}k".format(x_val / 1000)))
            ax.tick_params(axis='y', labelcolor='tab:orange')
            df_lat.plot(x='timestamp', y='QPS', legend=False, ax=ax, color='tab:orange', grid=True, kind='scatter')

            # def running_mean(x, N):
            #     cumsum = np.cumsum(np.insert(x, 0, 0))
            #     return (cumsum[N:] - cumsum[:-N]) / float(N)
            # ax.plot(df_lat['timestamp'][2:], running_mean(df_lat['QPS'].to_numpy(), 3), color='tab:orange')

        # Plot A
        axA_QPS = axA_95p.twinx()
        fig.suptitle(f'Run {run} visualization')
        axA_95p.set_title(f"Plot A")
        axA_95p.set_xlim([0, time_end - time_start])
        config_QPS_ax(axA_QPS)

        axA_95p.set_ylabel("95th Percentile Latency [ms]")
        axA_95p.tick_params(axis='y', labelcolor='blue')
        # axA_95p.set_ylim([0, 3.6])
        axA_95p.set_xticks(range(0, 1800, 10))
        plt.setp(axA_95p.get_xticklabels(), visible=True)
        # axA_95p.grid(True)
        axA_95p.set_xlabel("Time [s]")

        df_lat.plot(x='timestamp', y='p95', legend=False, ax=axA_95p, color='tab:blue')

        # Plot B
        axB_CPU_cores.set_title(f"Plot B")
        axB_QPS = axB_CPU_cores.twinx()
        config_QPS_ax(axB_QPS)
        axB_QPS.set_xlim([0, time_end - time_start])

        axB_CPU_cores.set_ylabel('Memcached CPU cores')
        axB_CPU_cores.tick_params(axis='y', labelcolor='tab:green')

        axB_CPU_cores.plot(memcached_df['timestamp'], memcached_df['event'], drawstyle='steps-post', color='tab:green')
        # axB_CPU_cores.set_ylim([-, 4])
        # axB_CPU_cores.set_yticks(range(4))

        fig.legend(labels=['95th perc. latency', 'Memcached cores', 'QPS'],
                   # bbox_to_anchor=(0.88, 0.19),
                   # bbox_transform=plt.gcf().transFigure,
                   loc='upper right'
                   )

        axB_CPU_cores.set_xlabel("Time [s]")
        plt.xlabel("Time [s]")
        plt.show()
        # plt.savefig(f'plots/task4question2-{run}.pdf', bbox_inches='tight')




if __name__ == "__main__":
    main()
