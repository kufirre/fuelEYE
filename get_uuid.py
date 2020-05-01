from uuid import getnode as get_mac
import os


def get_uuid():
    mac = get_mac()
    mac_string = ':'.join(("%012X" % mac)[i:i+2] for i in range(0, 12, 2))
    return mac_string


def get_ipaddress():
    ipaddress = os.popen("ifconfig wlan0 \
                       | grep 'inet ' \
                       | awk '{print $2}' \
                       | awk '{print $1}'").read()
    return ipaddress.split('\n')[0]


def get_ssid():
    ssid = os.popen("iwconfig wlan0 \
                    | grep 'ESSID' \
                    | awk '{print $4}' \
                    | awk -F\\\" '{print $2}'").read()
    return ssid.split('\n')[0]


if __name__ == '__main__':
    print(get_uuid())
