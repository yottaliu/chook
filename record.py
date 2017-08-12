#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import serial
import serial.tools.list_ports
from multiprocessing import Process
import sqlite3
from datetime import datetime

def listen(fd, conn):
    def get_id(fd):
        id = fd.read(id_len)
        return id

    class Chook(object):
        def __init__(self, name, start, end, k):
            self.name = name
            self.start = start
            self.end = end
            self.k = k

    cursor = conn.cursor()
    cursor.execute('select id, name from chooks');
    chooks = cursor.fetchall()
    cursor.close()

    chook_dict = dict()
    for id, name in chooks:
        chook = Chook(name, 0, 0, 0)
        chook_dict[id] = chook

    while True:
        cursor = conn.cursor()
        id = get_id(fd)
        cursor.execute('select id from chooks where id=?', (id, ))
        if cursor.fetchall() == []:
            name = '无名侠'
            chook = Chook(name, 0, 0, 0)
            chook_dict[id] = chook
            cursor.execute('insert into chooks (id, name) values (?, ?)', (id, name))
        chook_dict[id].start = chook_dict[id].end
        chook_dict[id].end = datetime.now().timestamp()
        if chook_dict[id].end - chook_dict[id].start < cell * (2**chook_dict[id].k):
            cursor.execute('update records set end=? where id=? and end=?', (chook_dict[id].end, id, chook_dict[id].start))
            if chook_dict[id].k < n:
                chook_dict[id].k += 1
            print('"%s"还在这儿，上次记录时间是 \t%s' % (chook_dict[id].name, datetime.fromtimestamp(chook_dict[id].start)))
        else:
            chook_dict[id].start = chook_dict[id].end
            cursor.execute('insert into records (id, start, end) values (?, ?, ?)', (id, chook_dict[id].start, chook_dict[id].end))
            chook_dict[id].k = 0
            print('"%s"来了，现在时间是 \t\t%s' % (chook_dict[id].name, datetime.fromtimestamp(chook_dict[id].start)))
        cursor.close()
        conn.commit()

def read_records(conn):
    cursor = conn.cursor()
    cursor.execute('select name, start, end from chooks, records where chooks.id=records.id');
    records = cursor.fetchall()
    cursor.close()
    for rec in records:
        print('%s: from %s to %s' % (rec[0], datetime.fromtimestamp(rec[1]), datetime.fromtimestamp(rec[2])))

def chooks_operation(conn):
    def modify(conn, chooks):
        idx = input('选择序号：')
        idx = int(idx)
        name = input('新名字：')
        cursor = conn.cursor()
        cursor.execute('update chooks set name=? where id=?', (name, chooks[idx][0]))
        cursor.close()
        conn.commit()
        print('%s: "%s"修改为"%s"' % (chooks[idx][0], chooks[idx][1], name))
        chooks[idx][1] = name

    def delete(conn, chooks):
        idx = input('选择序号：')
        idx = int(idx)
        cursor = conn.cursor()
        cursor.execute('delete from chooks where id=?', (chooks[idx][0], ))
        cursor.close()
        conn.commit()
        print('删除%s: "%s"' % (chooks[idx][0], chooks[idx][1]))
        chooks.pop(idx)

    def get_chooks(conn):
        cursor = conn.cursor()
        cursor.execute('select id, name from chooks');
        chooks = cursor.fetchall()
        cursor.close()
        chooks = list(map(list, chooks))
        return chooks

    def show_chooks(chooks):
        for i, chook in enumerate(chooks):
            print('%6d: %s,\t\t%s' % (i, chook[0], chook[1]))

    chooks = get_chooks(conn)
    show_chooks(chooks)
    op = {'m': modify, 'd': delete}
    c = menu(op)
    while (c != 'q'):
        if c in op:
            op[c](conn, chooks)
        show_chooks(chooks)
        c = menu(op)

def menu(cmd):
    for c in cmd:
        print('%s: %s' % (c, cmd[c].__name__), end=', ')
    print('q: quit')
    c = input()
    return c

def accept(conn):
    def send_signal(fd, signal):
        fd.write(signal)
        fd.read(status_len)

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

        plisten = Process(target=listen, args=(fd, conn))
        plisten.start()

        cmd.pop('a')
        c = menu(cmd)
        while (c != 'q'):
            if c in cmd:
                cmd[c](conn)
            c = menu(cmd)
        cmd['a'] = accept

        plisten.terminate()

        send_signal(fd, close_signal)

def table_exist(cursor, tbl_name):
    cursor.execute('select name from sqlite_master where type=\'table\'')
    tables = cursor.fetchall()
    exist = False
    for table in tables:
        if table[0] == tbl_name:
            exist = True
    return exist

if __name__ == '__main__':

    id_len = 14
    status_len = 5
    cell = 10
    n = 6
    db_name = 'chook.db'
    open_signal = b'\x02\x05\x01\xaa\x03'
    close_signal = b'\x02\x05\x02\xaa\x03'

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    if not table_exist(cursor, 'chooks'):
        cursor.execute('create table chooks (id text primary key, name text)')
    if not table_exist(cursor, 'records'):
        cursor.execute('create table records (id text, start real, end real, primary key(id, start))')
    cursor.close()
    conn.commit()

    cmd = {'r': read_records, 'c': chooks_operation, 'a': accept}
    c = menu(cmd)
    while (c != 'q'):
        if c in cmd:
            cmd[c](conn)
        c = menu(cmd)

    conn.close()
