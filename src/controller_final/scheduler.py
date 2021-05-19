import docker

NORMAL = "normal"
HIGH = "high"
CRITICAL = "critical"


class ContainerScheduler:
    def __init__(self, q0_conf, q1_conf, q2_conf):
        hard_remove_everything()
        # 1 core
        self.__queue1 = [create_container(c_tuple) for c_tuple in q0_conf]
        # 2 core
        self.__queue2 = [create_container(c_tuple) for c_tuple in q1_conf]
        # 3 core
        self.__queue3 = [create_container(c_tuple) for c_tuple in q2_conf]

        self.__load_level = NORMAL  # Initialize the load level to normal

        self.__queue3[0].start()
        print("run " + self.__queue3[0].name)
        self.__running = [0, 0, 1]

    def get_load_level(self):
        return self.__load_level

    def get_core_usage(self):
        return self.__running[0] + 2 * self.__running[1] + 3 * self.__running[2]

    def can_schedule_queue1(self):
        return len(self.__queue1) > self.__running[0]

    def can_schedule_queue2(self):
        return len(self.__queue2) > self.__running[1]

    def can_schedule_queue3(self):
        return len(self.__queue3) > self.__running[2]

    def NORMAL_to_HIGH(self):
        self.__load_level = HIGH
        if self.__running == [0, 0, 1]:
            pause_container(self.__queue3[0])
            if self.__queue2:
                start_or_unpause_container(self.__queue2[0])
                self.__running = [0, 1, 0]
            else:
                if self.__queue1:
                    start_or_unpause_container(self.__queue1[0])
                    self.__running = [1, 0, 0]
                if len(self.__queue1) >= 2:
                    start_or_unpause_container(self.__queue1[1])
                    self.__running = [2, 0, 0]
        elif self.__running == [1, 1, 0]:
            pause_container(self.__queue1[0])
            self.__running = [0, 1, 0]

        print("switched to HIGH")

    def HIGH_to_NORMAL(self):
        self.__load_level = NORMAL
        if self.__running == [0, 1, 0]:
            if self.__queue3:
                pause_container(self.__queue2[0])
                start_or_unpause_container(self.__queue3[0])
                self.__running = [0, 0, 1]
            elif self.__queue1:
                start_or_unpause_container(self.__queue1[0])
                self.__running = [1, 1, 0]
        elif self.__running == [2, 0, 0]:
            if self.__queue3:
                pause_container(self.__queue1[0])
                pause_container(self.__queue1[1])
                start_or_unpause_container(self.__queue3[0])
                self.__running = [0, 0, 1]
            if len(self.__queue1) >= 3:
                start_or_unpause_container(self.__queue1[2])
                self.__running = [3, 0, 0]

        print("switched to NORMAL")

    def HIGH_to_CRITICAL(self):
        self.__load_level = CRITICAL
        # allow memcached to use all cpus.
        if self.__running == [0, 1, 0]:
            pause_container(self.__queue2[0])
        elif self.__running == [2, 0, 0]:
            pause_container(self.__queue1[0])
            pause_container(self.__queue1[1])
        elif self.__running == [1, 0, 0]:
            pause_container(self.__queue1[0])
        self.__running = [0, 0, 0]

        print("switched to CRITICAL")

    def CRITICAL_to_HIGH(self):
        self.__load_level = HIGH
        if self.__queue2:
            unpause_container(self.__queue2[0])
            self.__running = [0, 1, 0]
        elif self.__queue1:
            unpause_container(self.__queue1[0])
            self.__running = [1, 0, 0]
            if len(self.__queue1) >= 2:
                unpause_container(self.__queue1[1])
                self.__running = [2, 0, 0]

        print("switched to HIGH")

    def REMOVE_EXITED_CONTAINERS(self):
        # Remove exited containers.
        pop_location = 0
        running = self.__running[0]
        for x in range(0, running):
            removed = remove_if_done_container(self.__queue1[pop_location])
            if removed:
                self.__running[0] -= 1
                self.__queue1.pop(pop_location)
            else:
                pop_location += 1

        if self.__running[1] == 1:
            removed = remove_if_done_container(self.__queue2[0])
            if removed:
                self.__queue2.pop(0)
                self.__running[1] = 0

        if self.__running[2] == 1:
            removed = remove_if_done_container(self.__queue3[0])
            if removed:
                self.__queue3.pop(0)
                self.__running[2] = 0

    def SCHEDULE_NEXT(self):
        if self.__load_level == NORMAL:
            if self.get_core_usage() == 0 and self.can_schedule_queue3():
                start_or_unpause_container(self.__queue3[self.__running[2]])
                self.__running[2] += 1

            if self.get_core_usage() <= 1 and self.can_schedule_queue2():
                start_or_unpause_container(self.__queue2[self.__running[1]])
                self.__running[1] += 1

            while self.get_core_usage() < 3 and self.can_schedule_queue1():
                start_or_unpause_container(self.__queue1[self.__running[0]])
                self.__running[0] += 1

        if self.__load_level == HIGH:
            if self.get_core_usage() == 0 and self.can_schedule_queue2():
                start_or_unpause_container(self.__queue2[self.__running[1]])
                self.__running[1] += 1

            while self.get_core_usage() < 2 and self.can_schedule_queue1():
                start_or_unpause_container(self.__queue1[self.__running[0]])
                self.__running[0] += 1

    def DONE(self):
        return self.__running == [0,0,0] and not self.__queue1 and not self.__queue2 and not self.__queue3

    def print_queues(self):
        print("queue1", [c.name for c in self.__queue1], end="  ")
        print("queue2", [c.name for c in self.__queue2], end="  ")
        print("queue3", [c.name for c in self.__queue3], end=50*" "+"\r")


# Docker helper functions.

# Initialize client object for docker.
client = docker.from_env()


def create_container(c_tuple):
    cont = client.containers.create(cpuset_cpus=c_tuple[0],
                                    name=c_tuple[1],
                                    detach=True,
                                    auto_remove=False,
                                    image=c_tuple[2],
                                    command=c_tuple[3])
    cont.reload()
    return cont


def hard_remove_container(cont):
    if cont is None: return
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
        # print("Inside remove container. Returning none.")
        return None
    try:
        # print(f"Removed {cont.name}.")
        cont.remove()
    except:
        hard_remove_container(cont)
    return None


def remove_if_done_container(cont):
    if cont is None:
        # print("Inside remove if done, returning none.")
        return False
    cont.reload()
    if cont.status == "exited":
        # print(f"Removing {cont.name} because it is done.")
        remove_container(cont)
        return True

    return False
    # else:
    #    raise NotImplementedError("IMPLEMENT ME???")


def pause_container(cont):
    if cont is None:
        return
    try:
        cont.reload()
        if cont.status in ["running", "restarting"]:
            cont.pause()
    except:
        print("something seems to have gone wrong while PAUSING the container (But dont care)")


def unpause_container(cont):
    if cont is None:
        return
    cont.reload()
    if cont.status == "paused":
        cont.unpause()


def start_or_unpause_container(cont):
    if cont is None:
        return
    cont.reload()
    if cont.status == "paused":
        cont.unpause()
    elif cont.status == "created":
        cont.start()
    else:
        print("start_or_unpause didn't do anything.")
        return
    print("run " + cont.name)


def update_container(cont, cpu_set):
    if cont is None:
        return
    if cont.status == "exited":
        return

    cont.update(cpuset_cpus=cpu_set)


def hard_remove_everything():
    try:
        hard_remove_container(client.containers.get("dedup"))
    except:
        print("Tried to remove Dedup, but didn't exist.")
    try:
        hard_remove_container(client.containers.get("splash2x-fft"))
    except:
        print("Tried to remove FFT, but didn't exist.")
    try:
        hard_remove_container(client.containers.get("blackscholes"))
    except:
        print("Tried to remove Blackscholes, but didn't exist.")
    try:
        hard_remove_container(client.containers.get("canneal"))
    except:
        print("Tried to remove Canneal, but didn't exist.")
    try:
        hard_remove_container(client.containers.get("freqmine"))
    except:
        print("Tried to remove Freqmine, but didn't exist.")
    try:
        hard_remove_container(client.containers.get("ferret"))
    except:
        print("Tried to remove Ferret, but didn't exist.")
