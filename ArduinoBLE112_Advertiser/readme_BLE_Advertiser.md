#WIRING

|BLE112        | Arduino Uno / Nano  | Comment |
|--------------|---------------------|---------|
|BLE112 P0_4   |Arduino Digital Pin 2|         |
|BLE112 P0_5   |Arduino Digital Pin 2|Fix me   |
|GND           |GND                  |         |
|3.3 V         |3.3 V                |(so you can power both modules via Arduinos USB-Port)|
|BLE_RESET     |Arduino Digital Pin 6|         |
#Advertising message:
Change last line in	adv_data_resting [ ]  / adv_data_moving[ ]
#Advertising Interval:
ble112.ble_cmd_gap_set_adv_parameters (320, 480, 7);
where arguments are
first: 	*minimum* *advertisement* *interval* in units of 625us
second: *maximum* *advertisement* *interval* in units of 625us
last: advertisement_ channels, here all there channels are used

for min 0.9 s, max 1 s it should be ble112.ble_cmd_gap_set_adv_parameters (1440, 1600, 7);

