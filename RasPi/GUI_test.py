#!/usr/bin/env python

'''
Created on 20.4.2015

@author: Juha Kallas
'''

import reader

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import random
import threading
import time

class ItemReminderGUI:
    
    #global sharedList
    
    def __init__(self):
        UI_filename = "ItemReminderGUI.glade"
        self.builder = gtk.Builder()
        self.builder.add_from_file(UI_filename)
        self.builder.connect_signals(self)
        
        self.window2 = self.builder.get_object("TestWindow1")
        self.window2.fullscreen()
        
        'First tag slot'
        self.item1box = self.builder.get_object("eventbox1")
        self.item1box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(0xFFFF,0x0000,0x0000)) #Red
        self.labelKeys = self.builder.get_object("labelKeys")
        self.labelKeys.set_markup('<span size="24000" foreground="#FFFFFF">Keys</span>')
        
        'Second tag slot'
        self.item2box = self.builder.get_object("eventbox2")
        self.item2box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(0xFFFF,0xFFFF,0x0000)) #Yellow
        self.labelWallet = self.builder.get_object("labelWallet")
        self.labelWallet.set_markup('<span size="24000">Wallet</span>')
        
        'Third tag slot'
        self.item3box = self.builder.get_object("eventbox3")
        self.item3box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(0x0000,0xFFFF,0x0000)) #Green
        self.labelPhone = self.builder.get_object("labelPhone")
        self.labelPhone.set_markup('<span size="24000">Mobile Phone</span>')

        'These used for the state of the text'
        self.x = 0
        self.y = 0
        self.z = 0
        self.g = 0
        
    def on_MainWindow_destroy(self, widget, data=None):
        gtk.main_quit()        
        
    def start_t(self):
        self.g = gobject.timeout_add(1000, self.counter)    
     
    def counter(self):
        
        #self.x = random.randint(0,2)
        #self.y = random.randint(0,2)
        #self.z = random.randint(0,2)
        
        self.x = sharedList[0]
        self.y = sharedList[1]
        self.z = sharedList[2]
        
        if self.x == 0:
            self.labelKeys.set_markup('<span size="24000" foreground="#FFFFFF">Keys</span>')
            self.item1box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(0xCFFF,0x0000,0x0000)) #Red
        if self.x == 1:
            self.labelKeys.set_markup('<span size="24000" foreground="#000000">Keys</span>')
            self.item1box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(0xFFFF,0x8FFF,0x0000)) #Yellow
        if self.x == 2:
            self.labelKeys.set_markup('<span size="24000" foreground="#000000">Keys</span>')
            self.item1box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(0x0000,0xDFFF,0x0000)) #Green
        
        if self.y == 0:
            self.labelWallet.set_markup('<span size="24000" foreground="#FFFFFF">Wallet</span>')
            self.item2box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(0xCFFF,0x0000,0x0000)) #Red
        if self.y == 1:
            self.labelWallet.set_markup('<span size="24000" foreground="#000000">Wallet</span>')
            self.item2box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(0xFFFF,0x8FFF,0x0000)) #Yellow
        if self.y == 2:
            self.labelWallet.set_markup('<span size="24000" foreground="#000000">Wallet</span>')
            self.item2box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(0x0000,0xDFFF,0x0000)) #Green
            
        if self.z == 0:
            self.labelPhone.set_markup('<span size="24000" foreground="#FFFFFF">Mobile phone</span>')
            self.item3box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(0xCFFF,0x0000,0x0000)) #Red
        if self.z == 1:
            self.labelPhone.set_markup('<span size="24000" foreground="#000000">Mobile phone</span>')
            self.item3box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(0xFFFF,0x8FFF,0x0000)) #Yellow
        if self.z == 2:
            self.labelPhone.set_markup('<span size="24000" foreground="#000000">Mobile phone</span>')
            self.item3box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(0x0000,0xDFFF,0x0000)) #Green
        
        return True
            
if __name__ == "__main__":
    
    print "startin'"
    sharedList = [0,0,0]
    scan_thread = threading.Thread(target=reader.scan_loop, args = [sharedList])
    scan_thread.daemon = True
    scan_thread.start()
    
    print_thread = threading.Thread(target=reader.print_loop, args = [sharedList])
    print_thread.daemon = True
    print_thread.start()
    
    gtk.gdk.threads_init()
    ItemReminder = ItemReminderGUI()
    ItemReminder.start_t()
     
    print "runnin'"
    while(1):
        time.sleep(0.01)
        gtk.threads_enter()
        gtk.main()
        gtk.threads_leave()
    print "quittin'"
