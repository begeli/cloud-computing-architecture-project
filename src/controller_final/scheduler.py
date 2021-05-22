import docker

NORMAL = "normal"
HIGH = "high"
CRITICAL = "critical"


class ContainerScheduler:
    def __init__(self, q0_conf, q1_conf, q2_conf, logger):
        self.__client = docker.from_env()
        self.hard_remove_everything()
        # 1 core
        self.__queue1 = [self.create_container(c_tuple) for c_tuple in q0_conf]
        # 2 core
        self.__queue2 = [self.create_container(c_tuple) for c_tuple in q1_conf]
        # 3 core
        self.__queue3 = [self.create_container(c_tuple) for c_tuple in q2_conf]

        self.__load_level = NORMAL  # Initialize the load level to normal
        self.__logger = logger
        # Initialize client object for docker.

        self.start_or_unpause_container(self.__queue3[0])
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
        print("switching to HIGH")
        self.__load_level = HIGH
        if self.__running == [0, 0, 1]:
            # If there are only jobs in q3 left, we don't want want to stop it.
            if not self.__queue1 and not self.__queue2:
                self.update_container(self.__queue3[0], "2,3")
                return

            self.pause_container(self.__queue3[0])
            if self.__queue2:
                self.start_or_unpause_container(self.__queue2[0])
                self.__running = [0, 1, 0]
            else:
                if self.__queue1:
                    self.start_or_unpause_container(self.__queue1[0])
                    self.__running = [1, 0, 0]
                if len(self.__queue1) >= 2:
                    self.start_or_unpause_container(self.__queue1[1])
                    self.__running = [2, 0, 0]

        elif self.__running == [1, 1, 0]:
            self.pause_container(self.__queue1[0])
            self.__running = [0, 1, 0]

        elif self.__running == [3, 0, 0]:
            self.pause_container(self.__queue1[2])
            self.__running = [2, 0, 0]

    def HIGH_to_NORMAL(self):
        print("switching to NORMAL")
        self.__load_level = NORMAL
        if self.__running == [0, 1, 0]:
            if self.__queue3:
                self.pause_container(self.__queue2[0])
                self.start_or_unpause_container(self.__queue3[0])
                self.__running = [0, 0, 1]
            elif self.__queue1:
                self.start_or_unpause_container(self.__queue1[0])
                self.__running = [1, 1, 0]
        elif self.__running == [2, 0, 0]:
            if self.__queue3:
                self.pause_container(self.__queue1[0])
                self.pause_container(self.__queue1[1])
                self.start_or_unpause_container(self.__queue3[0])
                self.__running = [0, 0, 1]
            if len(self.__queue1) >= 3:
                self.start_or_unpause_container(self.__queue1[2])
                self.__running = [3, 0, 0]

        # This is a special case when all other jobs are done.
        elif self.__running == [0, 0, 1]:
            self.update_container(self.__queue3[0], "1,2,3")

    def HIGH_to_CRITICAL(self):
        print("switching to CRITICAL")
        self.__load_level = CRITICAL
        # allow memcached to use all cpus.
        if self.__running == [0, 1, 0]:
            self.pause_container(self.__queue2[0])
        elif self.__running == [2, 0, 0]:
            self.pause_container(self.__queue1[0])
            self.pause_container(self.__queue1[1])
        elif self.__running == [1, 0, 0]:
            self.pause_container(self.__queue1[0])
        elif self.__running == [0, 0, 1]:
            self.pause_container(self.__queue3[0])
        self.__running = [0, 0, 0]

    def CRITICAL_to_HIGH(self):
        print("switching to HIGH")
        self.__load_level = HIGH
        if self.__queue2:
            self.unpause_container(self.__queue2[0])
            self.__running = [0, 1, 0]
        elif self.__queue1:
            self.unpause_container(self.__queue1[0])
            self.__running = [1, 0, 0]
            if len(self.__queue1) >= 2:
                self.unpause_container(self.__queue1[1])
                self.__running = [2, 0, 0]
        elif self.__queue3:
            self.unpause_container(self.__queue3[0])
            self.__running = [0, 0, 1]

    def REMOVE_EXITED_CONTAINERS(self):
        # Remove exited containers.
        pop_location = 0
        running = self.__running[0]
        for x in range(0, running):
            removed = self.remove_if_done_container(self.__queue1[pop_location])
            if removed:
                self.__running[0] -= 1
                self.__queue1.pop(pop_location)
            else:
                pop_location += 1

        if self.__running[1] == 1:
            removed = self.remove_if_done_container(self.__queue2[0])
            if removed:
                self.__queue2.pop(0)
                self.__running[1] = 0

        if self.__running[2] == 1:
            removed = self.remove_if_done_container(self.__queue3[0])
            if removed:
                self.__queue3.pop(0)
                self.__running[2] = 0

    def get_best_distribution(self, max):
        if max >= 4:
            if self.__queue3 and self.__queue1:
                return [3,1]
            if len(self.__queue2) >= 2:
                return [2,2]
            if self.__queue2 and len(self.__queue1) >= 2:
                return [2,1,1]
            if len(self.__queue1) >= 4:
                return [1,1,1,1]

        if max >= 3:
            if self.__queue3:
                return [3]
            if self.__queue2 and self.__queue1:
                return [2,1]
            if len(self.__queue1) >= 3:
                return [1,1,1]

        if max >= 2:
            if self.__queue2:
                return [2]
            if len(self.__queue1) >= 2:
                return [1,1]

        if max >= 1:
            if self.__queue1:
                return [1]

    def add(self, n_containers):
        for q in self.get_best_distribution(n_containers):
            if q == 3:
                self.start_or_unpause_container(self.__queue3[self.__running[2]-1])
                self.__running[2] += 1
            if q == 2:
                self.start_or_unpause_container(self.__queue2[self.__running[1]-1])
                self.__running[1] += 1
            if q == 1:
                self.start_or_unpause_container(self.__queue1[self.__running[0]-1])
                self.__running[0] += 1

    def remove(self, n_containers):
        if n_containers <= 0:
            return
        weight = 3
        queues = [self.__queue1, self.__queue2, self.__queue3]
        for n in reversed(self.__running):
            for i in reversed(range(0, self.__running[weight-1])):
                if n_containers > weight:
                    n_containers -= weight
                    self.__running[weight-1] -= 1
                    self.pause_container(queues[weight-1][i])



    def SCHEDULE_NEXT(self):
        if self.__load_level == NORMAL:
            if self.get_core_usage() == 0 and self.can_schedule_queue3():
                self.start_or_unpause_container(self.__queue3[self.__running[2]])
                self.__running[2] += 1

            if self.get_core_usage() <= 1 and self.can_schedule_queue2():
                self.start_or_unpause_container(self.__queue2[self.__running[1]])
                self.__running[1] += 1

            while self.get_core_usage() < 3 and self.can_schedule_queue1():
                self.start_or_unpause_container(self.__queue1[self.__running[0]])
                self.__running[0] += 1

        if self.__load_level == HIGH:
            if self.get_core_usage() == 0 and self.can_schedule_queue2():
                self.start_or_unpause_container(self.__queue2[self.__running[1]])
                self.__running[1] += 1

            while self.get_core_usage() < 2 and self.can_schedule_queue1():
                self.start_or_unpause_container(self.__queue1[self.__running[0]])
                self.__running[0] += 1

            # If we still didn't schedule anything, just schedule queue3.
            if self.get_core_usage() == 0 and self.__queue3:
                self.start_or_unpause_container(self.__queue3[0])
                self.update_container(self.__queue3[0], "2,3")
                self.__running = [0, 0, 1]

    def DONE(self):
        return self.__running == [0, 0, 0] and not self.__queue1 and not self.__queue2 and not self.__queue3

    def print_queues(self):
        print("queue1", [c.name for c in self.__queue1], end="  ")
        print("queue2", [c.name for c in self.__queue2], end="  ")
        print("queue3", [c.name for c in self.__queue3], end=50 * " " + "\r")

    # Container management helpers.

    def create_container(self, c_tuple):
        cont = self.__client.containers.create(cpuset_cpus=c_tuple[0],
                                               name=c_tuple[1],
                                               detach=True,
                                               auto_remove=False,
                                               image=c_tuple[2],
                                               command=c_tuple[3])
        cont.reload()
        return cont

    def hard_remove_container(self, cont):
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

    def remove_container(self, cont):
        if cont is None:
            # print("Inside remove container. Returning none.")
            return None
        try:
            # print(f"Removed {cont.name}.")
            cont.remove()
        except:
            self.hard_remove_container(cont)
        return None

    def remove_if_done_container(self, cont):
        if cont is None:
            # print("Inside remove if done, returning none.")
            return False
        cont.reload()
        if cont.status == "exited":
            # print(f"Removing {cont.name} because it is done.")
            self.__logger.log_container_event(cont.name, 'FINISH')
            self.remove_container(cont)
            return True

        return False
        # else:
        #    raise NotImplementedError("IMPLEMENT ME???")

    def pause_container(self, cont):
        if cont is None:
            return
        try:
            cont.reload()
            if cont.status in ["running", "restarting"]:
                self.__logger.log_container_event(cont.name, 'PAUSE')
                cont.pause()
        except:
            print("something seems to have gone wrong while PAUSING the container (But dont care)")

    def unpause_container(self, cont):
        if cont is None:
            return
        cont.reload()
        if cont.status == "paused":
            self.__logger.log_container_event(cont.name, 'UNPAUSE')
            cont.unpause()

    def start_or_unpause_container(self, cont):
        if cont is None:
            return
        cont.reload()
        if cont.status == "paused":
            self.__logger.log_container_event(cont.name, 'UNPAUSE')
            cont.unpause()
            print("unpause " + cont.name)
        elif cont.status == "created":
            self.__logger.log_container_event(cont.name, 'START')
            print("start " + cont.name)
            cont.start()
        else:
            print("start_or_unpause didn't do anything.")
            return

    def update_container(self, cont, cpu_set):
        if cont is None:
            return
        if cont.status == "exited":
            return

        cont.update(cpuset_cpus=cpu_set)

    def hard_remove_everything(self):
        try:
            self.hard_remove_container(self.__client.containers.get("dedup"))
        except:
            print("Tried to remove Dedup, but didn't exist.")
        try:
            self.hard_remove_container(self.__client.containers.get("splash2x-fft"))
        except:
            print("Tried to remove FFT, but didn't exist.")
        try:
            self.hard_remove_container(self.__client.containers.get("blackscholes"))
        except:
            print("Tried to remove Blackscholes, but didn't exist.")
        try:
            self.hard_remove_container(self.__client.containers.get("canneal"))
        except:
            print("Tried to remove Canneal, but didn't exist.")
        try:
            self.hard_remove_container(self.__client.containers.get("freqmine"))
        except:
            print("Tried to remove Freqmine, but didn't exist.")
        try:
            self.hard_remove_container(self.__client.containers.get("ferret"))
        except:
            print("Tried to remove Ferret, but didn't exist.")

