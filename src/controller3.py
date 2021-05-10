from time import sleep
from queue import Queue
import psutil
import docker
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

# Initialize client object for docker.
client = docker.from_env()

# Initialize queues for parsec jobs.
queue1 = Queue(maxsize = 6) # Max no. of parsec jobs is 6.
queue2 = Queue(maxsize = 6)

# Parsec jobs - (assigned cpus,  name, image, command to run)
dedup = ("1", "dedup", "anakli/parsec:dedup-native-reduced", "./bin/parsecmgmt -a run -p dedup -i native -n 1")
fft = ("1", "splash2x-fft", "anakli/parsec:splash2x-fft-native-reduced", "./bin/parsecmgmt -a run -p splash2x.fft -i native -n 1")
blackscholes = ("1", "blackscholes", "anakli/parsec:blackscholes-native-reduced", "./bin/parsecmgmt -a run -p blackscholes -i native -n 1")
canneal = ("2,3", "canneal", "anakli/parsec:canneal-native-reduced", "./bin/parsecmgmt -a run -p canneal -i native -n 2")
freqmine = ("2,3", "freqmine", "anakli/parsec:freqmine-native-reduced", "./bin/parsecmgmt -a run -p freqmine -i native -n 2")
ferret = ("2,3", "ferret", "anakli/parsec:ferret-native-reduced", "./bin/parsecmgmt -a run -p ferret -i native -n 2")

# Fill the first queue.
queue1.put(fft)
queue1.put(blackscholes)

# Fill the second queue.
queue2.put(freqmine)
queue2.put(ferret)

# Flag to keep track of whether last job is deleted or not - I am sure there is a more elegant way of doing this, but am I gonna???
isLastDeleted1 = False
isLastDeleted2 = False

# First psutil.cpu_percent measurement is always incorrect - Call it once to get proper results later on.
psutil.cpu_percent(interval=None, percpu=True)

memcached_config = init_memcached_config()

# Setup is completed - start scheduling
print("Creating containers!")
#client.containers.get("dedup").remove()
#client.containers.get("canneal").kill()
#client.containers.get("canneal").remove()

container1 = client.containers.create(cpuset_cpus=dedup[0], name=dedup[1], detach=True, auto_remove=False, image=dedup[2], command=dedup[3])
container1.reload()

container2 = client.containers.create(cpuset_cpus=canneal[0], name=canneal[1], detach=True, auto_remove=False, image=canneal[2], command=canneal[3])
container2.reload()

# Measure CPU utilization every 1.0 seconds. Adaptively change the CPU assignment of memcached based on load.
while(True):
    cpu_utilizations = psutil.cpu_percent(interval=None, percpu=True)

    # If we are using one core and its utilization is over 90.0% increase the number of cores to 2.
    if memcached_config[1] == 1 and cpu_utilizations[0] > 90.0:
        if not isLastDeleted1 and isLastDeleted2:
            print("Changing cpu set of container 1 to 2 and 3.")
            container1.update(cpuset_cpus="2,3")
        elif not isLastDeleted1 and container1.status == "running":
            print(f"Pausing {container1.name}")
            container1.pause()

        # Unlikely scenario
        if isLastDeleted1 and not isLastDeleted2:
            container2.update(cpuset_cpus="2,3")

        memcached_config = set_memcached_cpu(memcached_config[0], 2)
    # If we are using 2 cores and the average utilization of the cores is less than or equal to 60.0% switch to 1 core.
    # Normally 55k QPS is the upper limit for memcache to handle requests without violating the SLO which is around 65.0% average CPU 
    # utilization for two CPUs. We set the threshold for switching back to 1 CPU to 60.0% average CPU utilizations, so, for QPS around
    # 55k the controller doesn't constantly switch between 1 CPU to 2 CPUs.
    elif memcached_config[1] == 2 and ( ((cpu_utilizations[0] + cpu_utilizations[1]) / 2.0) <= 60.0):
        memcached_config = set_memcached_cpu(memcached_config[0], 1)

        if not isLastDeleted1 and isLastDeleted2:
            print("Changing cpu set of container 1 to 1,2 and 3.")
            container1.update(cpuset_cpus="1-3")
        elif not isLastDeleted1 and container1.status == "paused":
            print(f"Unpausing {container1.name}")
            container1.unpause()

        if isLastDeleted1 and not isLastDeleted2:
            container2.update(cpuset_cpus="1-3")

'''
    if memcached_config[1] == 2 and ( ((cpu_utilizations[0] + cpu_utilizations[1]) / 2.0) >= 95.0):
        if not isLastDeleted1 and isLastDeleted2:
            container1.pause()
        elif isLastDeleted1 and not isLastDeleted2:
            container2.pause()
        elif not isLastDeleted1 and not isLastDeleted2:
            container2.pause()
    elif memcached_config[1] == 2 and ( ((cpu_utilizations[0] + cpu_utilizations[1]) / 2.0) <= 90.0):
        if not isLastDeleted1 and isLastDeleted2 and container1.status == "paused":
            container1.unpause()                    
        elif isLastDeleted1 and not isLastDeleted2 and container2.status == "paused":
            container2.unpause()
        elif not isLastDeleted1 and not isLastDeleted2 and container2.status == "paused":
            container2.unpause()
'''

    if (memcached_config[1] == 1 and container1.status == "created"):
        print(f"Starting {container1.name}")
        container1.start()

    if (container2.status == "created"):
        print(f"Starting {container2.name}")
        container2.start()

    if ((not queue1.empty()) and container1.status == "exited"):
        # Delete the container that stopped its execution.
        print(f"Removing {container1.name}")
        client.containers.get(container1.name).remove()

        # Start the next job in the queue.
        job = queue1.get()
        print(f"Running {job[1]}.")
        container1 = client.containers.run(cpuset_cpus=job[0], name=job[1], detach=True, auto_remove=False, image=job[2], command=job[3])

    if ((not queue2.empty()) and container2.status == "exited"):
        # Delete the container that stopped its execution.
        print(f"Removing {container2.name}")
        client.containers.get(container2.name).remove()

        # Start the next job in the queue.
        job = queue2.get()
        print(f"Running {job[1]}.")
        container2 = client.containers.run(cpuset_cpus=job[0], name=job[1], detach=True, auto_remove=False, image=job[2], command=job[3])

    if (queue1.empty() and not isLastDeleted1 and container1.status == "exited"):
        isLastDeleted1 = True
        # Delete the container that stopped its execution.
        print(f"Removing {container1.name}")
        client.containers.get(container1.name).remove()

    if (queue2.empty() and not isLastDeleted2 and container2.status == "exited"):
        isLastDeleted2 = True
        # Delete the container that stopped its execution.
        print(f"Removing {container2.name}")
        client.containers.get(container2.name).remove()

    if not isLastDeleted1:
        container1.reload()

    if not isLastDeleted2:
        container2.reload()

    sleep(0.5)

