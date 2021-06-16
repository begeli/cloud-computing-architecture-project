###################### Instructions for running the static scheduler (Part 3) #####################

- Prior to running the scheduler, the user should create the clusters as specified in the project description. 

- User should manually create the memcache pod by running the YAML file in the memcache folder.

- Then user should run the python script static_schedule.py file inside this folder. (python3 static_schedule.py should work just fine.)

- Important note: static_schedule.py hardcodes the path to the YAML files for PARSEC jobs. The user should use the default folder hierarchy or they should ensure the location variable in the script points to the folder that contains the relevant PARSEC jobs.

- The script will output the scheduled pods and then it will exit. User should manually check if all the pods finished execution by using the get_time.py script of the command line. 

- NOTE: get_time.py is provided by the teaching team and it is unmodified.
##################### Instructions for running the dynamic controller (Part 4) #####################

- User should create the cluster as specified in the project description.

- User should setup memcache and mc-perf in the respective machines as described in the project description.

- User should set the number of threads used by memcache to 2.

- When the cluster is up and running they should do the following: 

1) Install pip3 in the memcache server.
2) Install psutil and docker with pip3.
3) Activate docker inside the VM by following steps 2-4 in the following website: https://docs.docker.com/engine/install/linux-postinstall/
4) Pull the docker images by running the following command: 

	docker pull anakli/parsec:dedup-native-reduced && 
	docker pull anakli/parsec:splash2x-fft-native-reduced &&
	docker pull anakli/parsec:blackscholes-native-reduced && 
	docker pull anakli/parsec:canneal-native-reduced && 
	docker pull anakli/parsec:freqmine-native-reduced && 
	docker pull anakli/parsec:ferret-native-reduced

5) Copy the files in the controller_final folder into the memcache server. It is important that logger.py and scheduler.py files are named the same. 

6) User can run the controller by the following command:

	python3 controller_final.py --log_path <Name of the logging File (REQUIRED)>
	
	This command will start scheduling the PARSEC jobs, so, it is important to start running mc-perf right after this command executes.


- NOTE: cpu_ps_util.py is a small script we used to get the cpu utilization numbers for the first 2 questions in part 4.
