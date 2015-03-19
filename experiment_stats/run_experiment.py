#!/usr/bin/env python

from __future__ import print_function
import re
import os
import sys
import json
import fileinput
import subprocess
import time
import csv
import psutil
import platform
import datetime
from argparse import ArgumentParser
from collections import Counter


def write_num_games(num_games, cfg):
    """ Writes the number of games `num_games` to the `game_settings_file`
    as specified in the configuration file.
    """
    regex = re.compile(r'({0})\s*:\s*\d+'.format(cfg['num_games_kwd']))
    for line in fileinput.input(cfg['game_settings_file'], inplace=True):
        print(regex.sub(r'\1: ' + str(num_games), line.rstrip()))


def write_sio_transports(cfg):
    """ Writes the number of games `num_games` to the `game_settings_file`
    as specified in the configuration file.
    """
    # the following encoding is necessary to disable unicode (i.e. u['foobar'])
    # output, that is not readable by javascript
    sio_transports = [trans.encode('utf8') for trans in cfg['sio_transports']]
    regex = re.compile(r'({0})\s*:\s*\[.*\]'.format(cfg['sio_transports_kwd']))
    for line in fileinput.input(cfg['game_settings_file'], inplace=True):
        print(regex.sub(r'\1: ' + str(sio_transports), line.rstrip()))


def write_timeout(timeout, reliable, cfg):
    """ Writes the retry timeout and the reliable boolean flag to the
    `variables_file`. Note that even though timeout is written every time it
    only takes effect if reliable == True.
    """
    regex_reliable = re.compile(r'({0})\s*=\s*(true|false)'.
                                format(cfg['rel_msgs_var']))

    regex_retry = re.compile(r'({0})\s*=\s*\d+'.format(cfg['rel_retry_var']))

    for line in fileinput.input(cfg['variables_file'], inplace=True):
        line = line.rstrip()
        if regex_reliable.search(line):
            print(regex_reliable.sub(r'\1 = ' + str(reliable).lower(), line))
        elif regex_retry.search(line):
            print(regex_retry.sub(r'\1 = ' + str(timeout), line))
        else:
            print(line)


def sizeof_fmt(num, suffix='B'):
    """ Utility function to convert byte amounts to human readable format.
    Taken from http://stackoverflow.com/a/1094933/2528077"""
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def time_fmt(time):
    """ Utilty function to convert duration to human readable format. Follows
    default format of the unix `time` command. """
    return "{:.0f}m{:.3f}s".format(time // 60, time % 60)


def run_launcher(cfg):
    """ Executes `node launcher.js` from the right cwd and logs stdout and
    stderr to a previously defined folder.
    """
    stdout_log = os.path.join(cfg['exp_log_dir'],
                              'experiment_{0}_stdout.log'.
                              format(cfg['exp_time']))

    stderr_log = os.path.join(cfg['exp_log_dir'],
                              'experiment_{0}_stderr.log'.
                              format(cfg['exp_time']))

    with open(stdout_log, 'a') as f_out, open(stderr_log, 'a') as f_err:
        node_proc = subprocess.Popen(['node', cfg['launcher_file']],
                                     cwd=cfg['launcher_dir'],
                                     stdout=f_out,
                                     stderr=f_err)

        return node_proc


def get_process_metrics(proc):
    """ Extracts cpu times, memory infos and connection infos about a given
    process started via Popen(). Also obtains the return code.
    """
    p = psutil.Process(proc.pid)
    while proc.poll() == None:
        try:
            cpu = p.cpu_times()
            mem = p.memory_info()
            conns = p.connections('all')
        except AccessDenied:
            pass
        time.sleep(1)
    retcode = proc.wait()

    return retcode, cpu, mem, conns


def run_test(cfg):
    """ Runs `npm test` from the correct cwd and returns the return code. """
    return subprocess.call(['npm', 'test'], cwd=cfg['test_dir'])


def parse_server_msg_file(msg_file, is_reliable):
    """ Parses the server message log file. Extract metrics about the total
    number of messages and the break down according to type. In addition
    computes the average delay of a message round-trip if reliable messaging is
    enabled.
    """
    msg_counter = Counter()
    timestamps = {'client': {}, 'server': {}}

    with open(msg_file) as messages:
        for message in messages:
            msg_counter['total'] += 1
            winstonMsg = json.loads(message)
            gameMsg = json.loads(winstonMsg['message'])
            msg_counter[gameMsg['target']] += 1
            if not is_reliable:
                continue

            msg_id = str(gameMsg['id'])
            created = datetime.datetime.strptime(gameMsg['created'],
                                                 '%Y-%m-%dT%H:%M:%S.%fZ')

            time = datetime.datetime.strptime(winstonMsg['timestamp'],
                                              '%Y-%m-%dT%H:%M:%S.%fZ')

            if msg_id not in timestamps['client']:
                timestamps['client'][msg_id] = [0, 0]
            if msg_id not in timestamps['server']:
                timestamps['server'][msg_id] = [0, 0]

            if gameMsg['target'] == 'ACK':
                if gameMsg['to'] == 'SERVER':
                    timestamps['server'][gameMsg['text']][1] = time
                elif gameMsg['from'] == 'ultimatum':
                    timestamps['client'][gameMsg['text']][1] = time

            else:
                if gameMsg['to'] == 'SERVER':
                    timestamps['client'][msg_id][0] = created
                elif gameMsg['from'] == 'ultimatum':
                    timestamps['server'][msg_id][0] = time

    if not is_reliable:
        return msg_counter

    client_server_times = [
        v[1] - v[0] for v in timestamps['client'].values() if v[0] and v[1]
    ]

    server_client_times = {
        v[1] - v[0] for v in timestamps['server'].values() if v[0] and v[1]
    }

    avg_client_server_time = sum(
        client_server_times, datetime.timedelta(0)
    ).total_seconds() / len(client_server_times)

    avg_server_client_time = sum(
        server_client_times, datetime.timedelta(0)
    ).total_seconds() / len(server_client_times)

    print ("The average delay to deliver a message was of {:.0f} milliseconds."
           .format(avg_server_client_time * 1000))
    return msg_counter, avg_client_server_time, avg_server_client_time


def main():
    # Define ArgumentParser and declare all needed command line arguments
    parser = ArgumentParser(description='Execute nodegame experiment and write'
                            ' experiment data to csv file.')

    parser.add_argument('-c', '--config', type=str, required=True,
                        help='Experiment configuration file in JSON format '
                        'containing variables that likely do not change '
                        'between experiments.')

    parser.add_argument('-n', '--num_games', type=int, nargs='+',
                        required=True, help='Number of simultaneous games to '
                        'consider for the experiment, can be a list.')

    parser.add_argument('-r', '--reliable', action='store_true',
                        help='Boolean flag to turn on reliable messaging.')

    parser.add_argument('-t', '--timeouts', type=int, nargs='+',
                        help='Timeouts to consider for the experiment when '
                        'reliable messaging is used, can be a list.')

    args = parser.parse_args()

    # Manually check dependency of reliable on timeouts
    if args.reliable and not args.timeouts:
        print('Error: --timeouts needs to be specified when reliable messaging'
              ' is activated.')
        return

    with open(args.config) as cfg_fp:
        cfg = json.load(cfg_fp)

    if not args.reliable:
        args.timeouts = [cfg["default_timeout"]]

    write_sio_transports(cfg)

    # record the current unix time in micro seconds and store it in cfg
    cfg['exp_time'] = int(time.time() * 10**6)

    # construct metrics.csv file name
    csv_metrics_file = os.path.join(cfg['csv_out_dir'],
                                    'experiment_{0}_metrics.csv'.
                                    format(cfg['exp_time']))

    # construct messages.csv file name
    csv_msg_file = os.path.join(cfg['csv_out_dir'],
                                'experiment_{0}_messages.csv'.
                                format(cfg['exp_time']))

    with open(csv_metrics_file, 'w') as csv_metrics, \
         open(csv_msg_file, 'w') as csv_msg:
        metrics_names = [
            "id", "machine", "num_conns", "is_reliable", "timeout",
            "exp_ret_code", "test_ret_code", "cpu_time_user",
            "cpu_time_system", "mem_info_rss", "mem_info_vms",
            "avg_client_time", "avg_server_time"
        ]

        metrics_writer = csv.DictWriter(csv_metrics, fieldnames=metrics_names)
        metrics_writer.writeheader()

        msg_names = [
            "id", "total",
            "ACK", "ALERT", "BYE", "DATA", "ERR", "GAMECOMMAND", "HI", "JOIN",
            "LANG", "LOG", "MCONNECT", "MDISCONNECT", "MLIST", "MRECONNECT",
            "PCONNECT", "PDISCONNECT", "PLAYER_UPDATE", "PLIST", "PRECONNECT",
            "REDIRECT", "SERVERCOMMAND", "SETUP", "STAGE", "STAGE_LEVEL",
            "TXT", "WARN"
        ]

        msg_writer = csv.DictWriter(csv_msg, fieldnames=msg_names)
        msg_writer.writeheader()

        for num_games in args.num_games:
            write_num_games(num_games, cfg)
            for timeout in args.timeouts:
                write_timeout(timeout, bool(args.reliable), cfg)
                server_msg = os.path.join(cfg["msg_log_dir"],
                                          cfg["server_msg_file"])
                try:
                    os.remove(server_msg)
                except OSError:
                    pass

                # run_time serves as the current run id, again unix timestamp
                run_time = int(time.time() * 10**6)

                print ("Number of Connections: {}, Reliable: {}, Timeout: {}".
                       format(num_games, bool(args.reliable), timeout))

                proc = run_launcher(cfg)
                ret_exp, cpu, mem, conns = get_process_metrics(proc)

                ret_test = run_test(cfg)

                if args.reliable:
                    msg_counter, avg_client_time, avg_server_time = \
                        parse_server_msg_file(server_msg, args.reliable)
                else:
                    msg_counter = \
                        parse_server_msg_file(server_msg, args.reliable)

                exp_metrics = {
                    'id': run_time,
                    'machine': platform.platform(),
                    'num_conns': num_games,
                    'is_reliable': bool(args.reliable),
                    'timeout': timeout,
                    'exp_ret_code': ret_exp,
                    'test_ret_code': ret_test,
                    'cpu_time_user': time_fmt(cpu[0]),
                    'cpu_time_system': time_fmt(cpu[1]),
                    'mem_info_rss': sizeof_fmt(mem[0]),
                    'mem_info_vms': sizeof_fmt(mem[1]),
                    'avg_client_time':
                        time_fmt(avg_client_time) if args.reliable else 'N/A',
                    'avg_server_time':
                        time_fmt(avg_server_time) if args.reliable else 'N/A'
                }

                metrics_writer.writerow(exp_metrics)

                msg_counter["id"] = run_time
                # we manually set not occurring counts to 0 to avoid empty
                # strings in the csv
                for msg_name in msg_names:
                    if msg_name not in msg_counter:
                        msg_counter[msg_name] = 0
                msg_writer.writerow(msg_counter)

if __name__ == '__main__':
    main()
