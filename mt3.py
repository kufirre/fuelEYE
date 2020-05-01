import serial
import binascii
import time


from threading import Thread


class Ping:

    def __init__(self):

        self.secondary_response = b''
        self.rfid = ''

        self.no_of_reads = 0
        self.time_interval = 0.00
        self.r_time = 0.00

        self.x = b''

        self.ser = serial.Serial("/dev/ttyUSB-MT124", baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=0, inter_byte_timeout=0)

        t1 = Thread(target=self.query_mt124, daemon=True)
        t1.start()

    def query_mt124(self):
        message = ([0x48, 0x03, 0x50, 0x55, 0x02, 0x03, 0x4F])
        self.r_time = time.time()

        while True:

            if len(self.x) == 0:
                self.ser.write(message)
                while self.ser.inWaiting() == 0:
                    pass
                self.x = self.ser.read(self.ser.inWaiting())

            elif len(self.x) < 8:
                while self.ser.inWaiting() != 0:
                    self.x += self.ser.read(self.ser.inWaiting())

            elif len(self.x) == 8:
                while True:
                    if self.ser.inWaiting() != 0:
                        self.x += self.ser.read(self.ser.inWaiting())
                    else:
                        self.x += self.ser.read(self.ser.inWaiting())
                        if self.x[5] == 6:
                            self.rfid = ''
                            print("nozzle reading failed" + self.rfid)
                            self.r_time = time.time()
                            # set tag read flag here to be false

                        elif self.x[5] == 10:
                            print("nozzle reader low power")

                        self.x = b''
                        break

            elif 8 < len(self.x) < 16:
                while self.ser.inWaiting() != 0:
                    self.x += self.ser.read(self.ser.inWaiting())
                print("GREATER THAN 8...." + str(len(self.x)))

            elif len(self.x) >= 16:
                while self.ser.inWaiting() != 0:
                    self.x += self.ser.read(self.ser.inWaiting())
                self.secondary_response = self.x

                if len(self.x) == 16:
                    if self.secondary_response[5] == 7:
                        self.secondary_response = binascii.hexlify(self.secondary_response[6:14]).decode('utf-8')
                        self.secondary_response = ' '.join(self.secondary_response[i:i + 2] for i in range(0, len(self.secondary_response), 2))
                        self.rfid = self.secondary_response
                        self.time_interval = round((time.time() - self.r_time), 3)
                        self.no_of_reads += 1
                        print(str(self.no_of_reads) + ". " + self.rfid + " time: " + str(self.time_interval) + str(len(self.rfid)))

                        self.r_time = time.time()
                    self.x = b''

                elif len(self.x) > 16:
                    self.secondary_response = binascii.hexlify(self.secondary_response[0:15]).decode('utf-8')
                    self.secondary_response = ' '.join(self.secondary_response[i:i + 2] for i in range(0, len(self.secondary_response), 2))
                    print(str(self.no_of_reads) + ". greater than 16: " + self.secondary_response + " time: " + str(self.time_interval))  # . time: " + str(round((time.time() - self.prev), 3)))

                    self.x = b''

                else:
                    self.secondary_response = binascii.hexlify(self.secondary_response).decode('utf-8')
                    self.secondary_response = ' '.join(self.secondary_response[i:i + 2] for i in range(0, len(self.secondary_response), 2))
                    print("in the else 1   " + self.secondary_response)
                    self.x = b''

            else:
                self.secondary_response = binascii.hexlify(self.secondary_response[0:15]).decode('utf-8')
                self.secondary_response = ' '.join(self.secondary_response[i:i + 2] for i in range(0, len(self.secondary_response), 2))
                print("in the else 2 and data is:" + self.secondary_response)
                self.x = b''


if __name__ == "__main__":
    ping = Ping()
    while True:
        pass
