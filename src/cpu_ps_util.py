from __future__ import print_function
from time import sleep
import psutil

print("Starting measuring cpu utilization percentages")
print("Each number represents the percentage of cpu used per cpu.")

for i in range(50):
    print(psutil.cpu_percent(interval=None, percpu=True))
    sleep(1)
