from time import sleep
import psutil
import subprocess

'''
The initial prototype of our controller.

To use this file inside the VMs do the following instructions:
1) Create a python file (i.e. controller.py) inside the VM.
2) Copy the contents of this file into the file in VM.
3) Download pip3/pip. (VMs we use have python3, so, you will probably have to download pip3.)
4) Download psutil library using pip3/pip.
5) Start executing the code.

Currently, the prototype successfully adjusts the number of cores according to the random load generated
by mcperf. 

Controller switches from 1 core to 2 cores when the core 0's CPU utilization exceeds 90.0%.
Controller switches from 2 cores to 1 core when the average CPU utilization of both cores drops below 65.0%. 
You can adjust these percentages based on the measurements we have in the part4_measurements file. (Compare the latency values in the latency folder
with CPU utilizations in the CPU utilizations folder.)
'''

def init_memcached_config():
    process_name = "memcache"
    pid = None

    # Find the pid of memcache
    for proc in psutil.process_iter():
        if process_name in proc.name():
            pid = proc.pid
            break

    # Set the cpu affinity of memcached to CPU 0
    set_memcached_cpu(pid, 1)
    
    # Return the current memcached config
    return (pid, 1)


def set_memcached_cpu(pid, no_of_cpus):
    cpu_affinity = "0" if no_of_cpus == 1 else "0,1"
    print(f'Setting Memcached CPU affinity to {cpu_affinity}')

    command = f'sudo taskset -a -cp {cpu_affinity} {pid}'
    subprocess.run(command.split(" "))

    return (pid, no_of_cpus)

# First psutil.cpu_percent measurement is always incorrect - Call it once to get proper results later on.
psutil.cpu_percent(interval=None, percpu=True)

memcached_config = init_memcached_config()

# Measure CPU utilization every 1.0 seconds. Adaptively change the CPU assignment of memcached based on load.
while(True):
    cpu_utilizations = psutil.cpu_percent(interval=None, percpu=True)

    # If we are using one core and its utilization is over 90.% increase the number of cores to 2.
    if memcached_config[1] == 1 and cpu_utilizations[0] > 90.0:
        memcached_config = set_memcached_cpu(memcached_config[0], 2)
    # If we are using 2 cores and the average utilization of the cores is less than or equal to 65.0% switch to 1 core.
    elif memcached_config[1] == 2 and ( ((cpu_utilizations[0] + cpu_utilizations[1]) / 2.0) <= 65.0):
        memcached_config = set_memcached_cpu(memcached_config[0], 1)

    sleep(1)
