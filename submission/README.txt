This submission folder contains our project report, the controller we have
written for part 4, the static scheduling policy we have written for part 3 and
the modified YAML files.

- src folder contains the script for part 3 (src/static_schedule.py) and the
  controller (src/controller_final/).

- memcache folder contains the modified YAML script for the memcache container
  in part 3. We changed the node selector field to make memcache run on the 2
  core VM. This pod should be created by the user prior to running the static
  scheduling policy.

- parsec-benchmarks/part3 folder contains the modified YAML files for the PARSEC
  jobs in part 3. We changed the node selector fields, arg fields and resource
  request/limits in the YAML files. You can find more information in the report.
  These jobs will be created by the static scheduling script.

Important note: this file hierarchy is important for the static scheduler to
work. If you want to change the locations of files inside the folders, then be
careful to ensure the location variable in static_schedule.py points to folder
location where PARSEC job YAML files are located.
