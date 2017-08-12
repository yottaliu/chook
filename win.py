#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import serial
import serial.tools.list_ports
from multiprocessing import Process, Queue
import sqlite3
from datetime import datetime

def listen(dev_name, db_name, que):
    cell = 10
    n = 6
    id_len = 14
    status_len = 5
    open_signal = b'\x02\x05\x01\xaa\x03'
    close_signal = b'\x02\x05\x02\xaa\x03'
    def send_signal(fd, signal):
        fd.write(signal)
        fd.read(status_len)

    def get_id(fd):
        id = fd.read(id_len)
        return id

    class Chook(object):
        def __init__(self, name, start, end, k):
            self.name = name
            self.start = start
            self.end = end
            self.k = k

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('select id, name from chooks');
    chooks = cursor.fetchall()
    cursor.close()

    chook_dict = dict()
    for id, name in chooks:
        chook = Chook(name, 0, 0, 0)
        chook_dict[id] = chook

    fd = serial.Serial(dev_name, 115200, timeout=0.5)

    send_signal(fd, open_signal)

    while True:
        cursor = conn.cursor()
        id = get_id(fd)
        if len(id) != 0:
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
                print('"%s"还在这儿，现在时间是 \t%s，上次记录时间是 \t%s' % (chook_dict[id].name, datetime.fromtimestamp(chook_dict[id].end), datetime.fromtimestamp(chook_dict[id].start)))
            else:
                chook_dict[id].start = chook_dict[id].end
                cursor.execute('insert into records (id, start, end) values (?, ?, ?)', (id, chook_dict[id].start, chook_dict[id].end))
                chook_dict[id].k = 0
                print('"%s"来了，现在时间是 \t\t%s' % (chook_dict[id].name, datetime.fromtimestamp(chook_dict[id].start)))
            cursor.close()
            conn.commit()
        if not que.empty():
            que.get()
            send_signal(fd, close_signal)
            conn.close()
            break

def read_records(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('select name, start, end from chooks, records where chooks.id=records.id');
    records = cursor.fetchall()
    cursor.close()
    for rec in records:
        print('%s: from %s to %s' % (rec[0], datetime.fromtimestamp(rec[1]), datetime.fromtimestamp(rec[2])))
    conn.close()

def chooks_operation(db_name):
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
        if idx < len(chooks):
            cursor = conn.cursor()
            cursor.execute('delete from chooks where id=?', (chooks[idx][0], ))
            cursor.close()
            conn.commit()
            print('删除%s: "%s"' % (chooks[idx][0], chooks[idx][1]))
            chooks.pop(idx)
        else:
            print('错误的序号！')

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

    conn = sqlite3.connect(db_name)
    chooks = get_chooks(conn)
    show_chooks(chooks)
    op = {'m': modify, 'd': delete}
    c = menu(op)
    while (c != 'q'):
        if c in op:
            op[c](conn, chooks)
        show_chooks(chooks)
        c = menu(op)
    conn.close()

def menu(cmd):
    for c in cmd:
        print('%s: %s' % (c, cmd[c].__name__), end=', ')
    print('q: quit')
    c = input()
    return c

def accept(db_name):
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

        que = Queue()

        plisten = Process(target=listen, args=(tuple(port_list[choice])[0], db_name, que))
        plisten.start()

        cmd.pop('a')
        c = menu(cmd)
        while (True):
            if c == 'q':
                que.put('q')
                plisten.join()
                break
            if c in cmd:
                cmd[c](db_name)
            c = menu(cmd)
        cmd['a'] = accept

        que.close()

def table_exist(cursor, tbl_name):
    cursor.execute('select name from sqlite_master where type=\'table\'')
    tables = cursor.fetchall()
    exist = False
    for table in tables:
        if table[0] == tbl_name:
            exist = True
    return exist

if __name__ == '__main__':

    db_name = 'chook.db'

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    if not table_exist(cursor, 'chooks'):
        cursor.execute('create table chooks (id text primary key, name text)')
    if not table_exist(cursor, 'records'):
        cursor.execute('create table records (id text, start real, end real, primary key(id, start))')
    cursor.close()
    conn.commit()
    conn.close()

    cmd = {'r': read_records, 'c': chooks_operation, 'a': accept}
    c = menu(cmd)
    while (c != 'q'):
        if c in cmd:
            cmd[c](db_name)
        c = menu(cmd)
