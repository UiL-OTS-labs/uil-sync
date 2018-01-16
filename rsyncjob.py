#!/usr/bin/env python3

import subprocess
import sys
import selectors
import threading 
import queue
from time import sleep

class ThreadedRSync(threading.Thread):
    '''Runs the rsync command in a separate thread'''

    def __init__(self, source, target, *args, **kwargs):
        '''Prepares the thread to run.'''
        super().__init__(*args, **kwargs)
        self.source     = source
        self.target     = target
        self.queue      = queue.Queue()
        self.finished   = threading.Event()
        self.finished.clear()
        self.result     = -1

    def run(self):
        '''Runs the actual rsync program.'''
        job = RSyncJob(self.source, self.target, self.queue)
        job.execute(self.queue)
        self.result = job.status()
        self.finished.set()

class RSyncJob:
    '''A single job that executes a rsync commando.'''
    CMD         = "rsync"
    ARCHIVE     = "-a"

    FINISHED    = 0
    STDOUT      = 1
    STDERR      = 2

    def __init__(self, source, target, queue):
        self.source, self.target = source, target
        self.queue = queue
        self.process = None
        self.exit_status = -1

    def execute(self, queue, recursive=True, verbose=True, progress=False):
        '''executes a rsync commando and read from stdout and -err.'''

        args = [self.CMD, self.ARCHIVE]
        if recursive:
            args.append("-r")
        if verbose:
            args.append("-v")
        if progress:
            args.append("--info=progress2")
        args += [self.source, self.target]

        selector = selectors.DefaultSelector()
        with subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True) as self.process:

            selector.register(
                self.process.stdout,
                selectors.EVENT_READ,
                self.rdstdout
                )
            selector.register(
                self.process.stderr,
                selectors.EVENT_READ,
                self.rdstderr
                )

            while self.process.poll() == None:
                events = selector.select()
                for key, mask in events:
                    callback = key.data
                    callback(key.fileobj)
        
        self.exitstatus = self.process.poll()

    def rdstdout(self, fileobj):
        msg = fileobj.readline()
        self.queue.put((self.STDOUT, msg))
    
    def rdstderr(self, fileobj):
        msg = fileobj.readline()
        self.queue.put((self.STDERR, msg))

    def status(self):
        return self.exitstatus


if __name__ ==  "__main__":
    import queue
    q = queue.Queue()
    proc = RSyncJob('/home/duijn119/github/utils/uil-sync', '/tmp/rsync-test', q)
    proc.execute(queue)
    while not q.empty():
        msg = q.get()
        print(msg[0], msg[1], end="")
    print("exit status = ", proc.status())
