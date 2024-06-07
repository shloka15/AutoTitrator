#include <SoftwareSerial.h>

#define rx 2
#define tx 3

SoftwareSerial myserial(rx, tx);

String sensorstring = "";                             // a string to hold the data from the Atlas Scientific product
boolean sensor_string_complete = false;               // have we received all the data from the Atlas Scientific product

void setup() {
  Serial.begin(9600);                                 // set baud rate for the hardware serial port_0 to 9600
  myserial.begin(9600);                               // set baud rate for the software serial port to 9600
}

void loop() {
  if (myserial.available() > 0) {
    char inchar = (char)myserial.read();              // get the char we just received
    sensorstring += inchar;                           // add the char to the var called sensorstring
    if (inchar == '\r') {                             // if the incoming character is a <CR>
      sensor_string_complete = true;                  // set the flag
    }
  }

  if (sensor_string_complete == true) {
    print_EC_data();                                  // call function to parse and print EC data
    sensorstring = "";                                // clear the string
    sensor_string_complete = false;                   // reset the flag
  }
}

void print_EC_data(void) {
  char sensorstring_array[30];                        // we make a char array
  char *EC;                                           // char pointer used in string parsing
  char *TDS;
  char *SAL;
  char *GRAV;
  float f_ec;                                         //used to hold a floating point number that is the EC
  
  sensorstring.toCharArray(sensorstring_array, 30);   //convert the string to a char array 
  EC = strtok(sensorstring_array, ",");               //let's parse the array at each comma
  TDS = strtok(NULL, ",");
  SAL = strtok(NULL, ",");
  GRAV = strtok(NULL, ",");
  sensorstring.toCharArray(sensorstring_array, 30);   // convert the string to a char array
  EC = strtok(sensorstring_array, ",");               // let's parse the array at each comma

  Serial.print("EC:");
  Serial.println(EC);                                 // this is the EC value
  Serial.println();
}
