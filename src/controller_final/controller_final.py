import argparse
import functools
import subprocess
from time import sleep

import psutil
import scheduler
import signal
import sys
from logger import Logger

parser = argparse.ArgumentParser()
parser.add_argument("--log_path", dest='log_path')
args = parser.parse_args()


def handle_signal(sched, sig, frame):
    print("aborting...")
    sched.hard_remove_everything()
    sys.exit(0)


# Returns tuple with pid of memcached and number of cpus (=1)
def init_memcached_config(logger):
    process_name = "memcache"
    pid = None

    # Find the pid of memcache
    for proc in psutil.process_iter():
        if process_name in proc.name():
            pid = proc.pid
            break

    # Set the cpu affinity of memcached to CPU 0
    return set_memcached_cpu(pid, 4, logger)


def set_memcached_cpu(pid, no_of_cpus, logger):
    cpu_affinity = ",".join(map(str, range(0, no_of_cpus)))
    print(f'Setting Memcached CPU affinity to {cpu_affinity}')
    command = f'sudo taskset -a -cp {cpu_affinity} {pid}'
    logger.log_memchached_state(no_of_cpus)
    subprocess.run(command.split(" "))
    return pid, no_of_cpus


dedup = ("0,1,2,3",
         "dedup",
         "anakli/parsec:dedup-native-reduced",
         "./bin/parsecmgmt -a run -p dedup -i native -n 1")
fft = ("0,1,2,3",
       "splash2x-fft",
       "anakli/parsec:splash2x-fft-native-reduced",
       "./bin/parsecmgmt -a run -p splash2x.fft -i native -n 1")
blackscholes = ("0,1,2,3",
                "blackscholes",
                "anakli/parsec:blackscholes-native-reduced",
                "./bin/parsecmgmt -a run -p blackscholes -i native -n 2")
canneal = ("0,1,2,3",
           "canneal",
           "anakli/parsec:canneal-native-reduced",
           "./bin/parsecmgmt -a run -p canneal -i native -n 2")
freqmine = ("0,1,2,3",
            "freqmine",
            "anakli/parsec:freqmine-native-reduced",
            "./bin/parsecmgmt -a run -p freqmine -i native -n 2")
ferret = ("0,1,2,3",
          "ferret",
          "anakli/parsec:ferret-native-reduced",
          "./bin/parsecmgmt -a run -p ferret -i native -n 3")


def main():
    if not args.log_path or args.log_path is None:
        raise ValueError("please provide --log_path PATH_TO_LOG_FILE.")

    q1_conf = [dedup, fft]
    q2_conf = [canneal, freqmine, blackscholes]
    q3_conf = [ferret]

    logger = Logger(args.log_path)
    sched = scheduler.ContainerScheduler(q1_conf, q2_conf, q3_conf, logger)
    signal.signal(signal.SIGINT, functools.partial(handle_signal, sched))

    # Discard first measurement, since it is always wrong.
    psutil.cpu_percent(interval=None, percpu=True)
    mc_pid, mc_ncpus = init_memcached_config(logger)

    mc_proc = psutil.Process(mc_pid)

    i = 0
    while True:
        if i == 0:
            sched.print_queues()
            print("running from queues", sched.get_running())
        i = (i + 1) % 20

        mc_utilization = mc_proc.cpu_percent()
        cpu_utilizations = psutil.cpu_percent(interval=None, percpu=True)
        cpu_util_total = sum(cpu_utilizations)

        if cpu_util_total < 100 and sched.get_core_usage() <= 1:
            sched.add(4)

        elif cpu_util_total < 200 and sched.get_core_usage() <= 2:
            sched.add(3)

        elif cpu_util_total < 300 and sched.get_core_usage() <= 3:
            sched.add(2)
        elif cpu_util_total < 350 and sched.get_core_usage() <= 4:
            sched.add(1)

        elif cpu_util_total > 380:
            if mc_utilization > 90:
                # reduce to 2 cores
                sched.remove(sched.get_core_usage() - 3)
            if mc_utilization > 180:
                # reduce to 1 core
                sched.remove(sched.get_core_usage() - 2)

        # Remove containers if they are done.
        sched.REMOVE_EXITED_CONTAINERS()

        # Start containers.
        # sched.SCHEDULE_NEXT()

        if sched.DONE():
            print("all other jobs have been completed")
            set_memcached_cpu(mc_pid, 4, logger)
            logger.log_end()
            break

        sleep(0.25)


if __name__ == "__main__":
    # execute only if run as a script
    main()
