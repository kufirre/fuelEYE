import paho.mqtt.client as mqtt
from datetime import datetime
import json

import get_uuid as i_d
import tkinter as tk

import serial
import binascii
import time
import os
import RPi.GPIO as GPIO
import secondary_reader as modbus

# from readerwriterlock import rwlock
from threading import Thread
import threading


# GPIO init
GPIO.setmode(GPIO.BCM)  # GPIO Numbers instead of board numbers
GPIO.setwarnings(False)
RELAY = 26
GPIO.setup(RELAY, GPIO.OUT)  # GPIO Assign mode
GPIO.output(RELAY, GPIO.LOW)


# function for GUI status label
def status(argument1):
    switcher1 = {
        1: "Waiting to scan Mastercard...          ",
        2: "Waiting for volume input...            ",
        3: "Fuel input error                       ",
        4: "Scanned MASTERCARD                     ",
        5: "Server Connection Error                ",
        6: "Connected to Server                    ",
        7: "Tag present                            ",
        8: "Waiting for response from server       ",
        9: "Nozzle reader low power                ",
        10: "No Tag                                ",
        11: "Unregistered Tag                      ",
        12: "Registered Tag                        ",
        13: "Pending Registration                  ",
        14: "Blocked Tag                           ",
        15: "Dispensing                            ",
        16: "Fueling error                         ",
        17: "Fueling complete                      ",
        18: "Waiting to dispense                   ",
        19: "Fueling ended                         ",
        20: "Fueling on going...                   ",
    }
    return switcher1.get(argument1, "Invalid value")


# function for GUI message label
def message(argument2, argument3):
    switcher2 = {
        1: "Use authorized Mastercard to add tag                    ",
        2: "Input Volume                                            ",
        3: f"Volume should be less than or equal to {argument3}     ",
        4: "Tag details uploaded to server                          ",
        5: "Check internet network connectivity                     ",
        6: "Connection successful                                   ",
        7: "Tag read successful                                     ",
        8: "Queried server for tag status                           ",
        9: "Please recharge the nozzle reader battery               ",
        10: "Insert Tag to scan                                     ",
        11: "Scan MASTERCARD to register                            ",
        12: "Tag Authenticated                                      ",
        13: "Contact Admin. to confirm tag                          ",
        14: "Contact Admin. to unblock tag                          ",
        15: "Dispensing fuel. Hold still!                           ",
        16: "Fueling process interrupted; Re-insert nozzle          ",
        17: "Fueling completed successfully                         ",
        18: "Ready to dispense fuel...                              ",
        19: "Fueling ended. Please remove nozzle                    ",
        20: "Dispensing... Please do not shake the nozzle!          ",
    }
    return switcher2.get(argument2, "Invalid value")


# Class for mqtt
class Mqtt:
    def __init__(self):
        self.MQTT_SERVER = "80.241.215.74"
        # self.MQTT_SERVER = "localhost"
        self.MQTT_SUB_TOPIC = "asset_code/check2"
        self.MQTT_PUB_TOPIC = "asset_code/query2"
        self.MQTT_PORT = "1883"
        self.msgs = ''
        self.connectLB = False
        self.connectionFlag = False

        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        # loop here is until connection to MQTT server is established
        while self.connectionFlag is False:
            for x in range(5):
                try:
                    self.client.connect(self.MQTT_SERVER, keepalive=10)
                    print("Connected to server")
                    self.connectionFlag = True
                    break

                except Exception:
                    print("Error in connection")
                    self.connectionFlag = False

        # start the mqtt  listening loop
        self.client.loop_start()

    def conn(self):
        return self.connectionFlag

    # The callback for when the client receives a connect response from the server.
    def on_connect(self, client, userdata, flags, rc):
        self.client = client
        if rc == 0:
            self.connectLB = True
        else:
            self.connectLB = False
        # print("Connected with result code "+str(rc))
        try:
            self.client.subscribe(self.MQTT_SUB_TOPIC, qos=1)
        except Exception:
            # logging.info("error on subscribe" + str(e))
            pass

    # The callback for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, mg):
        self.msgs = mg.payload.decode('utf-8')
        self.client = client
        # print("Topic: " +msg.topic+" "+ "Message:" +str(msg.payload.decode("utf-8")) + " QoS:" + str(msg.qos))

    def on_disconnect(self, client, userdata, rc=0):
        self.client = client
        # logging.debug("DisConnected result code " + str(rc))
        self.client.loop_stop()


# Class for primary card reader
class PrimaryReader:
    def __init__(self):
        self.data = b''
        PORT = "/dev/ttyUSB-primary_reader"
        try:
            self.ser = serial.Serial(port=PORT, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=0)
        except (OSError, serial.SerialException):
            print("Primary reader error. Please plug the card reader and reboot system")

    def auth(self):
        try:
            if self.ser.inWaiting() == 12:
                self.data = self.ser.read(self.ser.inWaiting()).decode('ascii')
                if 'B0CE8F5D' in self.data:
                    print('success')
                    return True
            else:
                return False
            time.sleep(0.01)
        except (OSError, serial.SerialException):
            print("Primary reader error.. Please plug the card reader and reboot system")


# Class for Tkinter
class Main(object):

    def __init__(self, master):

        # Instantiate reader-writer lock
        # marker = rwlock.RWLockFair()

        # for seneca_flag
        self.seneca_flag_lock = threading.RLock()

        # for final_seneca_input
        self.final_seneca_input_lock = threading.RLock()

        # for fuel_timeout_flag
        self.fuel_timeout_flag_lock = threading.RLock()

        # for fuel_timeout_flag2
        self.fuel_timeout_flag2_lock = threading.RLock()

        # for mqtt_auth_flag
        self.mqtt_auth_flag_lock = threading.RLock()

        # for scan_card_flag
        self.scan_card_flag_lock = threading.RLock()

        # for popup_flag
        self.popup_flag_lock = threading.RLock()

        # for self.f
        self.f_lock = threading.RLock()

        # for self.i
        self.i_lock = threading.RLock()

        # for ongoing transaction
        self.ongoing_trans_lock = threading.RLock()

        # for fueling interrupted transaction
        self.intrpt_lock = threading.RLock()

        # for transaction complete
        self.trans_complete_lock = threading.RLock()

        # read the register here
        self.initial_seneca = int(modbus.reads(register=10))
        self.mqtt = Mqtt()

        # for mt124
        self.secondary_response = b''
        self.x = b''
        self.time_interval = 0.00
        self.r_time = 0.00
        self.r_time = time.perf_counter()
        self.ser = serial.Serial("/dev/ttyUSB-MT124", baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=0, inter_byte_timeout=0)
        self.msg = ([0x48, 0x03, 0x50, 0x55, 0x02, 0x03, 0x4F])
        self.no_of_reads = 0

        # flags
        self.tag_registered_flag = False  # flag for show is read tag is registered or not
        self.seneca_flag = False  # flag to activate seneca. remember to set this to False in the main code. This is True only after popup is destroyed
        self.fuel_dispense_flag = False  # flag for checking is fuel is being dispensed or not
        self.fuel_timeout_flag = False  # flag for checking if time has passed without fuel being dispensed
        self.fuel_timeout_flag2 = False
        self.mqtt_auth_flag = False  # flag for querying mqtt
        self.scan_card_flag = False  # flag for scanning the master card
        self.tag_reg = False  # flag for registering a new tag
        self.popup_flag = False  # flag for popup
        self.tag_present = False  # flag to show whether a tag scan is successful
        self.low_power = False  # low power state. use this to test all the other conditions
        self.dest_flag = False  # flag to show that it has entered the print_value function
        self.trans_complete_flag = False  # Flag to show a successful transaction
        self.ongoing_trans_flag = False   # Flag to show ongoing fueling process
        self.intrpt_flag = False

        # variables
        self.present_seneca = 0
        self.present_volume_litre = 0.00
        self.volume_input = 0
        self.final_volume_litre = 0
        self.final_seneca_input = 0
        self.seneca_record_time = 0  # initialize the seneca record time interval here (the time the last_seneca value is recorded)
        self.last_seneca = 0
        self.read_time = 0.00
        self.scan_card_time = 0
        self.popup_time = 0  # popup record time variable
        self.fuel_record_time = 0
        self.fuel_record_time1 = 0
        self.i = False
        self.f = 0  # for statusLB
        self.g = 0  # for messageLB
        self.t = 180  # time in seconds to countdown before shutdown

        self.last_fill_vol = ''
        self.asset_code = ''
        self.rem_Vol = 0.00
        self.alloted_vol = ''
        self.asset_totalizer = 0.00
        self.asset_status = ''
        self.asset_name = ''
        self.rfid = ''
        self.dt = ''

        # constants
        self.KFACTOR = 10  # 74.1
        self.SENECA_RECORD_INTERVAL = 1
        self.SENECA_DIFFERENCE = 1
        self.MAX_SENECA = 4294967296  # max value of the seneca register which is 2^32
        self.FUEL_TIMEOUT = 5  # timeout value is no fuel is dispensed after the first time
        self.SCAN_CARD_TIMEOUT = 3  # timeout for scanning Master card
        self.POPUP_TIMEOUT = 1  # timeout for popup function
        self.READ_TAG_TIMEOUT = 4.5  # timeout after tag read successfully

        # initial tkinter labels
        self.message = 'Starting Application...                    '
        self.communication = 'Awaiting Server Connection           '
        self.status = '                                            '
        self.readerStatus = '                                      '
        self.network = i_d.get_ssid()
        self.entry = 0.00

        self.master = master
        self.master.title('main')
        # self.master.geometry('800x600+0+0')
        self.master.attributes('-fullscreen', True)

        master.after(10, self.start_maincode_thread)
        master.after(10, self.start_popup_thread)
        master.after(10, self.start_mastercard_thread)
        master.after(10, self.start_seneca_thread)
        master.after(10, self.start_nozzle_thread)

        # GUI label variables
        self.volumeLB = tk.StringVar()  # realtime volume to be calculated form the pulse_count instance
        self.readerStatusLB = tk.StringVar()  # reader status to be gotten from Ping() class
        self.tagIDLB = tk.StringVar()  # tag id to be gotten from MT124 class
        self.messageLB = tk.StringVar()  # real-time message label
        self.UIDLB = tk.StringVar()  # the asset name
        self.rem_VolLB = tk.DoubleVar()  # the remainder volume label gotten from the mqtt response
        self.dateTimeLB = tk.StringVar()  # date-time
        self.communicationLB = tk.StringVar()  # communication to mqtt server
        self.statusLB = tk.StringVar()  # status label
        self.networkLB = tk.StringVar()  # WiFi
        self.nozzleReaderLB = tk.IntVar()  # address of the particular nozzle reader
        self.volumeInputLB = tk.IntVar()  # volume input
        self.totalizerLB = tk.DoubleVar()  # totalizer

        # initial labels
        self.messageLB.set(self.message)  # real-time message display/notification
        self.UIDLB.set("Plate No.: %s" % self.asset_name)  # display the asset name which is the plate number
        self.rem_VolLB.set("Rem. Vol.: %.2f" % self.rem_Vol)  # display remaining volume here as received from the mqtt server
        self.volumeLB.set("Volume: %s" % str(self.present_volume_litre))  # remember to make this realtime volume
        self.readerStatusLB.set("Reader Status: %s" % self.readerStatus)  # tag reader
        self.tagIDLB.set("Tag ID: %s" % self.rfid)  # displays the rfid. refresh this when necessary
        self.dateTimeLB.set("Date Time: %s" % self.dt)  # date-time
        self.communicationLB.set("Communication: %s" % self.communication)  # communication status
        self.statusLB.set("Status: %s" % self.status)  # current status
        self.networkLB.set("SSID: %s" % self.network)  # WiFi connected to
        self.nozzleReaderLB.set("Nozzle Reader: 2")  # nozzle reader
        self.volumeInputLB.set("Input Volume: %d" % self.final_volume_litre)  # volume input
        self.totalizerLB.set("Pump totalizer: %.2f" % round(self.asset_totalizer, 2))  # final totalizer

        # the labels now on the gui
        self.l1 = tk.Label(self.master, textvariable=self.messageLB, font=('Piboto Light', 30))
        self.l1.place(x=20, y=8)
        self.l2 = tk.Label(self.master, textvariable=self.volumeLB, font=('Piboto Light', 60))
        self.l2.place(x=20, y=60)
        self.l3 = tk.Label(self.master, textvariable=self.readerStatusLB, font=('Piboto Light', 25))
        self.l3.place(x=20, y=306)
        self.l4 = tk.Label(self.master, textvariable=self.tagIDLB, font=('Piboto Light', 25))
        self.l4.place(x=20, y=360)
        self.l5 = tk.Label(self.master, textvariable=self.UIDLB, font=('Piboto Light', 25))
        self.l5.place(x=20, y=412)
        self.l6 = tk.Label(self.master, textvariable=self.dateTimeLB, font=('Piboto Light', 14))
        self.l6.place(x=20, y=485)
        self.l7 = tk.Label(self.master, textvariable=self.communicationLB, font=('Piboto Light', 14))
        self.l7.place(x=20, y=514)
        self.l8 = tk.Label(self.master, textvariable=self.statusLB, font=('Piboto Light', 14))
        self.l8.place(x=20, y=541)
        self.l1y = tk.Label(self.master, textvariable=self.networkLB, font=('Piboto Light', 25))
        self.l1y.place(x=470, y=402)
        self.l2y = tk.Label(self.master, textvariable=self.nozzleReaderLB, font=('Piboto Light', 14))
        self.l2y.place(x=470, y=465)
        self.l3y = tk.Label(self.master, textvariable=self.volumeInputLB, font=('Piboto Light', 14))
        self.l3y.place(x=470, y=494)
        self.l4y = tk.Label(self.master, textvariable=self.totalizerLB, font=('Piboto Light', 14))
        self.l4y.place(x=470, y=521)
        self.l5y = tk.Label(self.master, textvariable=self.rem_VolLB, font=('Piboto Light', 14))
        self.l5y.place(x=470, y=551)

        self.entry = tk.DoubleVar()
        self.inputField = tk.Entry(self.master, textvariable=self.entry, borderwidth=0, highlightthickness=0, font=('Piboto Light', 55), justify=tk.CENTER, width=6)

    # function for nozzle reader (mt124). This is the only function that should be able to write the state of the nozzle reader (present or not)
    def query_mt124(self):
        self.read_time = time.perf_counter()
        while True:
            if len(self.x) == 0:
                self.ser.write(self.msg)
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
                            # self.rfid = ''
                            # print("nozzle reading failed" + self.rfid)
                            self.r_time = time.perf_counter()
                            self.tag_present = False  # first condition self.tag_present is allowed to be false
                            # return "tag reading failed"
                            # set tag read flag here to be false

                        elif self.x[5] == 10:
                            # print("nozzle reader low power")
                            # print("nozzle reader low power. please recharge" + str(self.fuel_dispense_flag))
                            self.low_power = True

                        self.x = b''
                        break

            elif 8 < len(self.x) < 16:
                while self.ser.inWaiting() != 0:
                    self.x += self.ser.read(self.ser.inWaiting())
                # print("GREATER THAN 8...." + str(len(self.x)))

            elif len(self.x) >= 16:
                while self.ser.inWaiting() != 0:
                    self.x += self.ser.read(self.ser.inWaiting())
                self.secondary_response = self.x

                if len(self.x) == 16:
                    if self.secondary_response[5] == 7:
                        self.secondary_response = binascii.hexlify(self.secondary_response[6:14]).decode('utf-8')
                        self.secondary_response = ' '.join(self.secondary_response[i:i + 2] for i in range(0, len(self.secondary_response), 2))
                        self.rfid = self.secondary_response
                        self.time_interval = round((time.perf_counter() - self.r_time), 3)
                        self.no_of_reads += 1
                        # print(str(self.no_of_reads) + ". " + self.rfid + " time: " + str(self.time_interval))

                        self.r_time = time.perf_counter()

                        if self.low_power is False:
                            with self.f_lock:
                                if self.popup_flag is False:
                                    self.f = 7
                            self.tag_present = True  # only time self.tag_present should be set to True
                            self.read_time = time.perf_counter()
                            # print("__________tag read____________________no query yet")
                            if self.mqtt_auth_flag is False:
                                self.mqtt.msgs = ''
                                query_msgstr = f'{{"asset_code":"{self.rfid}", "title":"check_rfid", "cmd_type":"query"}}'
                                self.mqtt.client.publish(self.mqtt.MQTT_PUB_TOPIC, query_msgstr)

                                # with self.final_seneca_input_lock:
                                self.final_seneca_input = 0
                                self.present_volume_litre = 0.00
                                self.final_volume_litre = 0.00
                                self.fuel_dispense_flag = False

                                print("mqtt authenticated")

                                with self.intrpt_lock:
                                    self.intrpt_flag = False

                                with self.trans_complete_lock:
                                    self.trans_complete_flag = False

                                with self.mqtt_auth_flag_lock:
                                    self.mqtt_auth_flag = True

                                with self.i_lock:
                                    self.i = True

                                with self.popup_flag_lock:
                                    self.popup_flag = False

                                with self.f_lock:
                                    self.f = 8
                                self.communication = "Queried server                          "
                                # print("______________tag read____________query successful:" + str(self.asset_code))

                    self.x = b''

                elif len(self.x) > 16:
                    self.secondary_response = binascii.hexlify(self.secondary_response[0:15]).decode('utf-8')
                    self.secondary_response = ' '.join(self.secondary_response[i:i + 2] for i in range(0, len(self.secondary_response), 2))
                    # print(str(self.no_of_reads) + ". greater than 16: " + self.secondary_response + " time: " + str(self.time_interval))  # . time: " + str(round((time.perf_counter() - self.prev), 3)))

                    self.x = b''

                else:
                    self.secondary_response = binascii.hexlify(self.secondary_response).decode('utf-8')
                    self.secondary_response = ' '.join(self.secondary_response[i:i + 2] for i in range(0, len(self.secondary_response), 2))
                    # print("in the else 1   " + self.secondary_response)
                    self.x = b''

            else:
                self.secondary_response = binascii.hexlify(self.secondary_response[0:15]).decode('utf-8')
                self.secondary_response = ' '.join(self.secondary_response[i:i + 2] for i in range(0, len(self.secondary_response), 2))
                print("in the else 2 and data is:" + self.secondary_response)
                self.x = b''

            if self.tag_present is False and self.low_power is False:
                with self.trans_complete_lock:
                    self.trans_complete_flag = False

                with self.ongoing_trans_lock:
                    self.ongoing_trans_flag = False

            if self.low_power is False and self.popup_flag is False and self.asset_code == self.rfid and self.asset_status == 'registered':
                with self.f_lock:
                    self.f = 12

    # This is the main function to destroy popup
    def print_value(self):
        try:
            self.volume_input = self.entry.get()
            self.final_volume_litre = self.volume_input
        except Exception as e:
            # print("nonsense is happening here---- " + str(type(self.volume_input)) + str(self.volume_input))
            self.volume_input = 0.00
            # with self.excess_lock:
                # self.excess = True
            #pass

        self.inputField.delete(0, 'end')
        self.inputField.destroy()
        self.fuel_record_time1 = int(time.perf_counter())           # set fuel record time here???

        # if the volume input by the user is less than or equal to remaining volume, destroy the popup window. DISPENSE FUEL
        # this should only happen if it has gone through the popup loop at least once
        if 0 < self.volume_input <= self.rem_Vol and self.tag_registered_flag and self.fuel_timeout_flag2 is False:
            with self.seneca_flag_lock:
                self.seneca_flag = True  # this should only be true under this condition
            self.fuel_dispense_flag = True  # this should only be true under this condition
            # print("I'm in line 789 ooooooooooooooo---------" + str(self.volume_input))

        # if the volume input by the user is more than the remaining volume, destroy the popup window
        if 0 < self.volume_input > self.rem_Vol and self.tag_registered_flag or self.volume_input < 0:

            with self.i_lock:
                self.i = True

            with self.seneca_flag_lock:
                self.seneca_flag = False

            # with self.excess_lock:
                # self.excess = True

            self.volume_input = 0.00
            self.final_volume_litre = 0.00
            # print("volume input is too much now")

        else:
            with self.i_lock:
                self.i = False

        # self.dest_flag = True

        with self.popup_flag_lock:
            self.popup_flag = False  # The tag is registered but the value input is more than remaining volume

        # print("popup destroyed; input value: " + str(self.volume_input))

    # popup
    def popup_thread(self):
        while True:
            if self.popup_flag is False and self.low_power is False and self.i and self.tag_registered_flag:
                self.popup_time = int(time.perf_counter())
                self.inputField = tk.Entry(self.master, textvariable=self.entry, borderwidth=0, highlightthickness=0, font=('Piboto Light', 55), justify=tk.CENTER, width=6)
                self.inputField.bind('<KP_Enter>', lambda _: self.print_value())
                self.inputField.delete(0, 'end')
                self.inputField.focus()
                self.inputField.place(x=20, y=170, height=70)
                # self.dest_flag = False

                with self.f_lock:
                    self.f = 2

                with self.popup_flag_lock:
                    self.popup_flag = True
                    # print("in the popup function now")

            # so that the popup lasts only until the timeout, after which it is being destroyed
            if int(time.perf_counter()) - self.popup_time >= self.POPUP_TIMEOUT and self.popup_flag and self.tag_present is False:
                try:
                    self.inputField.delete(0, 'end')
                    self.inputField.destroy()

                except Exception:
                    pass

                with self.i_lock:
                    self.i = False

                with self.popup_flag_lock:
                    self.popup_flag = False

                # print("popup destroyed; input value: " + str(self.volume_input))

    # scan card reader
    def scan_mastercard(self):
        reader = PrimaryReader()
        while True:
            if self.scan_card_flag and self.low_power is False:
                self.scan_card_time = int(time.perf_counter())
                while int(time.perf_counter()) - self.scan_card_time <= self.SCAN_CARD_TIMEOUT:
                    with self.f_lock:
                        self.f = 1
                    self.tag_reg = reader.auth()
                    # print("scan master card to add new rfid tag")
                    if self.tag_reg:  # if the master card is scanned
                        # update details to mqtt
                        add_rfid_msgstr = f'{{"asset_code":"{self.rfid}", "asset_fuel_type":"diesel", "alloted_vol":"0.00", "used_vol":"0.00", "last_fill_vol":"0.00", "asset_totalizer":"0", "status":"pending", "title":"add_rfid", "cmd_type":"query"}}'
                        self.mqtt.client.publish(self.mqtt.MQTT_PUB_TOPIC, add_rfid_msgstr)
                        self.communication = "Data upload successful                                "
                        self.scan_card_flag = False
                        # print("scan successful_______________rfid tag add request successfully sent")

                        with self.f_lock:
                            self.f = 4
                        break
                    if self.tag_present is False:
                        with self.scan_card_flag_lock:
                            self.scan_card_flag = False
                        break
                # print("broken out of scan Mastercard while loop")

    def seneca(self):
        while True:
            # there should always be the flag for tag reading before activating the relay
            # seneca flag is True only after popup is destroyed
            # seneca_code_time = time.perf_counter()

            if not self.seneca_flag and self.low_power is False:  # if the seneca flag is False. This is the default state.  It is set true after volume has been input before relay is activated
                try:
                    self.initial_seneca = int(modbus.reads(register=10))  # read the register here
                    # if fuel is not being dispensed and the initial seneca reading is approaching the max value of the seneca register which is 2^32
                    if self.MAX_SENECA - self.initial_seneca <= 100000:
                        modbus.writes()
                        # print("seneca value reset")
                except ValueError:
                    print("modbus error. check the SENECA module")

            # if one second passes, record the last seneca reading
            if time.perf_counter() - self.seneca_record_time >= self.SENECA_RECORD_INTERVAL:
                self.last_seneca = self.present_seneca
                self.seneca_record_time = time.perf_counter()  # reset the seneca record time here
                # print("seneca time recorded: " + str(self.seneca_record_time))

            if self.fuel_dispense_flag:

                with self.final_seneca_input_lock:
                    # formulas for calculating present volume in litre and final seneca value desired
                    self.final_seneca_input = (self.final_volume_litre * self.KFACTOR) + self.initial_seneca  # convert the volume in litres to SENECA counts

                # changed this in dfgmdmk;dkl;kdf;glnkl;h'j;ldgkh'ldjfhgjdf;'
                if not self.intrpt_flag:
                    self.present_volume_litre = (self.present_seneca - self.initial_seneca) / self.KFACTOR  # convert the current SENECA register count/value to realtime volume for GUI

                if self.tag_registered_flag:
                    try:
                        self.present_seneca = int(modbus.reads(register=10))  # read the realtime register value of SENECA here
                        # print("About to begin fueling. presentCount: " + str(self.present_seneca) + " Volume: " + str(self.present_volume_litre))
                    except ValueError:
                        print("modbus error. check the SENECA module")

                if self.present_seneca - self.last_seneca > self.SENECA_DIFFERENCE:
                    self.fuel_record_time = int(time.perf_counter())
                    self.ongoing_trans_flag = True
                    # print("fuel_record_time:"+str(self.fuel_record_time))

                # if the present seneca reading minus the last seneca reading is less than 100, then turn off the relay and reset parameters
                elif self.present_seneca - self.last_seneca < self.SENECA_DIFFERENCE and self.fuel_timeout_flag2:

                    with self.ongoing_trans_lock:
                        self.ongoing_trans_flag = False

                    with self.intrpt_lock:
                        self.intrpt_flag = True

                    with self.seneca_flag_lock:
                        self.seneca_flag = False
                        # print("FUELING INTERRUPTED: present seneca - last seneca is less than  seneca difference....")
                        # self.fuel_dispense_flag = False
                        GPIO.output(RELAY, GPIO.LOW)

                    # update the server here
                    msg_str = f'{{"asset_code":"{self.rfid}", "used_vol":"{self.rem_Vol}", "pump_id":"002", "fill_qty":"{str(round(self.present_volume_litre, 2))}", "status":"completed", "trnx_dt_time":"{self.dt}", "title":"asset_trnx", "cmd_type":"query"}}'
                    if 0 < self.present_volume_litre < self.rem_Vol:
                        self.mqtt.client.publish(self.mqtt.MQTT_PUB_TOPIC, msg_str)
                        self.communication = "Data upload successful                                 "

                    # print("fueling interrupted: current time is" + str(int(time.perf_counter())) + "while previous time was" + str(self.seneca_record_time))

                # the process times-out if after a value is input in the popup and popup is destroyed, no fuel is dispensed
                # remember to set the fuel record time just after the popup is destroyed; do this: self.fuel_record_time = int(time.perf_counter())
                if int(time.perf_counter()) - self.fuel_record_time1 >= self.FUEL_TIMEOUT:
                    # print("------------------------------------TIMEOUT 1 HAPPENED HERE---------------------------")

                    with self.fuel_timeout_flag_lock:
                        self.fuel_timeout_flag = True
                        # print("present seneca:"+str(self.present_seneca) + "last seneca:" + str(self.last_seneca) + "time diff: " + str(int(time.perf_counter() - self.seneca_record_time)))
                    if self.present_seneca - self.last_seneca < self.SENECA_DIFFERENCE and time.perf_counter() - self.seneca_record_time > 0.7:

                        with self.fuel_timeout_flag2_lock:
                            self.fuel_timeout_flag2 = True
                        msg_str2 = f'{{"asset_code":"{self.rfid}", "used_vol":"{self.rem_Vol}", "pump_id":"002", "fill_qty":"{str(round(self.present_volume_litre, 2))}", "status":"completed", "trnx_dt_time":"{self.dt}", "title":"asset_trnx", "cmd_type":"query"}}'
                        if 0 < self.present_volume_litre < self.rem_Vol:
                            self.mqtt.client.publish(self.mqtt.MQTT_PUB_TOPIC, msg_str2)
                            self.communication = "Data upload successful                                 "

                        with self.seneca_flag_lock:
                            self.seneca_flag = False

                        with self.intrpt_lock:
                            self.intrpt_flag = True

                        # print("------------------------------------TIMEOUT 2 HAPPENED HERE---------------------------present seneca:"+str(self.present_seneca) + "last seneca:" + str(self.last_seneca))

                # if the fueling has completed successfully
                if self.present_seneca >= self.final_seneca_input and self.final_volume_litre > 0:
                    # print("fueling completed successfully")
                    GPIO.output(RELAY, GPIO.LOW)
                    self.fuel_dispense_flag = False

                    # with self.final_seneca_input_lock:
                    self.present_volume_litre = self.final_volume_litre

                    with self.trans_complete_lock:
                        self.trans_complete_flag = True

                    with self.ongoing_trans_lock:
                        self.ongoing_trans_flag = False

                    # update the mqtt server here
                    if 0 < self.present_volume_litre < self.rem_Vol:
                        msg_str = f'{{"asset_code":"{self.rfid}", "used_vol":"{round(self.rem_Vol - self.final_volume_litre, 2)}", "pump_id":"002", "fill_qty":"{round(self.final_volume_litre, 2)}", "status":"completed", "trnx_dt_time":"{self.dt}", "title":"asset_trnx", "cmd_type":"query"}}'
                        self.mqtt.client.publish(self.mqtt.MQTT_PUB_TOPIC, msg_str)  # update data to the server after the fueling process
                        self.communication = "Data upload successful                                                 "

                    with self.seneca_flag_lock:
                        self.seneca_flag = False

            # print("seneca code time -----------" + str(time.perf_counter() - seneca_code_time))

    # Functions for starting THREADS
    def start_seneca_thread(self):
        t1 = Thread(target=self.seneca, daemon=True, name="seneca_thread")
        t1.start()

    # thread for Mastercard
    def start_mastercard_thread(self):
        t2 = Thread(target=self.scan_mastercard, daemon=True, name="mastercard_thread")
        t2.start()

    # thread for maincode
    def start_maincode_thread(self):
        t3 = Thread(target=self.maincode, daemon=True, name="maincode_thread")
        t3.start()

    # thread for popup
    def start_popup_thread(self):
        t4 = Thread(target=self.popup_thread, daemon=True, name="popup_thread")
        t4.start()

    # thread for nozzle reader
    def start_nozzle_thread(self):
        t5 = Thread(target=self.query_mt124, daemon=True, name="nozzle_reader_thread")
        t5.start()

    def maincode(self):
        v = 0
        while True:

            # code_time = time.perf_counter()

            self.dt = datetime.now().replace(microsecond=0)

            # check if the system is connected to mqtt server to update the GUI labels
            if self.mqtt.conn() is False and self.low_power is False:
                with self.f_lock:
                    self.f = 5
                self.communication = "Server Connection Error                            "
            elif self.mqtt.conn() and self.low_power is False:
                if v == 0:
                    with self.f_lock:
                        self.f = 6
                        self.communication = "Connected to Server                        "
                    v += 1

            # get mqtt message and decode it
            if self.mqtt_auth_flag:
                try:
                    z = json.loads(self.mqtt.msgs)
                    self.communication = 'Received data packets from server               '
                    self.asset_status = z['status']
                    self.asset_code = z['asset_code']

                    try:
                        self.last_fill_vol = z['last_fill_vol']
                        self.asset_totalizer = float(z['asset_totalizer'])
                        self.asset_name = z['asset_name']
                        self.alloted_vol = z['alloted_vol']
                        self.rem_Vol = float(z['alloted_vol']) - float(z['used_vol'])  # Just added this

                    except KeyError:
                        pass

                except Exception:
                    pass

            # if the nozzle reader battery is  low and there's no tag present. shutdown the pi
            if self.low_power and not self.fuel_dispense_flag:
                self.message = "Recharge nozzle reader and restart system                      "
                self.status = "Nozzle reader low power                                         "
                self.readerStatus = "NOZZLE READER LOW POWER                                   "  # display auth failed
                self.communication = "No data available                                "
                with self.f_lock:
                    self.f = 9

                while self.t:
                    self.dt = datetime.now().replace(microsecond=0)
                    mins, secs = divmod(self.t, 60)
                    time_format = 'Shutting down in ' + '{:02d}:{:02d}'.format(mins, secs)
                    self.status = "%s                                         " % str(time_format)
                    time.sleep(1)
                    self.t -= 1
                    self.messageLB.set(self.message)  # real-time message display/notification
                    self.readerStatusLB.set("Reader Status: %s" % self.readerStatus)  # tag reader
                    self.dateTimeLB.set("Date Time: %s" % self.dt)  # date-time
                    self.communicationLB.set("Communication: %s" % self.communication)  # communication status
                    self.statusLB.set("Status: %s" % self.status)  # current status

                    if self.t == 0:
                        print('Goodbye!\n\n\n\n\n')
                        os.system("sudo shutdown -h now")  # command to shutdown the system

            elif self.low_power is False:

                if self.tag_present is False:

                    # msg_str = f'{{"asset_code":"{self.rfid}", "pump_id":"002", "fill_qty":"{round(self.final_volume_litre, 2)}", "status":"completed", "trnx_dt_time":"{self.dt}", "title":"asset_trnx", "cmd_type":"query"}}'
                    if 0 < self.present_volume_litre < self.rem_Vol and self.fuel_dispense_flag and self.intrpt_flag:
                        msg_str5 = f'{{"asset_code":"{self.rfid}", "used_vol":"{round(self.rem_Vol - self.present_volume_litre, 2)}", "pump_id":"002", "fill_qty":"{str(round(self.present_volume_litre, 2))}", "status":"completed", "trnx_dt_time":"{self.dt}", "title":"asset_trnx", "cmd_type":"query"}}'
                        self.mqtt.client.publish(self.mqtt.MQTT_PUB_TOPIC, msg_str5)
                        self.communication = "Data upload successful                                 "
                        self.f = 3

                    # the interrupted mqtt should be here and not in the timeout
                    self.rfid = ''
                    self.tag_registered_flag = False
                    self.fuel_dispense_flag = False

                    with self.fuel_timeout_flag_lock:
                        self.fuel_timeout_flag = False

                    with self.fuel_timeout_flag2_lock:
                        self.fuel_timeout_flag2 = False

                    with self.seneca_flag_lock:
                        self.seneca_flag = False

                    with self.mqtt_auth_flag_lock:
                        self.mqtt_auth_flag = False  # need to re-authenticate mqtt

                    self.readerStatus = "No Tag                                            "  # display auth failed
                    self.communication = "No data available                                "
                    self.last_fill_vol = ''
                    self.asset_code = ''
                    self.rem_Vol = 0.00
                    self.alloted_vol = ''
                    self.asset_totalizer = 0.00
                    self.asset_status = ''
                    self.asset_name = ''
                    # print("no tag oooo--------------------------")

                # if a card is scanned and status is unregistered
                if self.asset_status == 'unregistered':
                    with self.scan_card_flag_lock:
                        self.scan_card_flag = True

                    with self.f_lock:
                        self.f = 11

                elif self.asset_status == 'pending':
                    with self.f_lock:
                        self.f = 13

                elif self.asset_status == 'blocked':
                    with self.f_lock:
                        self.f = 14

                # if a card is scanned and the status is registered
                if self.asset_code == self.rfid and self.asset_status == 'registered':
                    self.readerStatus = "Auth OK                             "  # display auth ok
                    self.tag_registered_flag = True

                    # after registered card is found, check if the rem_vol > 0
                    if self.rem_Vol > 0 and self.dest_flag is False and self.i is False:
                        with self.popup_flag_lock:
                            self.popup_flag = False

                # if the volume input by the user is more than the remaining volume, destroy the popup window
                elif 0 < self.volume_input > self.rem_Vol and self.tag_registered_flag:
                    with self.popup_flag_lock:
                        self.popup_flag = False  # The tag is registered but the value input is more than remaining volume

                    with self.i_lock:
                        self.i = True

                    with self.seneca_flag_lock:
                        self.seneca_flag = False

                    with self.f_lock:
                        self.f = 3

                    self.volume_input = 0
                    self.final_volume_litre = 0
                    print("volume input is too much now")

                if (time.perf_counter() - self.read_time) > self.READ_TAG_TIMEOUT:
                    self.tag_registered_flag = False
                    self.tag_present = False  # second condition self.tag_present is allowed to be False

                    with self.seneca_flag_lock:
                        self.seneca_flag = False

                    if 0 < self.present_volume_litre < self.rem_Vol and self.fuel_dispense_flag:
                        msg_str = f'{{"asset_code":"{self.rfid}", "used_vol":"{self.rem_Vol}", "pump_id":"002", "fill_qty":"{str(round(self.present_volume_litre, 2))}", "status":"completed", "trnx_dt_time":"{self.dt}", "title":"asset_trnx", "cmd_type":"query"}}'
                        self.mqtt.client.publish(self.mqtt.MQTT_PUB_TOPIC, msg_str)
                        self.communication = "Data upload successful                                 "
                    # print("time elapsed without authentication. diff: " + str(time.perf_counter() - self.read_time))

                if self.fuel_dispense_flag and self.fuel_timeout_flag2 is False:
                    GPIO.output(RELAY, GPIO.HIGH)
                    # print("______________dispensing fuel.............")

                elif self.fuel_dispense_flag is False:
                    GPIO.output(RELAY, GPIO.LOW)

                if self.intrpt_flag is False and self.tag_present is False:
                    with self.f_lock:
                        self.f = 10

                elif self.intrpt_flag:
                    with self.f_lock:
                        self.f = 16

                elif self.fuel_dispense_flag and self.ongoing_trans_flag is False:
                    with self.f_lock:
                        self.f = 18
                        self.communication = "                                                  "

                elif self.trans_complete_flag and self.tag_present:
                    with self.f_lock:
                        self.f = 19

                elif self.trans_complete_flag is False and self.ongoing_trans_flag:
                    with self.f_lock:
                        self.f = 20

            self.message = message(self.f, self.rem_Vol)
            self.status = status(self.f)

            self.messageLB.set(self.message)  # real-time message display/notification
            self.UIDLB.set("Plate No.: %s" % self.asset_name)  # display the asset name which is the plate number
            self.rem_VolLB.set("Rem. Vol.: %.2f" % self.rem_Vol)  # display remaining volume here as received from the mqtt server
            self.volumeLB.set(f"Volume: {str(round(self.present_volume_litre, 2))}")  # remember to make this realtime volume
            self.readerStatusLB.set("Reader Status: %s" % self.readerStatus)  # tag reader
            self.tagIDLB.set("Tag ID: %s" % self.rfid)  # displays the rfid. refresh this when necessary
            self.dateTimeLB.set("Date Time: %s" % self.dt)  # date-time
            self.communicationLB.set("Communication: %s" % self.communication)  # communication status
            self.statusLB.set("Status: %s" % self.status)  # current status
            self.nozzleReaderLB.set("Nozzle Reader: 2")  # nozzle reader
            self.volumeInputLB.set(f"Input Volume: {round(self.final_volume_litre, 2)}")  # volume input
            self.totalizerLB.set("Pump totalizer: %.2f" % round(self.asset_totalizer, 2))  # final totalizer

            # print("code time is --------------------------------- " + str(time.perf_counter() - code_time))


if __name__ == "__main__":
    root = tk.Tk()
    app = Main(root)
    root.mainloop()
