#!/usr/bin/env python

import Queue
import threading
import urllib2
import time

from os import listdir
from os.path import isfile, join

def scan_loop():
	targetDir = "./target"
	while(1):
		files = [ f for f in listdir(targetDir) if isfile(join(targetDir,f)) ]
		for f in files:
			print f
		time.sleep(1)


def print_loop(): 
	while(1):
		print "loopin'"
		time.sleep(1)

if __name__ == '__main__':
	print "startin'"
	scan_thread = threading.Thread(target=scan_loop, args = ())
	scan_thread.daemon = True
	scan_thread.start()
	scan_thread = threading.Thread(target=print_loop, args = ())
	scan_thread.daemon = True
	scan_thread.start()
	print "runnin'"
	while(1):
		time.sleep(1)
	print "quittin'"

