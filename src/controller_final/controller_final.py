import subprocess
from time import sleep

import psutil
import scheduler


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
    cpu_affinity = ",".join(map(str, range(0, no_of_cpus)))
    print(f'Setting Memcached CPU affinity to {cpu_affinity}')
    command = f'sudo taskset -a -cp {cpu_affinity} {pid}'
    subprocess.run(command.split(" "))
    return pid, no_of_cpus


dedup = ("1,2,3",
         "dedup",
         "anakli/parsec:dedup-native-reduced",
         "./bin/parsecmgmt -a run -p dedup -i native -n 1")
fft = ("1,2,3",
       "splash2x-fft",
       "anakli/parsec:splash2x-fft-native-reduced",
       "./bin/parsecmgmt -a run -p splash2x.fft -i native -n 1")
blackscholes = ("1,2,3",
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
ferret = ("1,2,3",
          "ferret",
          "anakli/parsec:ferret-native-reduced",
          "./bin/parsecmgmt -a run -p ferret -i native -n 3")



def main():

    q1_conf = [dedup, fft, blackscholes]
    q2_conf = [canneal, freqmine]
    q3_conf = [ferret]

    sched = scheduler.ContainerScheduler(q1_conf, q2_conf, q3_conf)

    # Discard first measurement, since it is always wrong.
    psutil.cpu_percent(interval=None, percpu=True)

    mc_pid, mc_ncpus = init_memcached_config()
    i = 0
    while True:
        if i == 0:
            sched.print_queues()
        i= (i + 1)%20

        cpu_utilizations = psutil.cpu_percent(interval=None, percpu=True)
        cpu_util_avg = (cpu_utilizations[0] + cpu_utilizations[1]) / 2.0
        cpu_util_one = cpu_utilizations[0]

        if sched.get_load_level() == scheduler.NORMAL:
            if cpu_util_one > 90.0:
                mc_pid, mc_ncpus = set_memcached_cpu(mc_pid, 2)
                sched.NORMAL_to_HIGH()
        elif sched.get_load_level() == scheduler.HIGH:
            if cpu_util_avg <= 60:
                # change to 1 core
                mc_pid, mc_ncpus = set_memcached_cpu(mc_pid, 1)
                sched.HIGH_to_NORMAL()
            elif cpu_util_avg >= 95.0:
                # stop all containers
                mc_pid, mc_ncpus = set_memcached_cpu(mc_pid, 4)
                sched.HIGH_to_CRITICAL()
        elif sched.get_load_level() == scheduler.CRITICAL:
            if cpu_util_avg <= 90:
                mc_pid, mc_ncpus = set_memcached_cpu(mc_pid, 2)
                sched.CRITICAL_to_HIGH()

        # Remove containers if they are done.
        sched.REMOVE_EXITED_CONTAINERS()

        # Start containers.
        sched.SCHEDULE_NEXT()

        if sched.DONE():
            print("all other jobs have been completed")
            set_memcached_cpu(mc_pid, 4)
            break

        sleep(0.25)


if __name__ == "__main__":
    # execute only if run as a script
    main()
