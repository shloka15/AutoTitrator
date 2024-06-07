#include <SoftwareSerial.h>

void setup() {
  Serial.begin(9600); // Initialize the serial communication at 9600 baud rate
}

void loop() {
  float value1 = analogRead(A0) * (5.0 / 1023.0); // Example float value 1
  float value2 = analogRead(A1) * (5.0 / 1023.0); // Example float value 2
  unsigned long timestamp = millis(); // Get the current timestamp in milliseconds

  // Send the data in CSV format
  Serial.print(value1);
  Serial.print(",");
  Serial.print(value2);
  Serial.print(",");
  Serial.println(timestamp);

  delay(1000); // Wait for one second
}
