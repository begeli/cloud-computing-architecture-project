import glob
import os

import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


def conf_interval_left(data, confidence=95):
    # return st.t.interval(confidence/100.0, len(data)-1, loc=np.mean(data), scale=st.sem(data))[0]
    return sns.utils.ci(sns.algorithms.bootstrap(data, n_boot=1000), which=confidence)[0]

def conf_interval_right(data, confidence=95):
    return sns.utils.ci(sns.algorithms.bootstrap(data, n_boot=1000), which=confidence)[1]

def main():
    fig, ax = plt.subplots(figsize=(6, 6), dpi=80)
    plt.ylabel("95th Percentile Latency [ms]")
    plt.xlabel("Measured Queries Per Second")
    plt.xlim([0, 120000])
    plt.ylim([0, 3])
    plt.yticks(np.arange(0, 4, 0.5))
    plt.xticks(range(0, 120000, 10000))
    plt.grid(True)

    ax.xaxis.set_major_formatter(
        FuncFormatter(lambda x_val, tick_pos: "{:.0f}k".format(x_val / 1000)))

    sb = False
    labels = []

    for subdir in os.scandir("../results_part4/Q1"):
        all_files = glob.glob(os.path.join(subdir.path, "*.txt"))
        dfs = (pd.read_csv(file, delim_whitespace=True, skiprows=1) for file in all_files)
        data = pd.concat(dfs, ignore_index=True)
        data["p95"] = data["p95"].divide(1000.0)

        data_agg = data[["target", "p95", "QPS"]].groupby("target", as_index=False).agg([
            ('mean', np.mean),
            ('conf_interval_left', conf_interval_left),
            ('conf_interval_right', conf_interval_right),
        ]).reset_index()

        data_agg = data_agg[data_agg["QPS"]["mean"] > data_agg["target"] - 5000]
        labels += [subdir.name]
        if sb:
            sns.lineplot(data=data, x=data["target"], y=data["p95"],
                         label=subdir.name,
                         marker='o',
                         err_style="bars",
                         err_kws={'capsize': 4, 'capthick': 1.3, 'elinewidth': 1.5},
                         ax=ax
                         )
        else:
            xerr = [data_agg["QPS"]["mean"] - data_agg["QPS"]["conf_interval_left"],
                    data_agg["QPS"]["conf_interval_right"] - data_agg["QPS"]["mean"]]
            yerr = [data_agg["p95"]["mean"] - data_agg["p95"]["conf_interval_left"],
                    data_agg["p95"]["conf_interval_right"] - data_agg["p95"]["mean"]]
            ax.errorbar(data_agg["QPS"]["mean"], data_agg["p95"]["mean"],
                        xerr=xerr,
                        yerr=yerr,
                        capsize=4,
                        capthick=1.3,
                        elinewidth=1.5,
                        fmt='o-',
                        mec='white',
                        mew=.75,
                        )

    def map_label(label):
        return f"{label[1]} threads, {label[4]} cores"
    labels = list(map(map_label, labels))
    plt.legend(title='Memcached config', loc='upper left', labels=labels)
    plt.savefig('plots/task4question1.pdf', bbox_inches='tight')
    plt.close()


if __name__ == "__main__":
    main()