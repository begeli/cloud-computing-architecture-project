import glob
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter


def main():
    sb = False
    labels = []

    for run in ['T2_C1', 'T2_C2']:
        num_cores = int(run[-1])
        fig, ax = plt.subplots(figsize=(5, 5), dpi=80)
        ax.set_ylabel("95th Percentile Latency [ms]")

        ax.set_xlabel("Measured Queries Per Second")
        ax.set_title(f"{run[1]} threads, {run[4]} cores")
        plt.xlim([0, 105 * 1000])
        ax.set_ylim([0, 2.5])
        ax.set_yticks(np.arange(0, 2.75, 0.5))
        ax.tick_params(axis='y', labelcolor='tab:orange')

        plt.xticks(range(0, 105000, 10000))
        ax.grid(True)
        ax_cpu = ax.twinx()
        ax_cpu.set_ylabel("Total CPU utilization [%]")
        ax_cpu.tick_params(axis='y', labelcolor='tab:blue')
        ax_cpu.set_ylim([0, 105 * num_cores])
        ax_cpu.grid(True)

        ax.xaxis.set_major_formatter(
            FuncFormatter(lambda x_val, tick_pos: "{:.0f}k".format(x_val / 1000)))
        data = []
        all_files = glob.glob(os.path.join("../results_part4/Q2/CPU_Utilizations/ps_util_" + run +
                                           "/*.txt"))
        for filepath in all_files:
            file = open(filepath, "r")
            txt = file.readlines()
            txt = txt[2:]
            txt[-1] += '\n'
            measurements = sorted([sum(tuple(map(float, x[1:-2].split(',')))[:num_cores]) for x in txt])
            final_val = measurements[int(0.8 * len(measurements))]
            qps = float(os.path.basename(filepath)[4:-4])
            data.append({'target': qps, 'cpu_util': final_val})

        df = pd.DataFrame(data=data)
        df_lat = pd.read_csv('../results_part4/Q2/Latencies/latency_' + run + '/latency0.txt', delim_whitespace=True,
                             skiprows=1)
        df = df.join(df_lat.set_index('target'), on='target')
        df = df.sort_values('target')
        df = df[df['QPS'] > df['target'] - 5000]
        df["p95"] = df["p95"].divide(1000.0)
        df.plot(x='QPS', y='p95', legend=False, ax=ax, color='tab:orange', marker='o')
        df.plot(x='QPS', y='cpu_util', ax=ax_cpu, legend=False, color='tab:blue')
        ax.figure.legend([ax, ax_cpu],
                         labels=['95th perc. latency', 'CPU utilization'],
                         bbox_to_anchor=(0.88, 0.23),
                         bbox_transform=plt.gcf().transFigure)
        ax.plot([0, 105000], [2, 2], linestyle=':', color='grey')
        # plt.show()
        plt.savefig(f'plots/task4question2-{run}.pdf', bbox_inches='tight')

    def map_label(label):
        return f"{label[1]} threads, {label[4]} cores"

    labels = list(map(map_label, labels))
    plt.legend(title='Memcached config', loc='upper left', labels=labels)
    plt.close()


if __name__ == "__main__":
    main()
