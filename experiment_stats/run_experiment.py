#!/usr/bin/env python

import re
import os
import json
import fileinput
import subprocess
import time
import csv
import psutil
from argparse import ArgumentParser
from collections import Counter


def write_num_games(num_games, cfg):
    regex = re.compile(r'({0})\W*:\W*\d+'.format(cfg['num_games_keyword']))
    for line in fileinput.input(cfg['game_settings_file'], inplace=True):
        print regex.sub(r'\1: ' + str(num_games), line.rstrip())


def write_timeout(timeout, reliable, cfg):
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
    with open(os.devnull, 'w') as dev_null:
        node_proc = subprocess.Popen(['node', cfg['launcher_file']],
                                     cwd=cfg['launcher_dir'],
                                     stdout=dev_null,
                                     stderr=subprocess.STDOUT)
        p = psutil.Process(node_proc.pid)
        while node_proc.poll() == None:
            print p.cpu_times()
            time.sleep(5)
        retcode = node_proc.wait()
        return retcode, node_proc.pid


def run_test(cfg):
        return subprocess.call(['npm', 'test'], cwd=cfg['test_dir'])


def parse_server_msg_file(msg_file):
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

    if args.reliable and not args.timeouts:
        print('Error: --timeouts need to be specified when reliable messaging '
              'is activated.')
        return

    with open(args.config) as cfg_fp:
        cfg = json.load(cfg_fp)

    if not args.reliable:
        args.timeouts = [cfg["default_timeout"]]

    exp_time = int(time.time() * 10**6)  # time with micro-second accuracy
    csv_metrics_file = os.path.join(cfg['csv_out_dir'],
                                    'experiment_{0}_metrics.csv'.
                                    format(exp_time))

    csv_msg_file = os.path.join(cfg['csv_out_dir'],
                                'experiment_{0}_messages.csv'.format(exp_time))

    with open(csv_msg_file, 'w') as csv_msg:
        exp_metric_names = [
            "id", "nConn", "is_reliable", "timeout", "nACKs", "machine",
            "total_msgs", "test_result"
        ]

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
                os.remove(server_msg)
                run_time = int(time.time() * 10**6)
                code, pid = run_launcher(cfg)
                run_test(cfg)
                msg_counter = parse_server_msg_file(server_msg)

                msg_counter["id"] = run_time
                for msg_name in msg_names:
                    if msg_name not in msg_counter:
                        msg_counter[msg_name] = 0
                msg_writer.writerow(msg_counter)

if __name__ == '__main__':
    main()
