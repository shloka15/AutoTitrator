const float tit = 100.0;
const float mix = 6.0;
const float ini = 5000.0;
const float endi = 11500.0;


#include <SoftwareSerial.h>                           // Include the SoftwareSerial library

#define rx1 2                                          // Define pin for rx1
#define tx1 3                                          // Define pin for tx1
#define rx2 10                                         // Define pin for rx2
#define tx2 11                                         // Define pin for tx2

#define isolator 9                                     // Voltage Isolator

const int dirPin = 7;                                  // Stepper
const int stepPin = 6;
const int enPin = 5;

const int steps = 6400;

float roundUpToMultiple(float value, float multiple) {
  return ceil(value / multiple) * multiple;
}

float rotation = roundUpToMultiple(tit / 5378.0, 0.005);     // Number of rotations
unsigned long stepDelay = 10000;                       // Initial delay for the stepper motor in microseconds (1 rotation in 128 seconds)
unsigned long stepInterval = (mix + (rotation*128)) * 1000;        // delay between steps //consider the time it takes to rotate

float ini_rotation = roundUpToMultiple(ini / 5378.0, 0.005); // To dispense initial volume
unsigned long wait_time = 15000;                       // Mixing time after initial volume is dispensed

float adjusted_ini = 5378 * ini_rotation;
float adjusted_tit = 5378 * rotation;
float adjusted_endi = adjusted_ini + (adjusted_tit * ceil((endi - adjusted_ini) / adjusted_tit));

int j = 0;
int number_of_times = ceil((adjusted_endi - adjusted_ini) / adjusted_tit);

SoftwareSerial myserial1(rx1, tx1);                    // Define software serial port for mode 1
SoftwareSerial myserial2(rx2, tx2);                    // Define software serial port for mode 2

String inputstring = "";                               // String to hold incoming data from the PC
String sensorstring = "";                              // String to hold the data from the Atlas Scientific product
boolean input_string_complete = false;                 // Have we received all the data from the PC
boolean sensor_string_complete = false;                // Have we received all the data from the Atlas Scientific product

float t = 0.00;                                       
bool mode = 1;                                         // Initialize the mode variable
unsigned long startTime = 0;                           // Variable to store the start time
float marker = 0.00;
float prevMarker = 0.00;

unsigned long previousStepTime = 0;                    // Variable to store the last step time
unsigned long previousIntervalTime = 0;                // Variable to store the last interval time
unsigned long stepperStartTime = 0;                    // Variable to store the time when stepper should start
int currentStep = 0;                                   // Variable to store the current step
int n = 0; 

bool stepperStarted = false;                           // Flag to indicate if the stepper motor has started
bool markerSet = false;  

float serial_values[5] = {0.0, 0.0, 0.0, 0.0, 0.0};    // Define an array to store serial values

void setup() {                                         // Set up the hardware
  Serial.begin(9600);                                  // Set baud rate for the hardware serial port_0 to 9600
  port();
  inputstring.reserve(10);                             // Set aside some bytes for receiving data from the PC
  sensorstring.reserve(30);                            // Set aside some bytes for receiving data from Atlas Scientific product
  pinMode(isolator, OUTPUT);
  digitalWrite(isolator, HIGH);
  startTime = millis();                                // Initialize the start time

  pinMode(dirPin, OUTPUT);
  pinMode(stepPin, OUTPUT);                            // Stepper
  pinMode(enPin, OUTPUT);
  
  digitalWrite(dirPin, LOW);                           // Set the direction of the stepper motor
  previousStepTime = micros();                         // Initialize the previous step time with the current time
  previousIntervalTime = millis();                     // Initialize the previous interval time with the current time

  delay(1000);

  if (ini > 0){
    dispense();
  } else{
    delay(1000);
  }
  
  //marker = 1.00;
  probe_data(); 
  print_serial_data();
  stepperStartTime = millis();                         // Set the stepper start time to now  
}

void dispense(){
  // Perform initial rotation
  digitalWrite(enPin, LOW);                            // Enable motor
  digitalWrite(dirPin, LOW);
  for (int x = 0; x < steps * ini_rotation; x++) {
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(stepDelay);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(stepDelay);
  }
  digitalWrite(enPin, HIGH);                           // Disable motor

  // Wait for the specified time
  delay(wait_time);
}

void port() {
  if (mode == 1) {
    myserial1.begin(9600);                             // Set baud rate for software serial port 1 to 9600
  } else {
    myserial2.begin(9600);                             // Set baud rate for software serial port 2 to 9600
  }
}

void serialEvent() {                                   // If the hardware serial port_0 receives a char
  inputstring = Serial.readStringUntil(13);            // Read the string until we see a <CR>
  input_string_complete = true;                        // Set the flag used to tell if we have received a completed string from the PC
}

void loop() {                                          // Here we go...

  if (input_string_complete == true) {                 // If a string from the PC has been received in its entirety
    if (mode == 1) {
      myserial1.print(inputstring);                    // Send that string to the Atlas Scientific product on port 1
      myserial1.print('\r');                           // Add a <CR> to the end of the string
    } else {
      myserial2.print(inputstring);                    // Send that string to the Atlas Scientific product on port 2
      myserial2.print('\r');                           // Add a <CR> to the end of the string
    }
    inputstring = "";                                  // Clear the string
    input_string_complete = false;                     // Reset the flag used to tell if we have received a completed string from the PC
  }

  probe_data();

  unsigned long currentTime = millis();
  if (!stepperStarted && currentTime >= stepperStartTime) {
    stepperStarted = true;
    previousIntervalTime = currentTime;                // Initialize the previous interval time
  }

  if (stepperStarted && currentTime - previousIntervalTime >= stepInterval) {
    previousIntervalTime = currentTime;
    if (j < number_of_times) {
      j++;

      marker = 1.00;
      update_marker();
      print_serial_data();
      
      digitalWrite(enPin, LOW); // Enable motor

      digitalWrite(dirPin, LOW);
      for (int x = 0; x < steps * rotation; x++) {
        digitalWrite(stepPin, HIGH);
        delayMicroseconds(stepDelay);
        digitalWrite(stepPin, LOW);
        delayMicroseconds(stepDelay);
      }

      digitalWrite(enPin, HIGH); // Disable motor
      marker = 0.00;
      update_marker();
    } else {
      while (true); // Stop the program
    }
  }
}

void print_EC_data(void) {                             // This function will parse the string  
  char sensorstring_array[30];                         // We make a char array
  char *EC;                                            // Char pointer used in string parsing
  char *TDS;                                           // Char pointer used in string parsing
  char *SAL;                                           // Char pointer used in string parsing
  char *GRAV;                                          // Char pointer used in string parsing
  float f_ec;                                          // Used to hold a floating point number that is the EC

  sensorstring.toCharArray(sensorstring_array, 30);    // Convert the string to a char array 
  EC = strtok(sensorstring_array, ",");                // Parse the array at each comma
  TDS = strtok(NULL, ",");                             // Parse the array at each comma
  SAL = strtok(NULL, ",");                             // Parse the array at each comma
  GRAV = strtok(NULL, ",");                            // Parse the array at each comma

  f_ec = atof(EC);                                     // Convert the char to a float
  
  unsigned long currentTime = millis();                // Get the current time
  float elapsedTime = (currentTime-startTime)/1000.0;  // Calculate elapsed time in seconds
  
  serial_values[0] = elapsedTime;
  serial_values[1] = f_ec;
}

void probe_data(void){
  if (mode == 1) {
    if (myserial1.available() > 0) {                   // If we see that the Atlas Scientific product on port 1 has sent a character
      char inchar = (char)myserial1.read();            // Get the char we just received
      sensorstring += inchar;                          // Add the char to the var called sensorstring
      if (inchar == '\r') {                            // If the incoming character is a <CR>
        sensor_string_complete = true;                 // Set the flag
      }
    }
  } else {
    if (myserial2.available() > 0) {                   // If we see that the Atlas Scientific product on port 2 has sent a character
      char inchar = (char)myserial2.read();            // Get the char we just received
      sensorstring += inchar;                          // Add the char to the var called sensorstring
      if (inchar == '\r') {                            // If the incoming character is a <CR>
        sensor_string_complete = true;                 // Set the flag
      }
    }
  }

  if (sensor_string_complete == true) {                // If a string from the Atlas Scientific product has been received in its entirety
    if (mode == 1) {
      if (isdigit(sensorstring[0]) == false) {         // If the first character in the string is a digit
        Serial.println(sensorstring);                  // Send that string to the PC's serial monitor
      } else {
        mode = not(mode);
        port();
        print_EC_data();                               // Then call this function 
      }
    } else {
      mode = not(mode);
      port();
      float temperature = sensorstring.toFloat();      // Convert the string to a float
      serial_values[2] = temperature;                   
      update_marker();
      print_serial_data();
    }
    sensorstring = "";                                 // Clear the string
    sensor_string_complete = false;                    // Reset the flag used to tell if we have received a completed string from the Atlas Scientific product    
  }
}

void update_marker(void){
  if (prevMarker == 1.00){
    marker = 0.00;
    serial_values[3] = marker;
  } else{
    serial_values[3] = marker;
  }
    prevMarker = marker;
    serial_values[4] = adjusted_ini + (adjusted_tit * n);
    if (n < number_of_times && marker == 1.00){
      n++;
    }
}

void print_serial_data(void) {

  Serial.print(serial_values[0], 2);
  Serial.print(" ");
  Serial.print(serial_values[1], 2);
  Serial.print(" ");
  Serial.print(serial_values[2], 2);
  Serial.print(" ");
  Serial.print(serial_values[3], 2);
  Serial.print(" ");
  Serial.println(serial_values[4], 2);
  
}
