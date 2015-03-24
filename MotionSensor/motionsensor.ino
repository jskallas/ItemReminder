#include <Wire.h>
#define acc 0x1D

byte x=0x00; // Initializing x acceleration
byte y=0x00; // Initializing y acceleration
byte z=0x00; // Initializing z acceleration
int led = 13;
int count = 0;
int trigger = 10; // Number of counts to put the led on
int limit = 30; // Count upper limit
int freq = 100; // Delay between each loop

void setup()
{
  Serial.begin(9600);
  Wire.begin();
  pinMode(led,OUTPUT);
  accwrite(0x2A,0x03); // Set the motion sensor to active mode
}

void loop()
{
 Serial.print(accread(0x01));
 Serial.print(("\t"));
 Serial.print(accread(0x03));
 Serial.print(("\t"));
 Serial.print(accread(0x05));
 Serial.print(("\t"));
 Serial.print(count);
 Serial.println();
 check();
 delay(freq);
}

void accwrite(byte regaddress, byte data)
{
  Wire.beginTransmission(acc);
  Wire.write(regaddress);
  Wire.write(data);
  Wire.endTransmission();
}

byte accread(byte regaddress)
{
  Wire.beginTransmission(acc);
  Wire.write(regaddress);
  Wire.endTransmission(false);
  Wire.requestFrom(acc,1);
  while(!Wire.available())
  {
  }
  return Wire.read(); 
}

void ledon()
{
  digitalWrite(led, HIGH);   
}

void ledoff()
{
  digitalWrite(led, LOW);
}

void check() // Values of at least 2 of 3 axises must change to make the count to grow. 
{
 if(x-accread(0x01)!=0 && y-accread(0x03)!=0 && count<=30)
 {
   count=count+2;
 }
 else if(y-accread(0x03)!=0 && z-accread(0x05)!=0 && count<=30)
  {
   count=count+2;
  }
 else if(x-accread(0x01)!=0 && z-accread(0x05)!=0 && count<=30)
  {
   count=count+2;
  }
 else
 {
   if(count>0)
   {
     count=count-1;
   }
   else
   {
     count=0;
   }
 }
if(count>=trigger)
{
  ledon();
}
else
{
  ledoff();
}
 x=accread(0x01);
 y=accread(0x03);
 z=accread(0x05);
}
