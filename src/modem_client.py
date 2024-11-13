import binascii
import time
import traceback
import logging
import serial
from attila.atre import ATRuntimeEnvironment
from attila.exceptions import ATSerialPortError, ATRuntimeError

class ModemClient():
    def __init__(self, serial_port: str, baud_rate: int, default_timeout, line_break):
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.default_timeout = default_timeout
        self.line_break = line_break
        self.serial = None
        if not self.enter_command_mode():
            raise ATRuntimeError("Failed to enter command mode")
    
    def send(self, command: str):
        """Send AT command and return response"""
        try:
            if self.serial is None or not self.serial.is_open:
                self.serial = serial.Serial(
                    self.serial_port,
                    self.baud_rate,
                    timeout=self.default_timeout
                )
            
            # Clear any pending data
            self.serial.reset_input_buffer()
            
            # Send command with proper line ending
            full_command = f"{command}\r\n"
            logging.debug(f"Sending command: {full_command!r}")
            self.serial.write(full_command.encode())
            self.serial.flush()
            
            # Read response with timeout
            response = []
            start_time = time.time()
            
            while (time.time() - start_time) < self.default_timeout:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode().strip()
                    logging.debug(f"Received line: {line!r}")
                    
                    # Skip echo of command
                    if line == command:
                        continue
                        
                    response.append(line)
                    
                    # If we get OK or ERROR, we're done
                    if line in ['OK', 'ERROR']:
                        break
                        
                time.sleep(0.1)
            
            # Join all lines except the last OK/ERROR
            if response:
                return '\n'.join(response)
            
            return ''
            
        except serial.SerialException as e:
            logging.error(f"Serial port error: {e}")
            raise ATSerialPortError(str(e))
        except Exception as e:
            logging.error(f"Error executing command: {command}")
            logging.debug(traceback.format_exc())
            raise ATRuntimeError(str(e))

    def enter_command_mode(self, max_attempts=3):
        """Enter AT command mode using DTR control"""
        print("Switching modem to command mode...")
        for attempt in range(max_attempts):
            logging.debug(f"Attempt {attempt + 1} to enter command mode")
            try:
                with serial.Serial(self.serial_port, self.baud_rate, timeout=2) as ser:
               
                    
                    # Clear buffers
                    ser.reset_input_buffer()
                    ser.reset_output_buffer()
                    
                    ser.write("+++".encode())
                    time.sleep(1)
                    # Send test command multiple times
                    for _ in range(3):  # Try sending AT command multiple times
                        #idk why but this never works on attempt 1 so i do it 3 times
                        logging.debug("Sending test AT command")
                        ser.write(b'AT\r\n')
                        ser.flush()
                        time.sleep(0.5)  # Wait between attempts
                    
                    # Read response with longer timeout
                    response = b''
                    start = time.time()
                    while (time.time() - start) < 3.0:  # Increased from 1.0s
                        if ser.in_waiting:
                            chunk = ser.read(ser.in_waiting)
                            logging.debug(f"Received chunk: {chunk!r}")
                            response += chunk
                            if b'OK' in response or b'RFD SiK' in response:
                                print("Successfully entered command mode.")
                                self.serial = ser
                                return True
                        time.sleep(0.1)
                    
                    logging.debug(f"Full response: {response!r}")
                    
            except serial.SerialException as e:
                logging.error(f"Serial port error: {e}")
                continue
            
            time.sleep(2.0)  # Increased delay between attempts
        
        logging.error(f"Failed to enter command mode after {max_attempts} attempts")
        return False

    def close(self):
        """Close the serial connection"""
        if self.serial and self.serial.is_open:
            self.serial.close()