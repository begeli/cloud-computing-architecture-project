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
    workload_df = workload_df[
        workload_df['event'].isin(['START', 'FINISH'])
    ]
    return workload_df


def main():
    labels = []

    for run in range(1, 2):
        latency_path = f'../results_part4/Q4/latency/mcperf_out_{run}.txt'
        df_lat = pd.read_csv(latency_path, delim_whitespace=True,
                             skiprows=7, skipfooter=11, engine='python')  # maybe skipfooter=9
        time_start, time_end = get_start_end(latency_path)
        df_lat["p95"] = df_lat["p95"].divide(1000.0)  # convert to ms
        timestamps = list(range(0, time_end - time_start, 10))

        log_df = pd.read_csv(f'../results_part4/Q4/log/log{run}.txt', skipinitialspace=True)
        controller_time_end = log_df.iloc[-1]['timestamp']
        controller_time_start = log_df.iloc[0]['timestamp']
        log_df['timestamp'] -= controller_time_start
        df_lat['timestamp'] = list(map(lambda x: x - controller_time_start + time_start, timestamps[:len(df_lat)]))

        memcached_df = log_df[log_df['process name'] == 'memchached']

        events = get_events(log_df)

        fig = plt.figure(figsize=(16, 12))
        axA_95p, axB_CPU_cores = fig.subplots(2, 1)

        def draw_events(ax):
            ax.set_xticks(events['timestamp'])
            ax.set_xticklabels(event_labels, rotation=90)
            # for tick in ax.get_xticklabels():
            #     tick.set_rotation(45)
            #     tick.set_rotation_mode('anchor')
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

            # ax.xaxis.set_major_locator(FixedLocator(locs=events['timestamp']))
            # ax.xaxis.set_major_formatter(
            #     plt.FuncFormatter(lambda val, idx: events.iloc[idx]['process name'] + ": " + events.iloc[idx]['event']))
            # df_lat.plot(x='timestamp', y='QPS', legend=False, ax=ax, color='tab:orange', grid=True, kind='scatter')

        # events = events[0:1000:100]
        event_labels = [row['process name'] + ": " + row['event'] for _, row in events.iterrows()]

    # axB_QPS.set_xlabel("Time [s]")

        # Plot A
        fig.suptitle(f'Run {run} visualization')
        axA_95p.set_title(f"Plot A")
        axA_95p.set_xlim([0, controller_time_end - controller_time_start])
        axA_95p.set_xlabel("Time [s]")
        draw_events(axA_95p)
        axA_95p.set_ylabel("95th Percentile Latency [ms]")
        axA_95p.tick_params(axis='y', labelcolor='tab:blue')
        axA_95p.set_ylim([0, 4.0])
        axA_95p.set_yticks(np.arange(0, 4.0, 0.4))
        # axA_95p.set_xticks(range(0, 1800, 10))
        # axA_95p.grid(True)

        axA_95p.plot(df_lat['timestamp'], df_lat['p95'], 'o-', color='tab:blue')
        axA_QPS = axA_95p.twinx()
        config_QPS_ax(axA_QPS)

        # Plot B
        axB_CPU_cores.set_title(f"Plot B")
        axB_CPU_cores.set_xlim([0, controller_time_end - controller_time_start])
        draw_events(axB_CPU_cores)

        axB_CPU_cores.set_ylabel('Memcached CPU cores')
        axB_CPU_cores.tick_params(axis='y', labelcolor='tab:green')

        axB_CPU_cores.plot(memcached_df['timestamp'], memcached_df['event'], drawstyle='steps-post', color='tab:green')
        axB_QPS = axB_CPU_cores.twinx()
        config_QPS_ax(axB_QPS)
        # axB_CPU_cores.set_ylim([-, 4])
        # axB_CPU_cores.set_yticks(range(4))

        fig.legend(labels=['95th perc. latency', 'Memcached cores', 'QPS'],
                   # bbox_to_anchor=(0.88, 0.19),
                   # bbox_transform=plt.gcf().transFigure,
                   loc='upper right'
                   )


        # # fig.tight_layout()
        # plt.setp(axA_QPS.xaxis.get_majorticklabels(), rotation=90)
        # plt.setp(axB_QPS.xaxis.get_majorticklabels(), rotation=90)
        # axA_QPS.tick_params(axis='x', labelrotation=120.0)
        # axB_QPS.tick_params(axis='x', labelrotation=40.0)
        # plt.xticks([100, 1000], ['blah', 'fre'], rotation='vertical')
        plt.subplots_adjust(hspace=1.0, bottom=0.2)
        plt.show()
        # plt.savefig(f'plots/task4question2-{run}.pdf', bbox_inches='tight')


if __name__ == "__main__":
    main()
