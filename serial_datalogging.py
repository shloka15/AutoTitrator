import serial
import time

serial_port = 'COM3'  # Replace with actual COM port
baud_rate = 9600

# Open the serial connection
ser = serial.Serial(serial_port, baud_rate, timeout=1)

# Open the file in append mode
with open('data.txt', 'a') as file:
    while True:
        line = ser.readline().decode('utf-8').strip()
        
        if line:
            #print(line)
            
            file.write(line + '\n')
            
            file.flush()

# Close the serial connection (not typically reached in this infinite loop)
ser.close()
