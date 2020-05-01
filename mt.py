import serial
import binascii
import time
import csv

from threading import Thread


class Ping:

    def __init__(self):

        self.secondary_response = b''
        self.rsp = b''
        self.result = ''
        self.rfid = ''
        self.no_of_reads = 0
        self.time_interval = 0.00

        self.r_time = 0.00
        self.prev = 0

        self.write_state = False
        self.x = 0

        self.ser = serial.Serial("/dev/ttyUSB-MT124", baudrate=115200)

        # t1 = Thread(target=self.read_response, daemon=True)
        # t1.start()

        t2 = Thread(target=self.query_mt124, daemon=True)
        t2.start()

    def query_mt124(self):
        message = ([0x48, 0x03, 0x50, 0x55, 0x02, 0x03, 0x4F])
        self.r_time = time.time()
        with open('read_data.csv', 'w') as f:
            file = csv.writer(f)
            file.writerow(["time_interval", "no_of_reads"])

        while True:
            if self.ser.inWaiting() < 7:
                self.ser.write(message)
                time.sleep(.01)
                #print("message written")
            self.prev = time.time()

            while self.ser.inWaiting() == 0:
                #print("waiting  for data.   " + str(self.ser.inWaiting()))
                pass

            #print("time_elapsed = " + str(round((time.time() - self.prev), 2)))
            # time.sleep(1)
            self.prev = time.time()

            if self.ser.inWaiting() >= 7:
                if self.ser.inWaiting() == 7:
                    self.secondary_response = self.ser.read(size=self.ser.inWaiting())
                    self.secondary_response = binascii.hexlify(self.secondary_response[6:14]).decode('utf-8')
                    self.secondary_response = ' '.join(self.secondary_response[i:i + 2] for i in range(0, len(self.secondary_response), 2))
                    print(str(len(self.secondary_response)) + "less than 8: " + self.secondary_response)  # . time: " + str(round((time.time() - self.prev), 3)))
                    #self.ser.flushInput()
                    # time.sleep(1)

                elif self.ser.inWaiting() == 8:
                    #message = ([0x48, 0x03, 0x50, 0x55, 0x02, 0x03, 0x4F])
                    #self.ser.write(message)
                    self.secondary_response = self.ser.read(size=self.ser.inWaiting())
                    self.secondary_response = binascii.hexlify(self.secondary_response[0:len(self.secondary_response)]).decode('utf-8')
                    self.secondary_response = ' '.join(self.secondary_response[i:i + 2] for i in range(0, len(self.secondary_response), 2))
                    #print(self.secondary_response)
                    #self.ser.flushInput()
                    #time.sleep(1)

                elif self.ser.inWaiting() == 16:
                    self.secondary_response = self.ser.read(size=self.ser.inWaiting())
                    if self.secondary_response[5] == 7:
                        self.secondary_response = binascii.hexlify(self.secondary_response[0:15]).decode('utf-8')
                        self.secondary_response = ' '.join(self.secondary_response[i:i + 2] for i in range(0, len(self.secondary_response), 2))
                        self.time_interval = round((time.time() - self.r_time), 3)
                        self.no_of_reads += 1
                        print(str(self.no_of_reads) + ". " + self.secondary_response + " time: " + str(self.time_interval))
                        #self.ser.flushInput()
                        with open('read_data.csv', 'a+') as f:
                            file = csv.writer(f)
                            float_list = [self.no_of_reads, self.time_interval]
                            file.writerow(float_list)
                        #time.sleep(1)
                        self.r_time = time.time()

                elif self.ser.inWaiting() > 16:
                    self.secondary_response = self.ser.read(size=self.ser.inWaiting())
                    self.secondary_response = binascii.hexlify(self.secondary_response[0:15]).decode('utf-8')
                    self.secondary_response = ' '.join(self.secondary_response[i:i + 2] for i in range(0, len(self.secondary_response), 2))
                    self.time_interval = round((time.time() - self.r_time), 3)
                    self.no_of_reads += 1
                    print(str(self.no_of_reads) + ". greater than 16: " + self.secondary_response)  # . time: " + str(round((time.time() - self.prev), 3)))
                    #self.ser.flushInput()
                    # time.sleep(1)
                    with open('read_data.csv', 'a+') as f:
                        file = csv.writer(f)
                        float_list = [self.no_of_reads, self.time_interval]
                        file.writerow(float_list)
                    self.r_time = time.time()

                else:
                    # self.ser.flushInput()
                    # x = ''
                    # x = self.ser.inWaiting(size=self.ser.inWaiting())
                    print("in the else 1")

            else:
                print("in the else 2")  # and data is:" + str(self.ser.inWaiting()))
                # self.ser.flushInput()


if __name__ == "__main__":
    ping = Ping()
    while True:
        # ping.query_mt124()
        pass
