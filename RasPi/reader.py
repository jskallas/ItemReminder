#!/usr/bin/env python

import Queue
import threading
import urllib2
import time
import scanner

from os import listdir
from os.path import isfile, join

def scan_loop(sharedList):
	print "Scan starting"
	scanner.scan(sharedList)

		


def print_loop(sharedList): 
	while(1):
		for i in range (0,3):
			print str(i+1) + ": " + str(sharedList[i])
		time.sleep(1)

if __name__ == '__main__':
	print "startin'"
	sharedList = [0,0,0]
	scan_thread = threading.Thread(target=scan_loop, args = [sharedList])
	scan_thread.daemon = True
	scan_thread.start()
	scan_thread = threading.Thread(target=print_loop, args = [sharedList])
	scan_thread.daemon = True
	scan_thread.start()
	print "runnin'"
	while(1):
		time.sleep(1)
	print "quittin'"

