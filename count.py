#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import serial
import serial.tools.list_ports
from multiprocessing import Process

def listen(fd):
    def get_id(fd):
        id = fd.read(id_len)
        return id

    count = dict()
    while True:
        id = get_id(fd)
        if id in count:
            count[id] = count[id] + 1
        else:
            count[id] = 1
        print('\nID为 %s 的小鸡来了 %d 次' % (id, count[id]))

def send_signal(fd, signal):
    fd.write(signal)
    fd.read(status_len)

if __name__ == '__main__':
    id_len = 14
    status_len = 5
    open_signal = b'\x02\x05\x01\xaa\x03'
    close_signal = b'\x02\x05\x02\xaa\x03'

    port_list = list(serial.tools.list_ports.comports())
    count_port = len(port_list)
    if count_port <= 0:
        print('The serial port can\'t find!')
    else:
        for i in range(count_port):
            print('%d. %s' % (i, port_list[i]))
        s = input('Please select one:')
        if (s == ''):
            choice = 0
        else:
            choice = int(s)
        fd = serial.Serial(tuple(port_list[choice])[0], 115200)

        send_signal(fd, open_signal)

        plisten = Process(target=listen, args=(fd, ))
        plisten.start()
        while (input() != 'q'):
            pass
        plisten.terminate()

        send_signal(fd, close_signal)
