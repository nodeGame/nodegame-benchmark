#!/usr/bin/env python

import re
import os
import json
import fileinput
import subprocess
import time
import csv
import psutil
import platform
from argparse import ArgumentParser
from collections import Counter


def write_num_games(num_games, cfg):
    """ Writes the number of games `num_games` to the `game_settings_file`
    as specified in the configuration file.
    """
    regex = re.compile(r'({0})\W*:\W*\d+'.format(cfg['num_games_keyword']))
    for line in fileinput.input(cfg['game_settings_file'], inplace=True):
        print regex.sub(r'\1: ' + str(num_games), line.rstrip())


def write_timeout(timeout, reliable, cfg):
    """ Writes the retry timeout and the reliable boolean flag to the
    `variables_file`. Note that even though timeout is written every time it
    only takes effect if reliable == True.
    """
    regex_reliable = re.compile(r'({0})\W*=\W*(true|false)'.
                                format(cfg['rel_msgs_var']))

    regex_retry = re.compile(r'({0})\W*=\W*\d+'.format(cfg['rel_retry_var']))

    for line in fileinput.input(cfg['variables_file'], inplace=True):
        line = line.rstrip()
        if regex_reliable.search(line):
            print regex_reliable.sub(r'\1 = ' + str(reliable).lower(), line)
        elif regex_retry.search(line):
            print regex_retry.sub(r'\1 = ' + str(timeout), line)
        else:
            print line


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
        cpu, mem, conns = p.cpu_times(), p.memory_info(), p.connections('all')
        time.sleep(1)
    retcode = proc.wait()

    return retcode, cpu, mem, conns


def run_test(cfg):
    """ Runs `npm test` from the correct cwd and returns the return code. """
    return subprocess.call(['npm', 'test'], cwd=cfg['test_dir'])


def parse_server_msg_file(msg_file):
    """ Parses the server message log file. Extract metrics about the total
    number of messages and the break down according to type.
    """
    msg_counter = Counter()
    with open(msg_file) as messages:
        for message in messages:
            msg_counter['total'] += 1
            winstonMsg = json.loads(message)
            gameMsg = json.loads(winstonMsg['message'])
            msg_counter[gameMsg['target']] += 1

    print msg_counter
    return msg_counter


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
            "cpu_time_system", "mem_info_rss", "mem_info_vms"
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

                proc = run_launcher(cfg)
                ret_exp, cpu, mem, conns = get_process_metrics(proc)

                ret_test = run_test(cfg)

                exp_metrics = {
                    'id': run_time,
                    'machine': platform.platform(),
                    'num_conns': num_games,
                    'is_reliable': bool(args.reliable),
                    'timeout': timeout,
                    'exp_ret_code': ret_exp,
                    'test_ret_code': ret_test,
                    'cpu_time_user': cpu[0],
                    'cpu_time_system': cpu[1],
                    'mem_info_rss': mem[0],
                    'mem_info_vms': mem[1]
                }

                metrics_writer.writerow(exp_metrics)
                msg_counter = parse_server_msg_file(server_msg)

                msg_counter["id"] = run_time
                # we manually set not occurring counts to 0 to avoid empty
                # strings in the csv
                for msg_name in msg_names:
                    if msg_name not in msg_counter:
                        msg_counter[msg_name] = 0
                msg_writer.writerow(msg_counter)

if __name__ == '__main__':
    main()
