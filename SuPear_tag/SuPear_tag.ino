// ITEM_FINDER ADVERTSIEING, edit from
// Bluegiga BGLib Arduino interface library slave device stub sketch
// 2014-02-12 by Jeff Rowberg <jeff@rowberg.net>
// Updates should (hopefully) always be available at https://github.com/jrowberg/bglib

/* ============================================
      THIS SCRIPT WILL NOT COMMUNICATE PROPERLY IF YOU DO NOT ENSURE ONE OF THE
   FOLLOWING IS TRUE:

   1. You enable the <wakeup_pin> functionality in your firmware

   2. You COMMENT OUT the two lines 128 and 129 below which depend on wake-up
      funcitonality to work properly (they will BLOCK otherwise):

          ble112.onBeforeTXCommand = onBeforeTXCommand;
          ble112.onTXCommandComplete = onTXCommandComplete;
          
    -> FOR THE MOMENT OPTION TWO
   ============================================  
*/

#include <SoftwareSerial.h>
#include "BGLib.h"

// uncomment the following lines for debug serial output
#define BLE_DEBUG 0
#define ACCELOMETER_DEBUG 0
#define CSV_OUTPUT 0
#define PROGRAM_FLOW_DEBUG 0
#define ACCELOMETER_TRIGGER_LEVEL 3
#define DEBUG_LED 0 
// ================================================================
// BLE STATE TRACKING (UNIVERSAL TO JUST ABOUT ANY BLE PROJECT)
// ================================================================

// BLE state machine definitions
#define BLE_STATE_STANDBY           0
#define BLE_STATE_SCANNING          1
#define BLE_STATE_ADVERTISING       2
#define BLE_STATE_CONNECTING        3
#define BLE_STATE_CONNECTED_MASTER  4
#define BLE_STATE_CONNECTED_SLAVE   5

// BLE state/link status tracker
uint8_t ble_state = BLE_STATE_STANDBY;
uint8_t ble_encrypted = 0;  // 0 = not encrypted, otherwise = encrypted
uint8_t ble_bonding = 0xFF; // 0xFF = no bonding, otherwise = bonding handle

// ITEM-Variable

    // State of Item-tag
    //boolean moving = false;
    
    // custom advertising data if Item-tag is resting
    uint8 adv_data_resting[] = {
        0x02, // field length
        BGLIB_GAP_AD_TYPE_FLAGS, // field type (0x01)
        0x06, // data (0x02 | 0x04 = 0x06, general discoverable + BLE only, no BR+EDR)
        0x11, // field length
        BGLIB_GAP_AD_TYPE_SERVICES_128BIT_ALL, // field type (0x07)
        0xe4, 0xba, 0x94, 0xc3, 0xc9, 0xb7, 0xcd, 0xb0, 0x9b, 0x48, 0x7a, 0x43, 0x8a, 0xe5, 0x5a, 0x19
     };
     
    // custom advertising data if Item-tag is moving
    uint8 adv_data_moving[] = {
        0x02, // field length
        BGLIB_GAP_AD_TYPE_FLAGS, // field type (0x01)
        0x06, // data (0x02 | 0x04 = 0x06, general discoverable + BLE only, no BR+EDR)
        0x11, // field length
        BGLIB_GAP_AD_TYPE_SERVICES_128BIT_ALL, // field type (0x07)
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
    };
    

// ================================================================
// HARDWARE CONNECTIONS AND GATT STRUCTURE SETUP
// ================================================================

// NOTE: this assumes you are using one of the following firmwares:
//  - BGLib_U1A1P_38400_noflow
//  - BGLib_U1A1P_38400_noflow_wake16
//  - BGLib_U1A1P_38400_noflow_wake16_hwake15
// If not, then you may need to change the pin assignments and/or
// GATT handles to match your firmware.

#define LED_PIN         A2   // LED2
#define LED_PIN         A1  // TAG LED pin
#define BLE_WAKEUP_PIN  7   // BLE wake-up pin
#define BLE_RESET_PIN   6   // BLE reset pin (active-low)
#define CS              10

#define GATT_HANDLE_C_RX_DATA   17  // 0x11, supports "write" operation
#define GATT_HANDLE_C_TX_DATA   20  // 0x14, supports "read" and "indicate" operations

// use SoftwareSerial on pins D2/D3 for RX/TX (Arduino side)
SoftwareSerial bleSerialPort(4, 5);
SoftwareSerial debugSerialPort(9, A0); // only in the debugtag 
SoftwareSerial& debugOutput = debugSerialPort;
// create BGLib object:
//  - use SoftwareSerial por for module comms
//  - use nothing for passthrough comms (0 = null pointer)
//  - enable packet mode on API protocol since flow control is unavailable
BGLib ble112((HardwareSerial *)&bleSerialPort, 0, 1);

#define BGAPI_GET_RESPONSE(v, dType) dType *v = (dType *)ble112.getLastRXPayload()

// ================================================================
// Motion Sensor SETUP AND LOOP FUNCTIONS
// ================================================================
#define OUT_X_MSB 0x01
#define OUT_Y_MSB 0x03
#define OUT_Z_MSB 0x05
#define WHO_AM_I  0x0D

byte x=0x00; // Initializing x acceleration
byte y=0x00; // Initializing y acceleration
byte z=0x00; // Initializing z acceleration
byte inByte = 0x00; // return value of movement state.

#include <SPI.h>

void accwrite(byte regaddress, byte data)
{

  //select the IC
  digitalWrite(CS, LOW);
  SPI.transfer((regaddress & 0x7F) | 0x80); //Set the first bit HIGH
  SPI.transfer(regaddress & 0x80); //Write the most significant bit of address
  SPI.transfer(data); //Write data
  digitalWrite(CS, HIGH); //Deselect 

}

byte accread(byte regaddress)
{
  byte data = 0;
  //select the IC
  digitalWrite(CS, LOW);
  SPI.transfer(regaddress & 0x7F); //Set the first bit LOW
  SPI.transfer(regaddress & 0x80); //Write the most significant bit of address
  data = SPI.transfer(0x00); //Write dummy data, receive value
  digitalWrite(CS, HIGH); //Deselect  IC
  return data;
}

/*
 * Returns 0 if tag is not moving, 1 if tag is moving
 */
byte check(void)
{

//Store previous values, down to 2 times
static int8_t lastX = 0;
static int8_t lastY = 0;
static int8_t lastZ = 0;

int8_t nowX = (int8_t) accread(0x01);
int8_t nowY = (int8_t) accread(0x03);
int8_t nowZ = (int8_t) accread(0x05);

//High pass values, nextX-lastX = 0 if no change
int8_t HiPassX = nowX - lastX;  
int8_t HiPassY = nowY - lastY;
int8_t HiPassZ = nowZ - lastZ;

int16_t movement = abs(HiPassX) + abs(HiPassY) + abs(HiPassZ);

lastX = nowX;
lastY = nowY;
lastZ = nowZ;
 
#if ACCELOMETER_DEBUG
	debugOutput.print("Movement: ");
	debugOutput.println(movement);
#endif

byte rvalue = '0';
  if (movement > ACCELOMETER_TRIGGER_LEVEL)
    rvalue++;
 
#if ACCELOMETER_DEBUG
	debugOutput.print("rvalue: ");
	debugOutput.println(rvalue);
#endif

#if CSV_OUTPUT
  debugOutput.print("Last values");
  debugOutput.print(lastX);
  debugOutput.print("; ");
  debugOutput.print(lastY);
  debugOutput.print("; ");
  debugOutput.print(lastZ);
  debugOutput.println("; ");
  
  debugOutput.print(nowX);
  debugOutput.print("; ");
  debugOutput.print(nowY);
  debugOutput.print("; ");
  debugOutput.print(nowZ);
  debugOutput.println("; ");
#endif

  return rvalue;
}

//Power settings
//#include "power.h"
//Power power_cls();
#include <avr/wdt.h>
#include <avr/sleep.h>
#include <avr/power.h>
void watchdogSetup(void)
{
cli();
wdt_reset();
/*
WDTCSR configuration:
WDIE = 1: Interrupt Enable
WDE = 1 :Reset Enable
See table for time-out variations:
WDP3 = 0 :For 1000ms Time-out
WDP2 = 1 :For 1000ms Time-out
WDP1 = 1 :For 1000ms Time-out
WDP0 = 0 :For 1000ms Time-out
*/
// Enter Watchdog Configuration mode:
WDTCSR |= (1<<WDCE) | (1<<WDE);
// Set Watchdog settings:
WDTCSR = (1<<WDIE) | (0<<WDE) |
(0<<WDP3) | (1<<WDP2) | (1<<WDP1) |
(0<<WDP0);
sei();
}

ISR(WDT_vect) // Watchdog timer interrupt.
{
  
}


// ================================================================
// ARDUINO APPLICATION SETUP AND LOOP FUNCTIONS
// ================================================================


// initialization sequence
void setup() {
   
    // initialize status LED
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);
    
    // initialize BLE reset pin (active-low)
    pinMode(BLE_RESET_PIN, OUTPUT);
    digitalWrite(BLE_RESET_PIN, HIGH);

    // initialize BLE wake-up pin to allow (not force) sleep mode (assumes active-high)
    pinMode(BLE_WAKEUP_PIN, OUTPUT);
    digitalWrite(BLE_WAKEUP_PIN, LOW);

    // set up internal status handlers (these are technically optional)
    ble112.onBusy = onBusy;
    ble112.onIdle = onIdle;
    ble112.onTimeout = onTimeout;

    // ONLY enable these if you are using the <wakeup_pin> parameter in your firmware's hardware.xml file
    // BLE module must be woken up before sending any UART data
    ble112.onBeforeTXCommand = onBeforeTXCommand;
    ble112.onTXCommandComplete = onTXCommandComplete;

    // set up BGLib event handlers
    ble112.ble_evt_system_boot = my_ble_evt_system_boot;
    //ble112.ble_evt_connection_status = my_ble_evt_connection_status;
    //ble112.ble_evt_connection_disconnected = my_ble_evt_connection_disconnect;
    //ble112.ble_evt_attributes_value = my_ble_evt_attributes_value;

    // open Arduino USB serial (and wait, if we're using Leonardo)
    // use 38400 since it works at 8MHz as well as 16MHz
    debugOutput.begin(38400);

    // open BLE software serial port
    bleSerialPort.begin(38400);

    // reset module (maybe not necessary for your application)
    digitalWrite(BLE_RESET_PIN, LOW);
    delay(5); // wait 5ms
    digitalWrite(BLE_RESET_PIN, HIGH);
    //ble112.ble_cmd_gap_set_mode(BGLIB_GAP_GENERAL_DISCOVERABLE, BGLIB_GAP_UNDIRECTED_CONNECTABLE);
    
    //Setup accelerometer
    SPI.begin();
    SPI.setBitOrder(MSBFIRST);
    SPI.setClockDivider(SPI_CLOCK_DIV128);
    SPI.setDataMode(SPI_MODE0);
    accwrite(0x2A,0x3D); // Set the motion sensor to active mode
    
    //Wait for the BLE init.
    while(!bleSerialPort.available()){
      #if PROGRAM_FLOW_DEBUG
      debugOutput.println("Waiting for ble112 to init");
      delay(100);
      #endif
    }
    
    //setup watchdog
    watchdogSetup();

    #if PROGRAM_FLOW_DEBUG  
    debugOutput.print("Setup complete\n");
    #endif
}

// main application loop
void loop() {
    // keep polling for new data from BLE
    ble112.checkActivity();
    
    inByte = check();
    static byte lastState = 0;
    if(lastState == inByte){
      inByte = 0; 
    }
    else {
      lastState = inByte;

      #if PROGRAM_FLOW_DEBUG
      debugOutput.println("Status of tag has changed"); 
      #endif
    }
    //delay(freq); //TODO: Run check at fixed intervals

    switch (inByte) {
    case '0':    
      ble112.ble_cmd_gap_set_adv_data(0, 0x15, adv_data_resting);
      #if PROGRAM_FLOW_DEBUG
      debugOutput.println("Advertising, now with adv.data for resting Item-tag");
      #endif
      break;
      
     case '1':
      ble112.ble_cmd_gap_set_adv_data(0, 0x15, adv_data_moving);
      #if PROGRAM_FLOW_DEBUG
      debugOutput.println("Advertising, now with adv.data for moving Item-tag");
      #endif
      break;
      
     default:
      //do nothing on invalid inbyte
      break;    
    }
 
    #if PROGRAM_FLOW_DEBUG
    debugOutput.println("Entering sleep");
    #endif
    //Flush and end serial communication in case there is some other debug option on 
    debugOutput.flush();
    debugOutput.end();


    bleSerialPort.flush();
    bleSerialPort.end();
    set_sleep_mode(SLEEP_MODE_PWR_DOWN);   // sleep mode is set here
    cli();
    sleep_enable(); 
    sei();
    sleep_mode();
    sleep_disable();

    //Always start serial comms in case there is some debug option on
    debugOutput.begin(38400);

    wdt_reset(); //Next wake up in constant interval 
    bleSerialPort.begin(38400);

    #if PROGRAM_FLOW_DEBUG
    debugOutput.println("Waking up");
    #endif

    // blink Arduino LED based on state:
    //  - solid = STANDBY
    //  - 1 pulse per second = ADVERTISING
    //  - 2 pulses per second = CONNECTED_SLAVE
    //  - 3 pulses per second = CONNECTED_SLAVE with encryption
    #if DEBUG_LED
    uint16_t slice = millis() % 1000;
    if (ble_state == BLE_STATE_STANDBY) {
        digitalWrite(LED_PIN, HIGH);
        //debugOutput.print("STANDBY");
    } else if (ble_state == BLE_STATE_ADVERTISING) {
        digitalWrite(LED_PIN, slice < 100);
        // debugOutput.print("ADVERTISING");
    } else if (ble_state == BLE_STATE_CONNECTED_SLAVE) {
        if (!ble_encrypted) {
            digitalWrite(LED_PIN, slice < 100 || (slice > 200 && slice < 300));
        } else {
            digitalWrite(LED_PIN, slice < 100 || (slice > 200 && slice < 300) || (slice > 400 && slice < 500));
        }
    }
    #endif
}



// ================================================================
// INTERNAL BGLIB CLASS CALLBACK FUNCTIONS
// ================================================================

// called when the module begins sending a command
void onBusy() {
    // turn LED on when we're busy
    //digitalWrite(LED_PIN, HIGH);
}

// called when the module receives a complete response or "system_boot" event
void onIdle() {
    // turn LED off when we're no longer busy
    //digitalWrite(LED_PIN, LOW);
}

// called when the parser does not read the expected response in the specified time limit
void onTimeout() {
    // reset module (might be a bit drastic for a timeout condition though)
    digitalWrite(BLE_RESET_PIN, LOW);
    delay(5); // wait 5ms
    digitalWrite(BLE_RESET_PIN, HIGH);
}

// called immediately before beginning UART TX of a command
void onBeforeTXCommand() {
    // wake module up (assuming here that digital pin 5 is connected to the BLE wake-up pin)
    digitalWrite(BLE_WAKEUP_PIN, HIGH);

    // wait for "hardware_io_port_status" event to come through, and parse it (and otherwise ignore it)
    uint8_t *last;
    while (1) {
        ble112.checkActivity();
        last = ble112.getLastEvent();
        if (last[0] == 0x07 && last[1] == 0x00) break;
    }

    // give a bit of a gap between parsing the wake-up event and allowing the command to go out
    delayMicroseconds(1000);
}

// called immediately after finishing UART TX
void onTXCommandComplete() {
    // allow module to return to sleep (assuming here that digital pin 5 is connected to the BLE wake-up pin)
    digitalWrite(BLE_WAKEUP_PIN, LOW);
}



// ================================================================
// APPLICATION EVENT HANDLER FUNCTIONS
// ================================================================

void my_ble_evt_system_boot(const ble_msg_system_boot_evt_t *msg) {
    #if BLE_DEBUG
        debugOutput.print("###\tsystem_boot: { ");
        debugOutput.print("major: "); debugOutput.print(msg -> major, HEX);
        debugOutput.print(", minor: "); debugOutput.print(msg -> minor, HEX);
        debugOutput.print(", patch: "); debugOutput.print(msg -> patch, HEX);
        debugOutput.print(", build: "); debugOutput.print(msg -> build, HEX);
        debugOutput.print(", ll_version: "); debugOutput.print(msg -> ll_version, HEX);
        debugOutput.print(", protocol_version: "); debugOutput.print(msg -> protocol_version, HEX);
        debugOutput.print(", hw: "); debugOutput.print(msg -> hw, HEX);
        debugOutput.println(" }");
    #endif

    // set advertisement interval to 800-1200ms, use all advertisement channels
    // (note min/max parameters are in units of 625 uSec)
    ble112.ble_cmd_gap_set_adv_parameters(1280, 1920, 7);
    while (ble112.checkActivity(1000));

    // set custom advertisement data
    ble112.ble_cmd_gap_set_adv_data(0, 0x15, adv_data_resting);
    while (ble112.checkActivity(1000));

    // put module into discoverable/ NOT connectable mode (with user-defined advertisement data)
    ble112.ble_cmd_gap_set_mode(BGLIB_GAP_USER_DATA, BGLIB_GAP_NON_CONNECTABLE);
    while (ble112.checkActivity(1000));

    // set state to ADVERTISING
    ble_state = BLE_STATE_ADVERTISING;
}


void my_ble_evt_connection_status(const ble_msg_connection_status_evt_t *msg) {
    #ifdef BLE_DEBUG
        debugOutput.print("###\tconnection_status: { ");
        debugOutput.print("connection: "); debugOutput.print(msg -> connection, HEX);
        debugOutput.print(", flags: "); debugOutput.print(msg -> flags, HEX);
        debugOutput.print(", address: ");
        // this is a "bd_addr" data type, which is a 6-byte uint8_t array
        for (uint8_t i = 0; i < 6; i++) {
            if (msg -> address.addr[i] < 16) debugOutput.write('0');
            debugOutput.print(msg -> address.addr[i], HEX);
        }
        debugOutput.print(", address_type: "); debugOutput.print(msg -> address_type, HEX);
        debugOutput.print(", conn_interval: "); debugOutput.print(msg -> conn_interval, HEX);
        debugOutput.print(", timeout: "); debugOutput.print(msg -> timeout, HEX);
        debugOutput.print(", latency: "); debugOutput.print(msg -> latency, HEX);
        debugOutput.print(", bonding: "); debugOutput.print(msg -> bonding, HEX);
        debugOutput.println(" }");
    #endif

    // "flags" bit description:
    //  - bit 0: connection_connected
    //           Indicates the connection exists to a remote device.
    //  - bit 1: connection_encrypted
    //           Indicates the connection is encrypted.
    //  - bit 2: connection_completed
    //           Indicates that a new connection has been created.
    //  - bit 3; connection_parameters_change
    //           Indicates that connection parameters have changed, and is set
    //           when parameters change due to a link layer operation.

    // check for new connection established
    if ((msg -> flags & 0x05) == 0x05) {
        // track state change based on last known state, since we can connect two ways
        if (ble_state == BLE_STATE_ADVERTISING) {
            ble_state = BLE_STATE_CONNECTED_SLAVE;
        } else {
            ble_state = BLE_STATE_CONNECTED_MASTER;
        }
    }

    // update "encrypted" status
    ble_encrypted = msg -> flags & 0x02;
    
    // update "bonded" status
    ble_bonding = msg -> bonding;
}

void my_ble_evt_connection_disconnect(const struct ble_msg_connection_disconnected_evt_t *msg) {
    #ifdef BLE_DEBUG
        debugOutput.print("###\tconnection_disconnect: { ");
        debugOutput.print("connection: "); debugOutput.print(msg -> connection, HEX);
        debugOutput.print(", reason: "); debugOutput.print(msg -> reason, HEX);
        debugOutput.println(" }");
    #endif

    // set state to DISCONNECTED
    //ble_state = BLE_STATE_DISCONNECTED;
    // ^^^ skip above since we're going right back into advertising below

    // after disconnection, resume advertising as discoverable/connectable
    //ble112.ble_cmd_gap_set_mode(BGLIB_GAP_GENERAL_DISCOVERABLE, BGLIB_GAP_UNDIRECTED_CONNECTABLE);
    //while (ble112.checkActivity(1000));

    // after disconnection, resume advertising as discoverable/connectable (with user-defined advertisement data)
    ble112.ble_cmd_gap_set_mode(BGLIB_GAP_USER_DATA, BGLIB_GAP_UNDIRECTED_CONNECTABLE);
    while (ble112.checkActivity(1000));

    // set state to ADVERTISING
    ble_state = BLE_STATE_ADVERTISING;

    // clear "encrypted" and "bonding" info
    ble_encrypted = 0;
    ble_bonding = 0xFF;
}

void my_ble_evt_attributes_value(const struct ble_msg_attributes_value_evt_t *msg) {
    #ifdef BLE_DEBUG
        debugOutput.print("###\tattributes_value: { ");
        debugOutput.print("connection: "); debugOutput.print(msg -> connection, HEX);
        debugOutput.print(", reason: "); debugOutput.print(msg -> reason, HEX);
        debugOutput.print(", handle: "); debugOutput.print(msg -> handle, HEX);
        debugOutput.print(", offset: "); debugOutput.print(msg -> offset, HEX);
        debugOutput.print(", value_len: "); debugOutput.print(msg -> value.len, HEX);
        debugOutput.print(", value_data: ");
        // this is a "uint8array" data type, which is a length byte and a uint8_t* pointer
        for (uint8_t i = 0; i < msg -> value.len; i++) {
            if (msg -> value.data[i] < 16) debugOutput.write('0');
            debugOutput.print(msg -> value.data[i], HEX);
        }
        debugOutput.println(" }");
    #endif

    // check for data written to "c_rx_data" handle
    if (msg -> handle == GATT_HANDLE_C_RX_DATA && msg -> value.len > 0) {
        // set ping 8, 9, and 10 to three lower-most bits of first byte of RX data
        // (nice for controlling RGB LED or something)
        digitalWrite(8, msg -> value.data[0] & 0x01);
        digitalWrite(9, msg -> value.data[0] & 0x02);
        digitalWrite(10, msg -> value.data[0] & 0x04);
    }
}
