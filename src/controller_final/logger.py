import time


class Logger:
    def __init__(self, log_path):
        self.log_file = open(log_path, 'w', buffering=1)
        self.log_file.write('timestamp, process name, event\n')
        timestamp = time.time()
        entry = f'{timestamp}, controller, START\n'
        self.log_file.write(entry)

    def log_container_event(self, container_name, event):
        assert event in ['UNPAUSE', 'PAUSE', 'START', 'FINISH']
        timestamp = time.time()
        entry = f'{timestamp}, {container_name}, {event}\n'
        self.log_file.write(entry)

    def log_memchached_state(self, ncpus):
        timestamp = time.time()
        entry = f'{timestamp}, memchached, {ncpus}\n'
        self.log_file.write(entry)

    def log_end(self):
        timestamp = time.time()
        entry = f'{timestamp}, controller, FINISH\n'
        self.log_file.write(entry)