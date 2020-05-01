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
        self.timeout_state = False
        self.x = b''

        self.ser = serial.Serial("/dev/ttyUSB-MT124", baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=0, inter_byte_timeout=0)

        t2 = Thread(target=self.query_mt124, daemon=True)
        t2.start()

    def query_mt124(self):
        message = ([0x48, 0x03, 0x50, 0x55, 0x02, 0x03, 0x4F])
        self.r_time = time.time()
        with open('read_data.csv', 'w') as f:
            file = csv.writer(f)
            file.writerow(["time_interval", "no_of_reads"])

        #if self.ser.inWaiting() == 0:
         #   self.ser.write(message)
            # print("message written")
          #  self.prev = time.time()
        #else:
          #  self.ser.flushInput()
           # self.ser.write(message)

        while True:
            #time.sleep(.1)
            #self.ser.flushInput()
            # print("init")
            #print(len(self.x))
            if len(self.x) == 0:
                #time.sleep(2)
                # print("step1")
                self.ser.write(message)
                #time.sleep(.01)
                while self.ser.inWaiting() == 0:
                    pass
                self.x = self.ser.read(self.ser.inWaiting())
                # print("passed"+str(len(self.x)))
                #time.sleep(.1)
            elif len(self.x) < 8:
                while self.ser.inWaiting() != 0:
                    self.x += self.ser.read(self.ser.inWaiting())
                # print("less than 8...." + str(len(self.x)))

            elif len(self.x) == 8:
                while True:
                    if self.ser.inWaiting() != 0:
                        self.x += self.ser.read(self.ser.inWaiting())
                        #pass
                    else:
                        self.x += self.ser.read(self.ser.inWaiting())
                        # print("step2.." + str(len(self.x)))
                        self.x = b''
                        break

                #self.ser.read(self.ser.inWaiting())
                #self.x = b''

                    #self.ser.read(8)
                    #self.ser.read(8)
                    #self.ser.flushInput()
                #self.ser.write(message)
                    #print("stuck here")
                #print("message written")
                #self.prev = time.time()

            #while self.ser.inWaiting() < 16:
             #   break
                #pass

            #self.prev = time.time()
            elif 8 < len(self.x) < 16:
                #time.sleep(.01)
                while self.ser.inWaiting() != 0:
                    self.x += self.ser.read(self.ser.inWaiting())
                print("GREATER THAN 8...." + str(len(self.x)))

            elif len(self.x) >= 16:
                # time.sleep(1)
                while self.ser.inWaiting() != 0:
                    self.x += self.ser.read(self.ser.inWaiting())
                #self.ser.read(self.ser.inWaiting())

                self.secondary_response = self.x

                if len(self.x) >= 7:
                    if len(self.x) == 7:
                        self.secondary_response = binascii.hexlify(self.secondary_response[6:14]).decode('utf-8')
                        self.secondary_response = ' '.join(self.secondary_response[i:i + 2] for i in range(0, len(self.secondary_response), 2))
                        print(str(len(self.secondary_response)) + "less than 8: " + self.secondary_response)  # . time: " + str(round((time.time() - self.prev), 3)))

                    elif len(self.x) == 8:
                        self.secondary_response = binascii.hexlify(self.secondary_response[0:len(self.secondary_response)]).decode('utf-8')
                        self.secondary_response = ' '.join(self.secondary_response[i:i + 2] for i in range(0, len(self.secondary_response), 2))

                        #self.ser.write(message)
                        #time.sleep(1)
                        #pass

                    elif len(self.x) == 16:
                        # if self.secondary_response[5] == 7:
                        self.secondary_response = binascii.hexlify(self.secondary_response[0:15]).decode('utf-8')
                        self.secondary_response = ' '.join(self.secondary_response[i:i + 2] for i in range(0, len(self.secondary_response), 2))
                        self.time_interval = round((time.time() - self.r_time), 3)
                        self.no_of_reads += 1
                        print(str(self.no_of_reads) + ". " + self.secondary_response + " time: " + str(self.time_interval))
                        with open('read_data.csv', 'a+') as f:
                            file = csv.writer(f)
                            float_list = [self.no_of_reads, self.time_interval]
                            file.writerow(float_list)
                        self.r_time = time.time()
                        self.x = b''
                        #time.sleep(2)
                        #self.ser.write(message)

                        #self.r_time = time.time()

                    elif len(self.x) > 16:
                        self.secondary_response = binascii.hexlify(self.secondary_response[0:15]).decode('utf-8')
                        self.secondary_response = ' '.join(self.secondary_response[i:i + 2] for i in range(0, len(self.secondary_response), 2))
                        #self.time_interval = round((time.time() - self.r_time), 3)
                        #self.no_of_reads += 1
                        print(str(self.no_of_reads) + ". greater than 16: " + self.secondary_response + " time: " + str(self.time_interval))  # . time: " + str(round((time.time() - self.prev), 3)))
                        with open('read_data.csv', 'a+') as f:
                            file = csv.writer(f)
                            float_list = [self.no_of_reads, self.time_interval]
                            file.writerow(float_list)
                        #self.r_time = time.time()
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

            #if self.time_interval > 2.2:
            #    self.ser.flushInput()
            #    self.ser.write(message)

            #self.x = self.ser.read(self.ser.inWaiting())


if __name__ == "__main__":
    ping = Ping()
    while True:
        pass
