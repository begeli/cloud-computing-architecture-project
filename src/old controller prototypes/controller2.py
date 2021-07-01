import docker
from time import sleep
from queue import Queue

'''
A code snippet that creates 6 containers and runs parsec jobs in a specific order.

To run this code, you might have to configure your docker. I don't know how to explain it but if 
you have executing the code right away because you get an error related to Docker look at the following link:
https://docs.docker.com/engine/install/linux-postinstall/

This code doesn't dynamically update the resources of containers or un/pause them.
It should run for around 19 minutes without memcached, which means it is fairly slow right now.
To give you an idea, it would take around the same time if we ran all the jobs in sequence with 2 threads 
and 2-3 CPUs.

TODO: 
1) Combine this code with controller.py in the repo. (It won't be as simple as copy-paste. :()
2) Ensure that cpu allocations dynamically change based on the following factors:
    Is one of the queues empty? If yes, give its resources to other queue.
    Is memcache under heavy load? If yes, release one of 1st cpu or pause first queue.
'''

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

# Fill the second queue.
queue2.put(ferret)
queue2.put(freqmine)

print("Creating containers!")

print("Running dedup.")
container1 = client.containers.run(cpuset_cpus=dedup[0], name=dedup[1], detach=True, auto_remove=False, image=dedup[2], command=dedup[3])
print("Running canneal.")
container2 = client.containers.run(cpuset_cpus=canneal[0], name=canneal[1], detach=True, auto_remove=False, image=canneal[2], command=canneal[3])

container1.reload()
container2.reload()
while (not queue1.empty() or not queue2.empty()) or (container1.status != "exited" or container2.status != "exited"):
    sleep(1)
    # If the previous job stopped and queue isn't empty, start the next job in the queue
    if ((not queue1.empty()) and container1.status == "exited"):
        # Delete the container that stopped its execution.
        print(f"Removing {container1.name}")
        client.containers.get(container1.name).remove()

	# Start the next job in the queue.
        job = queue1.get()
        print(f"Running {job[1]}.")
        container1 = client.containers.run(cpuset_cpus=job[0], name=job[1], detach=True, auto_remove=False, image=job[2], command=job[3])

    # If the previous job stopped and queue isn't empty, start the next job in the queue
    if ((not queue2.empty()) and container2.status == "exited"):
        # Delete the container that stopped its execution.
        print(f"Removing {container2.name}")
        client.containers.get(container2.name).remove()

        # Start the next job in the queue.
        job = queue2.get()
        print(f"Running {job[1]}.")
        container2 = client.containers.run(cpuset_cpus=job[0], name=job[1], detach=True, auto_remove=False, image=job[2], command=job[3])

    container1.reload()
    container2.reload()

# Delete the last containers.
print(f"Removing {container1.name}")
client.containers.get(container1.name).remove()
print(f"Removing {container2.name}")
client.containers.get(container2.name).remove()

print("All jobs finished running! Hurray!")
