#!/usr/bin/env python3

import re
import os
import sys
import json
import fileinput
import subprocess
import time
import csv
import platform
import datetime
import configparser
import argparse
import collections

try:
    import psutil
except ImportError:
    found_psutil = False
    print("Was not able to import psutil. Please install it via `pip3 install "
          "psutil`.\nThe benchmark will run, but it won't be able to extract "
          "CPU or memory metrics.\n", file=sys.stderr)
else:
    found_psutil = True


def get_cmd_args():
    # Define ArgumentParser and declare all needed command line arguments
    parser = argparse.ArgumentParser(description='Execute nodegame benchmark '
                                     'and write benchmark data to csv file.')

    parser.add_argument('-c', '--config', type=str, required=True,
                        help='Benchmark configuration file in INI format '
                        'containing variables that likely do not change '
                        'between benchmarks.')

    parser.add_argument('-n', '--num_games', type=int, nargs='+',
                        required=True, help='Number of simultaneous games to '
                        'consider for the benchmark, can be a list.')

    parser.add_argument('-r', '--reliable', action='store_true',
                        help='Boolean flag to turn on reliable messaging.')

    parser.add_argument('-t', '--timeouts', type=int, nargs='+',
                        help='Timeouts to consider for the benchmark when '
                        'reliable messaging is used, can be a list.')

    args = parser.parse_args()

    # Manually check dependency of reliable on timeouts
    if args.reliable and not args.timeouts:
        print('Error: --timeouts needs to be specified when reliable messaging'
              ' is activated.', file=sys.stderr)
        sys.exit(1)

    # Make sure we have a default value for args.timeouts. This is important
    # because we are iterating over it, even though the actual value does not
    # matter
    if not args.reliable:
        args.timeouts = [4000]

    return args


def expand_user_in_cfg(cfg):
    """ Iterate over all options in both the 'Directories' and 'Files' sections
    and expand the user variable"""
    for dir_option in cfg.options('Directories'):
        cfg.set('Directories', dir_option,
                os.path.expanduser(cfg.get('Directories', dir_option)))

    for file_option in cfg.options('Files'):
        cfg.set('Files', file_option,
                os.path.expanduser(cfg.get('Files', file_option)))


# Record the current Unix time in micro seconds.
# This is used to uniquely identify the benchmark.
BENCHMARK_TIME = int(time.time() * 10**6)
def get_benchmark_filename(folder, suffix, ext):
    """ Utility function to create benchmark filenames with timestamp included.
    """
    file_name = 'benchmark_{}_{}.{}'.format(BENCHMARK_TIME, suffix, ext)
    return os.path.join(folder, file_name)


def write_launcher_settings(settings_file, settings):
    with open(settings_file, 'w') as settings_fp:
        settings_str = ",\n".join(["    {}: {}".format(k, v)
                                  for (k,v) in settings])
        settings_fp.write("module.exports = {{\n{}\n}};\n"
                          .format(settings_str))


def write_timeout_to_client_vars(cfg, reliable, timeout):
    """ Writes the retry timeout and the reliable boolean flag to the
    ${client_var_file}. Note that even though timeout is written every time it
    only takes effect if reliable == True.
    """
    regex_reliable = re.compile(r'({0})\s*=\s*(true|false)'.format(
                                cfg.get('Client Variables','rel_msg_var')))

    regex_retry = re.compile(r'({0})\s*=\s*\d+'.format(
                             cfg.get('Client Variables','rel_retry_var')))

    # We iterate through the client variable file and modify it in-place.
    # In this case everything written to stdout will be redirected to the file
    # we opened, hence we need to print every line.
    for line in fileinput.input(cfg.get('Files', 'client_var_file'),
                                inplace=True):
        # Remove trailing whitespace
        line = line.rstrip()

        # If the current line matches the reliable regex, do the appropriate
        # substitution. We convert reliable to lower case, because booleans
        # are uppercase in python (True, False vs. true, false).
        if regex_reliable.search(line):
            print(regex_reliable.sub(r'\1 = ' + str(reliable).lower(), line))
        # Else if it matches the retry variable regex, do another substitution.
        elif regex_retry.search(line):
            print(regex_retry.sub(r'\1 = ' + str(timeout), line))
        # Else print the original line.
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
    """ Utilty function to convert duration to human readable format.
    Follows default format of the Unix `time` command. """
    return "{:.0f}m{:.3f}s".format(time // 60, time % 60)


def run_launcher(cfg):
    """ Executes `node launcher.js` from the right cwd and logs stdout and
    stderr to the previously defined log folder.
    """

    stdout_log = get_benchmark_filename(cfg.get('Directories', 'log_dir'),
                                        'stdout', 'log')

    stderr_log = get_benchmark_filename(cfg.get('Directories', 'log_dir'),
                                        'stderr', 'log')

    launcher_file = cfg.get('Files', 'launcher_file')
    if not os.path.exists(launcher_file):
        raise FileNotFoundError("$[Files] launcher_file = {} does not "
                                "exist.".format(launcher_file))

    launcher_cwd = cfg.get('Directories', 'launcher_cwd')
    if not os.path.exists(launcher_cwd):
        raise FileNotFoundError("[Directories] launcher_cwd = {} does not "
                                "exist.".format(launcher_cwd))

    with open(stdout_log, 'a') as f_out, open(stderr_log, 'a') as f_err:
        proc = subprocess.Popen(['node', cfg.get('Files', 'launcher_file')],
                                 cwd=cfg.get('Directories', 'launcher_cwd'),
                                 stdout=f_out, stderr=f_err)

        return proc


def get_process_metrics(proc):
    """ Extracts CPU times, memory infos and connection infos about a given
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
    return subprocess.call(['npm', 'test'],
                           cwd=cfg.get('Directories', 'test_cwd'))


def parse_server_msg_file(msg_file, is_reliable):
    """ Parses the server message log file. Extract metrics about the total
    number of messages and the break down according to type. In addition
    computes the average delay of a message round-trip if reliable messaging is
    enabled.
    """

    # define a message counter and a timestamps dictionary for both client and
    # server
    msg_counter = collections.Counter()
    timestamps = {'client': {}, 'server': {}}

    # open the message file for reading
    with open(msg_file) as messages:
        for message in messages:
            # increment total message counter
            msg_counter['total'] += 1

            # parse the resulting json strings
            winstonMsg = json.loads(message)
            gameMsg = json.loads(winstonMsg['message'])

            # increment corresponding target counter
            msg_counter[gameMsg['target']] += 1

            # skip the rest if reliable messaging is not activated
            if not is_reliable:
                continue

            # extract message id
            msg_id = str(gameMsg['id'])

            # parse JavaScript Date.prototype.toISOString() into a Python
            # datetime object
            created = datetime.datetime.strptime(gameMsg['created'],
                                                 '%Y-%m-%dT%H:%M:%S.%fZ')

            time = datetime.datetime.strptime(winstonMsg['timestamp'],
                                              '%Y-%m-%dT%H:%M:%S.%fZ')

            # initialize timestamps
            if msg_id not in timestamps['client']:
                timestamps['client'][msg_id] = [0, 0]
            if msg_id not in timestamps['server']:
                timestamps['server'][msg_id] = [0, 0]

            # different between ACK and normal messages for both client and
            # server
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

    # simply return counter if no reliable messaging
    if not is_reliable:
        return msg_counter

    # compute timedeltas for both client and server
    client_server_times = [
        v[1] - v[0] for v in timestamps['client'].values() if v[0] and v[1]
    ]

    server_client_times = {
        v[1] - v[0] for v in timestamps['server'].values() if v[0] and v[1]
    }

    if len(client_server_times) == 0:
        print("Warning: Could not record time deltas for client -> server "
              "messages.", file=sys.stderr)
        avg_client_server_time = 0.0
    else:
        avg_client_server_time = sum(
            client_server_times, datetime.timedelta(0)
        ).total_seconds() / len(client_server_times)

    if len(server_cleint_times) == 0:
        print("Warning: Could not record time deltas for server -> client "
              "messages.", file=sys.stderr)
        avg_server_cleint_time = 0.0
    else:
        avg_server_client_time = sum(
            server_client_times, datetime.timedelta(0)
        ).total_seconds() / len(server_client_times)

    print("The average delay to deliver a message was of {:.0f} milliseconds."
          .format(avg_server_client_time * 1000))
    return msg_counter, avg_client_server_time, avg_server_client_time


def main():
    args = get_cmd_args()

    with open(args.config) as cfg_fp:
        cfg = configparser.SafeConfigParser(
                interpolation=configparser.ExtendedInterpolation())
        # make the config options case sensitive
        cfg.optionxform = str
        cfg.readfp(cfg_fp)

    expand_user_in_cfg(cfg)

    # construct metrics.csv file name
    csv_metrics_file = \
        get_benchmark_filename(cfg.get('Directories', 'csv_dir'),
                               'metrics', 'csv')

    # construct messages.csv file name
    csv_msg_file = \
        get_benchmark_filename(cfg.get('Directories', 'csv_dir'),
                               'messages', 'csv')

    # this defines the metrics we want to record
    metrics_names = [
        "id", "machine", "num_conns", "is_reliable", "timeout",
        "benchmark_ret_code", "test_ret_code", "cpu_time_user",
        "cpu_time_system", "mem_info_rss", "mem_info_vms",
        "avg_client_time", "avg_server_time"
    ]

    # this defines the messages we want to record
    msg_names = [
        "id", "total",
        "ACK", "ALERT", "BYE", "DATA", "ERR", "GAMECOMMAND", "HI", "JOIN",
        "LANG", "LOG", "MCONNECT", "MDISCONNECT", "MLIST", "MRECONNECT",
        "PCONNECT", "PDISCONNECT", "PLAYER_UPDATE", "PLIST", "PRECONNECT",
        "REDIRECT", "SERVERCOMMAND", "SETUP", "STAGE", "STAGE_LEVEL",
        "TXT", "WARN"
    ]

    # open csv files for writing
    with open(csv_metrics_file, 'w') as csv_metrics, \
         open(csv_msg_file, 'w') as csv_msg:

        # define the respective csv writers and write the header rows
        metrics_writer = csv.DictWriter(csv_metrics, fieldnames=metrics_names)
        metrics_writer.writeheader()

        msg_writer = csv.DictWriter(csv_msg, fieldnames=msg_names)
        msg_writer.writeheader()

        # iterate over the number of games
        for num_games in args.num_games:
            # set the current number of games in the cfg object and write it
            # to the launcher settings file
            cfg.set('Launcher Settings', 'numGames', str(num_games))
            write_launcher_settings(cfg.get('Files', 'launcher_settings_file'),
                                    cfg.items('Launcher Settings'))

            # iterate over the specified timeouts
            for timeout in args.timeouts:
                write_timeout_to_client_vars(cfg, bool(args.reliable), timeout)
                msg_file = os.path.join(cfg.get("Directories", "msg_log_dir"),
                                        cfg.get("Files", "server_msg_file"))

                # we try to delete the existing file, if this fails it means
                # it did not exist in the first place, so we can just continue
                try:
                    os.remove(msg_file)
                except OSError:
                    pass

                # run_timestamp serves as the current run id
                run_timestamp = int(time.time() * 10**6)

                # print information about the current run configuration to
                # standard output
                print ("Number of Connections: {}, Reliable: {}, Timeout: {}"
                       .format(num_games, bool(args.reliable), timeout))

                # start the launcher process
                launcher = run_launcher(cfg)

                # if psutil is installed record operating system utils
                if found_psutil:
                    ret_benchmark, cpu, mem, conns = \
                        get_process_metrics(launcher)
                # else just wait for termination of the run
                else:
                    ret_benchmark = launcher.wait()

                if ret_benchmark:
                    print("Warning: The current run had a non-zero exit code. "
                          "Please have a look at the log,\nthe benchmark id is"
                          " {}.".format(BENCHMARK_TIME), file=sys.stderr)

                ret_test = run_test(cfg)
                if ret_test:
                    print("Warning: The test run had a non-zero exit code.",
                          file=sys.stderr)

                # if reliable messaging is activated compute average response
                # time
                if args.reliable:
                    msg_counter, avg_client_time, avg_server_time = \
                        parse_server_msg_file(msg_file, args.reliable)
                else:
                    msg_counter = \
                        parse_server_msg_file(msg_file, args.reliable)

                # finally collect all benchmark metrics and write it to the csv
                benchmark_metrics = {
                    'id': run_timestamp,
                    'machine': platform.platform(),
                    'num_conns': num_games,
                    'is_reliable': bool(args.reliable),
                    'timeout': timeout if args.reliable else 'N/A',
                    'benchmark_ret_code': ret_benchmark,
                    'test_ret_code': ret_test,
                    'cpu_time_user':
                        time_fmt(cpu[0]) if found_psutil else 'N/A',
                    'cpu_time_system':
                        time_fmt(cpu[1]) if found_psutil else 'N/A',
                    'mem_info_rss':
                        sizeof_fmt(mem[0]) if found_psutil else 'N/A',
                    'mem_info_vms':
                        sizeof_fmt(mem[1]) if found_psutil else 'N/A',
                    'avg_client_time':
                        time_fmt(avg_client_time) if args.reliable else 'N/A',
                    'avg_server_time':
                        time_fmt(avg_server_time) if args.reliable else 'N/A'
                }

                metrics_writer.writerow(benchmark_metrics)

                # add 'id' field to the message counter
                msg_counter["id"] = run_timestamp
                # we manually set not occurring counts to 0 to avoid empty
                # strings in the csv
                for msg_name in msg_names:
                    if msg_name not in msg_counter:
                        msg_counter[msg_name] = 0

                # finally write the message statistics
                msg_writer.writerow(msg_counter)

if __name__ == '__main__':
    try:
        main()
        error = False
    except configparser.ParsingError as err:
        error = err
    except configparser.NoSectionError as err:
        print("Error: The config file has a missing section.", file=sys.stderr)
        error = err
    except configparser.NoOptionError as err:
        print("Error: The config file has a missing option.", file=sys.stderr)
        error = err
    except (PermissionError, FileNotFoundError) as err:
        print("Error: The config file has an invalid value.", file=sys.stderr)
        error = err

    if error:
        print(error, file=sys.stderr)
        sys.exit(1)
