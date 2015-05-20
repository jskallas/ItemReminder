"""Aalto University student project, modified from Jeff Rowbergs BLED112_SCANNER.
Original license below.


 Barebones BGAPI scanner script for Bluegiga BLE modules

This script is designed to be used with a BGAPI-enabled Bluetooth Smart device
from Bluegiga, probably a BLED112 but anything that is connected to a serial
port (real or virtual) and can "speak" the BGAPI protocol. It is tuned for
usable defaults when used on a Raspberry Pi, but can easily be used on other
platforms, including Windows or OS X.

Note that the command functions do *not* incorporate the extra preceding length
byte required when using "packet" mode (only available on USART peripheral ports
on the BLE112/BLE113 module, not applicable to the BLED112). It is built so you
can simply plug in a BLED112 and go, but other kinds of usage may require small
modifications.

Changelog:
    2013-04-07 - Fixed 128-bit UUID filters
               - Added more verbose output on startup
               - Added "friendly mode" output argument
               - Added "quiet mode" output argument
               - Improved comments in code
    2013-03-30 - Initial release



__author__ = "Jeff Rowberg"
__license__ = "MIT"
__version__ = "2013-04-07"
__email__ = "jeff@rowberg.net"

"""

"""
Changelog:
    2015-05-20: Hardcoded support for demo tags

"""

__author__ = "Otso Jousimaa"
__version__ = "2015-05-20"
__email__ = "otso.jousimaa@aalto.fi"

import sys, optparse, serial, struct, time, datetime, re, signal
#import RPi.GPIO as GPIO

options = []
filter_uuid = []
filter_mac = [[0x00,0x07,0x80, 0x05, 0x96, 0xF2], [0x00, 0x07, 0x80, 0x05, 0x96, 0xE8], [0x00, 0x07, 0x80, 0x05, 0x96, 0xF3],[0x00, 0x07, 0x80, 0x7F, 0x51, 0x4C]]
filter_rssi = 0

    
def scan(sharedList):
    global options, filter_uuid, filter_mac, filter_rssi
    print "Scan started"

    class MyParser(optparse.OptionParser):
        def format_epilog(self, formatter=None):
            return self.epilog

        def format_option_help(self, formatter=None):
            formatter = IndentedHelpFormatterWithNL()
            if formatter is None:
                formatter = self.formatter
            formatter.store_option_strings(self)
            result = []
            result.append(formatter.format_heading(optparse._("Options")))
            formatter.indent()
            if self.option_list:
                result.append(optparse.OptionContainer.format_option_help(self, formatter))
                result.append("\n")
            for group in self.option_groups:
                result.append(group.format_help(formatter))
                result.append("\n")
            formatter.dedent()
            # Drop the last "\n", or the header if no options or option groups:
            return "".join(result[:-1])

    # process script arguments
    p = MyParser(description='Bluetooth Smart Scanner for Bluegiga BLED112', epilog=
"""
Takes sharedList as a parameters, writes '1' if tag in index is seen, '0' if not
"""
    )

    # set all defaults for options
    p.set_defaults(port="/dev/ttyACM0", baud=115200, interval=0xC8, window=0xC8, display="rpsabd", uuid=[], mac=[], rssi=0, active=False, quiet=False, friendly=False)

    # create serial port options argument group
    group = optparse.OptionGroup(p, "Serial Port Options")
    group.add_option('--port', '-p', type="string", help="Serial port device name (default /dev/ttyACM0)", metavar="PORT")
    group.add_option('--baud', '-b', type="int", help="Serial port baud rate (default 115200)", metavar="BAUD")
    p.add_option_group(group)

    # create scan options argument group
    group = optparse.OptionGroup(p, "Scan Options")
    group.add_option('--interval', '-i', type="int", help="Scan interval width in units of 0.625ms (default 200)", metavar="INTERVAL")
    group.add_option('--window', '-w', type="int", help="Scan window width in units of 0.625ms (default 200)", metavar="WINDOW")
    group.add_option('--active', '-a', action="store_true", help="Perform active scan (default passive)\nNOTE: active scans result "
                                                                 "in a 'scan response' request being sent to the slave device, which "
                                                                 "should send a follow-up scan response packet. This will result in "
                                                                 "increased power consumption on the slave device.")
    p.add_option_group(group)

    # create filter options argument group
    group = optparse.OptionGroup(p, "Filter Options")
    group.add_option('--uuid', '-u', type="string", action="append", help="Service UUID(s) to match", metavar="UUID")
    group.add_option('--mac', '-m', type="string", action="append", help="MAC address(es) to match", metavar="ADDRESS")
    group.add_option('--rssi', '-r', type="int", help="RSSI minimum filter (-110 to -20), omit to disable", metavar="RSSI")
    p.add_option_group(group)

    # create output options argument group
    group = optparse.OptionGroup(p, "Output Options")
    group.add_option('--quiet', '-q', action="store_true", help="Quiet mode (suppress initial scan parameter display)")
    group.add_option('--friendly', '-f', action="store_true", help="Friendly mode (output in human-readable format)")
    group.add_option('--display', '-d', type="string", help="Display fields and order (default '%default')\n"
        "  t = Unix time, with milliseconds\n"
        "  r = RSSI measurement (signed integer)\n"
        "  p = Packet type (0 = normal, 4 = scan response)\n"
        "  s = Sender MAC address (hexadecimal)\n"
        "  a = Address type (0 = public, 1 = random)\n"
        "  b = Bonding status (255 = no bond, else bond handle)\n"
        "  d = Advertisement data payload (hexadecimal)", metavar="FIELDS")
    p.add_option_group(group)

    # actually parse all of the arguments
    options, arguments = p.parse_args()

    # validate any supplied MAC address filters
    for arg in options.mac:
        if re.search('[^a-fA-F0-9:]', arg):
            p.print_help()
            print "\n================================================================"
            print "Invalid MAC filter argument '%s'\n-->must be in the form AA:BB:CC:DD:EE:FF" % arg
            print "================================================================"
            exit(1)
        arg2 = arg.replace(":", "").upper()
        if (len(arg2) % 2) == 1:
            p.print_help()
            print "\n================================================================"
            print "Invalid MAC filter argument '%s'\n--> must be 1-6 full bytes in 0-padded hex form (00:01:02:03:04:05)" % arg
            print "================================================================"
            exit(1)
        mac = []
        for i in range(0, len(arg2), 2):
            mac.append(int(arg2[i : i + 2], 16))
        filter_mac.append(mac)

    # validate any supplied UUID filters
    for arg in options.uuid:
        if re.search('[^a-fA-F0-9:]', arg):
            p.print_help()
            print "\n================================================================"
            print "Invalid UUID filter argument '%s'\n--> must be 2 or 16 full bytes in 0-padded hex form (180B or 0123456789abcdef0123456789abcdef)" % arg
            print "================================================================"
            exit(1)
        arg2 = arg.replace(":", "").upper()
        if len(arg2) != 4 and len(arg2) != 32:
            p.print_help()
            print "\n================================================================"
            print "Invalid UUID filter argument '%s'\n--> must be 2 or 16 full bytes in 0-padded hex form (180B or 0123456789abcdef0123456789abcdef)" % arg
            print "================================================================"
            exit(1)
        uuid = []
        for i in range(0, len(arg2), 2):
            uuid.append(int(arg2[i : i + 2], 16))
        filter_uuid.append(uuid)

    # validate RSSI filter argument
    filter_rssi = abs(int(options.rssi))
    if filter_rssi > 0 and (filter_rssi < 20 or filter_rssi > 110):
        p.print_help()
        print "\n================================================================"
        print "Invalid RSSI filter argument '%s'\n--> must be between 20 and 110" % filter_rssi
        print "================================================================"
        exit(1)

    # validate field output options
    options.display = options.display.lower()
    if re.search('[^trpsabd]', options.display):
        p.print_help()
        print "\n================================================================"
        print "Invalid display options '%s'\n--> must be some combination of 't', 'r', 'p', 's', 'a', 'b', 'd'" % options.display
        print "================================================================"
        exit(1)

    # display scan parameter summary, if not in quiet mode
    if not(options.quiet):
        print "================================================================"
        print "BLED112 Scanner for Python v%s" % __version__
        print "================================================================"
        #p.set_defaults(port="/dev/ttyACM0", baud=115200, interval=0xC8, window=0xC8, display="trpsabd", uuid=[], mac=[], rssi=0, active=False, quiet=False, friendly=False)
        print "Serial port:\t%s" % options.port
        print "Baud rate:\t%s" % options.baud
        print "Scan interval:\t%d (%.02f ms)" % (options.interval, options.interval * 1.25)
        print "Scan window:\t%d (%.02f ms)" % (options.window, options.window * 1.25)
        print "Scan type:\t%s" % ['Passive', 'Active'][options.active]
        print "UUID filters:\t",
        if len(filter_uuid) > 0:
            print "0x%s" % ", 0x".join([''.join(['%02X' % b for b in uuid]) for uuid in filter_uuid])
        else:
            print "None"
        print "MAC filter(s):\t",
        if len(filter_mac) > 0:
            print ", ".join([':'.join(['%02X' % b for b in mac]) for mac in filter_mac])
        else:
            print "None"
        print "RSSI filter:\t",
        if filter_rssi > 0:
            print "-%d dBm minimum"% filter_rssi
        else:
            print "None"
        print "Display fields:\t-",
        field_dict = { 't':'Time', 'r':'RSSI', 'p':'Packet type', 's':'Sender MAC', 'a':'Address type', 'b':'Bond status', 'd':'Payload data' }
        print "\n\t\t- ".join([field_dict[c] for c in options.display])
        print "Friendly mode:\t%s" % ['Disabled', 'Enabled'][options.friendly]
        print "----------------------------------------------------------------"
        print "Starting scan for BLE advertisements..."

    # open serial port for BGAPI access
    try:
        ser = serial.Serial(port=options.port, baudrate=options.baud, timeout=1)
    except serial.SerialException as e:
        print "\n================================================================"
        print "Port error (name='%s', baud='%ld'): %s" % (options.port, options.baud, e)
        print "================================================================"
        exit(2)

    # flush buffers
    #print "Flushing serial I/O buffers..."
    ser.flushInput()
    ser.flushOutput()

    # disconnect if we are connected already
    #print "Disconnecting if connected..."
    ble_cmd_connection_disconnect(ser, 0)
    response = ser.read(7) # 7-byte response
    #for b in response: print '%02X' % ord(b),

    # stop advertising if we are advertising already
    #print "Exiting advertising mode if advertising..."
    ble_cmd_gap_set_mode(ser, 0, 0)
    response = ser.read(6) # 6-byte response
    #for b in response: print '%02X' % ord(b),

    # stop scanning if we are scanning already
    #print "Exiting scanning mode if scanning..."
    ble_cmd_gap_end_procedure(ser)
    response = ser.read(6) # 6-byte response
    #for b in response: print '%02X' % ord(b),

    # set scan parameters
    #print "Setting scanning parameters..."
    ble_cmd_gap_set_scan_parameters(ser, options.interval, options.window, options.active)
    response = ser.read(6) # 6-byte response
    #for b in response: print '%02X' % ord(b),

    # start scanning now
    #print "Entering scanning mode for general discoverable..."
    ble_cmd_gap_discover(ser, 1)
    timerList = []
    for ii in range (0, len(sharedList)):
         timerList.append(0)
    while (1):
        # catch all incoming data
        
        while (ser.inWaiting()): bgapi_parse(ord(ser.read()), sharedList, timerList)
        
        # don't burden the CPU
        time.sleep(0.01)
        
        # mark tags not seen in 1000 program cycles as missing
        for ii in range (0, len(sharedList)):
            timerList[ii] = timerList[ii] + 1
            if timerList[ii] > 300: ##delay in one-hundreths of a second before tag is considered inactive
                sharedList[ii] = 0


# define API commands we might use for this script
def ble_cmd_system_reset(p, boot_in_dfu):
    p.write(struct.pack('5B', 0, 1, 0, 0, boot_in_dfu))
def ble_cmd_connection_disconnect(p, connection):
    p.write(struct.pack('5B', 0, 1, 3, 0, connection))
def ble_cmd_gap_set_mode(p, discover, connect):
    p.write(struct.pack('6B', 0, 2, 6, 1, discover, connect))
def ble_cmd_gap_end_procedure(p):
    p.write(struct.pack('4B', 0, 0, 6, 4))
def ble_cmd_gap_set_scan_parameters(p, scan_interval, scan_window, active):
    p.write(struct.pack('<4BHHB', 0, 5, 6, 7, scan_interval, scan_window, active))
def ble_cmd_gap_discover(p, mode):
    p.write(struct.pack('5B', 0, 1, 6, 2, mode))

# define basic BGAPI parser
bgapi_rx_buffer = []
bgapi_rx_expected_length = 0
def bgapi_parse(b, sharedList, timerList):
    global bgapi_rx_buffer, bgapi_rx_expected_length
    #Team SuPear globals
    global led_status, led_counter, RED_LED, GREEN_LED, YELLOW_LED
    
    if len(bgapi_rx_buffer) == 0 and (b == 0x00 or b == 0x80):
        bgapi_rx_buffer.append(b)
    elif len(bgapi_rx_buffer) == 1:
        bgapi_rx_buffer.append(b)
        bgapi_rx_expected_length = 4 + (bgapi_rx_buffer[0] & 0x07) + bgapi_rx_buffer[1]
    elif len(bgapi_rx_buffer) > 1:
        bgapi_rx_buffer.append(b)

    #print '%02X: %d, %d' % (b, len(bgapi_rx_buffer), bgapi_rx_expected_length)
    if bgapi_rx_expected_length > 0 and len(bgapi_rx_buffer) == bgapi_rx_expected_length:
        #print '<=[ ' + ' '.join(['%02X' % b for b in bgapi_rx_buffer ]) + ' ]'
        packet_type, payload_length, packet_class, packet_command = bgapi_rx_buffer[:4]
        bgapi_rx_payload = b''.join(chr(i) for i in bgapi_rx_buffer[4:])
        if packet_type & 0x80 == 0x00: # response
            bgapi_filler = 0
        else: # event
            if packet_class == 0x06: # gap
                if packet_command == 0x00: # scan_response
                    rssi, packet_type, sender, address_type, bond, data_len = struct.unpack('<bB6sBBB', bgapi_rx_payload[:11])
                    sender = [ord(b) for b in sender]
                    data_data = [ord(b) for b in bgapi_rx_payload[11:]]
                    display = 1

                    # parse all ad fields from ad packet
                    ad_fields = []
                    this_field = []
                    ad_flags = 0
                    ad_services = []
                    ad_local_name = []
                    ad_tx_power_level = 0
                    ad_manufacturer = []

                    bytes_left = 0
                    for b in data_data:
                        if bytes_left == 0:
                            bytes_left = b
                            this_field = []
                        else:
                            this_field.append(b)
                            bytes_left = bytes_left - 1
                            if bytes_left == 0:
                                ad_fields.append(this_field)
                                #print "%s" % ''.join(['%02X' % dd for dd in this_field])
                                if this_field[0] == 0x01: # flags
                                    ad_flags = this_field[1]
                                if this_field[0] == 0x02 or this_field[0] == 0x03: # partial or complete list of 16-bit UUIDs
                                    for i in xrange((len(this_field) - 1) / 2):
                                        ad_services.append(this_field[-1 - i*2 : -3 - i*2 : -1])
                                        #print "16 bit UUID found"
                                if this_field[0] == 0x04 or this_field[0] == 0x05: # partial or complete list of 32-bit UUIDs
                                    for i in xrange((len(this_field) - 1) / 4):
                                        ad_services.append(this_field[-1 - i*4 : -5 - i*4 : -1])
                                        #print "32 bit UUID found"
                                if this_field[0] == 0x06 or this_field[0] == 0x07: # partial or complete list of 128-bit UUIDs
                                    for i in xrange((len(this_field) - 1) / 16):
                                        ad_services.append(this_field[-1 - i*16 : -17 - i*16 : -1])
                                        #print "128 bit UUID found"
                                if this_field[0] == 0x08 or this_field[0] == 0x09: # shortened or complete local name
                                    ad_local_name = this_field[1:]
                                if this_field[0] == 0x0A: # TX power level
                                    ad_tx_power_level = this_field[1]

                                # OTHER AD PACKET TYPES NOT HANDLED YET

                                if this_field[0] == 0xFF: # manufacturer specific data
                                    #Assuming nimble devices beacon / estimote
                                    ad_services.append(this_field[5:21]) #128-bit UUID
                                    #print "128 bit UUID found "
                                    #print ''.join('%02X' % ee for ee in ad_services[0])

                                if this_field[0] == 0x07: # BGLIB_GAP_AD_TYPE_SERVICES_128BIT_ALL
                                    # SuPear tag - you should probably ignore this unless you're in our team
                                    ad_services.append(this_field[5:21]) #128-bit UUID
                                    #this_field[5:21] has the UUID. Check if it's UUID of moving or still tag and turn on green or YELLOW LED accordingly
                                    #print "Attempting to ID a tag." + str(sender[::-1])
                                    #identify the tag
                                    for ii in range(0, len(sharedList)):
                                        #print "Comparing to " + str(filter_mac[ii])
                                        if filter_mac[ii] == sender[::-1]:
                                          #print "match found"
                                          if this_field[1] == 0: #With proto 0 only first value is needed to check, 0 = Moving, 0xE4 = Still
                                              sharedList[ii] = 2
                                              timerList[ii] = 0
                                          elif this_field[1] == 0xE4:
                                              sharedList[ii] = 1
                                              timerList[ii] = 0
                                    #print "128 bit UUID found in a SuPear tag"
                                    #print "%s" % this_field[5:21]
                                    #print ''.join('%02X' % ee for ee in ad_services[0])

        bgapi_rx_buffer = []

# gracefully exit without a big exception message if possible
def ctrl_c_handler(signal, frame):
    #print 'Goodbye, cruel world!'
    exit(0)

signal.signal(signal.SIGINT, ctrl_c_handler)

