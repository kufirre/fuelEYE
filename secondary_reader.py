import serial
import modbus_tk
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu
import time


PORT1 = "/dev/ttyUSB-pulse_counter"
cmd_read = cst.READ_HOLDING_REGISTERS
cmd_write = cst.WRITE_SINGLE_REGISTER

try:
    master = modbus_rtu.RtuMaster(serial.Serial(port=PORT1, baudrate=38400, bytesize=8, parity='N', stopbits=1, xonxoff=0))
    master.set_timeout(5.0)
    master.set_verbose(True)
except modbus_tk.modbus.ModbusError:
    print("modbus error")
except modbus_tk.modbus_rtu.ModbusInvalidResponseError:
    print("modbus error")


def reads(slave_address=1,  register=10, register_count=1):
    result = None
    try:
        result = master.execute(slave_address, cmd_read, register, register_count)
    except modbus_tk.modbus.ModbusError:
        print("modbus error")
    except modbus_tk.modbus_rtu.ModbusInvalidResponseError:
        print("modbus error")
    if register_count == 1:
        result = str(result)
        result = result.rstrip(",)")
        result = result.lstrip("(")
    return result


def writes(slave_address=1, register=4, value=0):
    try:
        master.execute(slave_address, cmd_write, register, value)
        print("pulse counter register reset successful!")
    except modbus_tk.modbus.ModbusError:
        print("modbus error")
    except modbus_tk.modbus_rtu.ModbusInvalidResponseError:
        print("modbus error")


if __name__ == "__main__":
    while True:
        print(reads(register=10))
        time.sleep(1)
