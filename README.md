# Cloud Computing Architecture Project

This repository contains code, results and reports for the Cloud Computing Architecture course project at ETH Zurich. The project explores how to schedule latency-sensitive and batch applications in a cloud cluster.  

## Files and Folders 

* `cloud_comp_project_parts1-4.pdf`: This file contains the project description and instructions for setting up the clusters required for the project.
* `interference`: This folder contains the YAML files used induce resource contention in the clusters.
* `memcache`: This folder contains the YAML files used to set up memcache pod for parts 1 & 3.
* `parsec-benchmarks`: This folder contains the YAML files used to set up PARSEC pods for parts 2 & 3.
* `project_yaml_files`: This folder contains the YAML files we used to start up the clusters used in parts 1-4.
* `reports`: This folder contains our reports for the project. You can find the detailed explanations of memcache and PARSEC application profiling in `report_part_1_2.pdf` file. You can find detailed explanation of the design of our static and dynamic scheduling policies, and their respective performances in the `report_part_3_4.pdf`.
* `results`: This folder contains the output logs of memcache and PARSEC executions for parts 1-4.
* `src`: This folder contains the implementations of our scheduling policies. `static_schedule.py` contains the static scheduling policy for part 3. `controller_final` folder contains the implementation of the dynamic scheduling policy and controller for part 4.
 
## Contributors 

* Julia Bazinska
* Floris Westermann
* Berke Egeli
