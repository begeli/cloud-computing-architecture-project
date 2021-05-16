import subprocess
from queue import Queue
from time import sleep

import docker
import psutil


# Returns tuple with pid of memcached and number of cpus (=1)
def init_memcached_config():
    process_name = "memcache"
    pid = None

    # Find the pid of memcache
    for proc in psutil.process_iter():
        if process_name in proc.name():
            pid = proc.pid
            break

    # Set the cpu affinity of memcached to CPU 0
    return set_memcached_cpu(pid, 1)


def set_memcached_cpu(pid, no_of_cpus):
    cpu_affinity = "0" if no_of_cpus == 1 else "0,1"
    print(f'Setting Memcached CPU affinity to {cpu_affinity}')
    command = f'sudo taskset -a -cp {cpu_affinity} {pid}'
    subprocess.run(command.split(" "))
    return pid, no_of_cpus


NORMAL = "normal"
HIGH = "high"
CRITICAL = "critical"

# Initialize client object for docker.
client = docker.from_env()

dedup = ("1",
        "dedup",
        "anakli/parsec:dedup-native-reduced",
        "./bin/parsecmgmt -a run -p dedup -i native -n 1")
fft = ("1",
        "splash2x-fft",
        "anakli/parsec:splash2x-fft-native-reduced",
        "./bin/parsecmgmt -a run -p splash2x.fft -i native -n 1")
blackscholes = ("1",
        "blackscholes",
        "anakli/parsec:blackscholes-native-reduced",
        "./bin/parsecmgmt -a run -p blackscholes -i native -n 1")
canneal = ("2,3",
        "canneal",
        "anakli/parsec:canneal-native-reduced",
        "./bin/parsecmgmt -a run -p canneal -i native -n 2")
freqmine = ("2,3",
        "freqmine",
        "anakli/parsec:freqmine-native-reduced",
        "./bin/parsecmgmt -a run -p freqmine -i native -n 2")
ferret = ("2,3",
        "ferret",
        "anakli/parsec:ferret-native-reduced",
        "./bin/parsecmgmt -a run -p ferret -i native -n 2")


def create_container(c_tuple):
    cont = client.containers.create(cpuset_cpus=dedup[0],
            name=c_tuple[1],
            detach=True,
            auto_remove=False,
            image=c_tuple[2],
            command=c_tuple[3])
    cont.reload()
    return cont


def hard_remove_container(cont):
    try:
        cont.reload()
        if cont.status == "paused":
            cont.unpause()
        cont.reload()
        if cont.status == "running":
            cont.kill()
        cont.remove()
    except:
        print("You fucked up the 'hard_remove thingy'")


def remove_container(cont):
    if cont is None:
        return None
    try:
        cont.remove()
    except:
        hard_remove_container(cont)
    return None


def remove_if_done_container(cont):
    if cont is None:
        return None
    cont.reload()
    if cont.status == "exited":
        return remove_container(cont)
    else:
        raise NotImplementedError("IMPLEMENT ME???")


def pause_container(cont):
    if cont is None: return
    try:
        cont.reload()
        if cont.status in ["running", "restarting"]:
            cont.pause()
    except:
        print("something seems to have gone wrong while PAUSING the container (But dont care)")


def unpause_container(cont):
    if cont is None: return
    cont.reload()
    if cont.status == "paused":
        cont.unpause()


def main():
    # Queue for CPU1 (1 cores [1])
    queue1 = Queue(maxsize=6)
    container1 = None

    # Queue for CPU2 (2 cores [2,3])
    queue2 = Queue(maxsize=6)
    container2 = None

    queue1.put(fft)
    queue1.put(blackscholes)

    queue2.put(freqmine)
    queue2.put(ferret)

    # Discard first measurement, since it is always wrong.
    psutil.cpu_percent(interval=None, percpu=True)
    mc_pid, mc_ncpus = init_memcached_config()

    running = True
    load_level = NORMAL  # Initialize the load level to normal

    while running:
        cpu_utilizations = psutil.cpu_percent(interval=None, percpu=True)
        cpu_util_avg = cpu_utilizations[0]  \
                if mc_ncpus == 1 \
                else (cpu_utilizations[0] + cpu_utilizations[1]) / 2.0

        if load_level == NORMAL:
            if cpu_util_avg > 90.0:
                load_level = HIGH

                # Update MemCached
                mc_pid, mc_ncpus = set_memcached_cpu(mc_pid, 2)

                # Update containers
                if queue2.empty() and container2 is None:
                    container1.update(cpuset_cpus="2,3")
                    # container1.reload()
                else:
                    pause_container(container1)

        elif load_level == HIGH:
            if cpu_util_avg <= 60:
                # change to 1 core
                load_level = NORMAL

                # Update MemCached
                mc_pid, mc_ncpus = set_memcached_cpu(mc_pid, 1)

                # Update containers
                if container1 is not None:
                    unpause_container(container1)
                elif queue1.empty():
                    # maybe we would want to start a second job here.
                    container2.update(cpuset_cpus="1-3")

            elif cpu_util_avg >= 95.0:
                # stop all containers
                load_level = CRITICAL

                pause_container(container1)
                pause_container(container2)

        elif load_level == CRITICAL:
            if cpu_util_avg <= 90:
                # restart containers
                load_level = HIGH

                if container2 is None and queue2.empty():
                    unpause_container(container1)
                else:
                    unpause_container(container2)

        # Remove containers if they are done.
        container1 = remove_if_done_container(container1)
        container2 = remove_if_done_container(container2)

        # Start containers.
        if load_level != CRITICAL:
            if container2 is None and not queue2.empty():
                container2 = create_container(queue2.get())
                container2.start()
        if load_level == NORMAL:
            if container1 is None and not queue2.empty():
                container1 = create_container(queue1.get())
                container1.start()

        if queue1.empty() and queue2.empty and container1 is None and container2 is None:
            print("all other jobs have been completed")

        sleep(0.5)


if __name__ == "__main__":
    # execute only if run as a script
    main()
