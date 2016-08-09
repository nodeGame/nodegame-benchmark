# nodegame-benchmark (beta)

Benchmark and Testing for nodeGame.

## Overview

The benchmark script reads settings from a config file, starts the
nodeGame server, connects a number of PhantomJS clients to the specified
channel and lets them play.

While playing, the script collects statistics about the number and the
timing of all exchanged messages, and also about CPU and memory usage
(if the dependency `psutil` is installed).

When all games are finished, all statistics are saved to csv files, as
specified in the settings. If an automated test script is defined by the
`package.json` file inside the game directory, such a test-script will
executed and the results displayed on screen.


## Usage

1. Create a copy of the file `config-sample.ini` with name `config.ini`
2. Edit `config.ini` with the correct settings for your environment (see below)
3. Run the benchmark either with `python run_benchmark.py` or simply with
   `./run_benchamrk.py`

### config.ini

This file needs to define the following variables. Note that it
is possible to refer to variables defined in other sections via
`${SECTION_NAME:VAR_NAME}` syntax.

```ini
[General Settings]
    game: ultimatum

; This is the directories section.
; All of these directories need to exist.
[Directories]
    nodegame_dir: ~/nodegame
    benchmark_dir: ${nodegame_dir}/node_modules/nodegame-benchmark
    client_dir: ${nodegame_dir}/node_modules/nodegame-client
    server_dir: ${nodegame_dir}/node_modules/nodegame-server
    game_dir: ${nodegame_dir}/games/${General Settings:game}

    ; This is the directory where stdout and stderr logs will be written.
    log_dir: ${benchmark_dir}/log

    ; This is the directory where data in csv format will be written.
    csv_dir: ${benchmark_dir}/csv

    ; This folder contains the launcher of the benchmark.
    launcher_dir: ${nodegame_dir}/test

    ; This folder determines the "current working directory" of the launcher.
    launcher_cwd: ${nodegame_dir}

    ; This folder contains the logs of messages.
    msg_log_dir: ${nodegame_dir}/log

    ; This folder is the current working directory of the test that sanitizes
    ; benchmark results.
    test_cwd: ${game_dir}

; This is the files section.
; All of these files need to exist.
[Files]
    ; This is where the values of the [Client Variables] section are written.
    client_var_file: ${Directories:client_dir}/lib/modules/variables.js

    ; This is where the values of the [Server Variables] section are written.
    server_var_file: ${Directories:server_dir}/conf/servernode.js

    ; This file contains the messages received and sent by the server.
    server_msg_file: ${Directories:msg_log_dir}/messages.log

    ; These files specify the launcher and its settings file.
    launcher_file: ${Directories:launcher_dir}/launcher-autoplay.js
    launcher_settings_file: ${Directories:game_dir}/test/settings.js

[Client Variables]
    rel_msg_var: k.reliableMessaging
    rel_retry_var: k.reliableRetryInterval

[Server Variables]
    rel_msg_var: servernode.reliableMessaging
    rel_retry_var: servernode.reliableRetryInterval

; The settings specified here will be written to the launcher_settings_file
[Launcher Settings]
    ; sioTransports are not working in Express 4 at the moment.
    ; sioTransports: ["websocket", "flashsocket", "htmlfile", "xhr-polling",
    ;                 "jsonp-polling"]
```

## Options for run_benchmark

```
$ ./run_benchmark.py --help
usage: run_benchmark.py [-h] -c CONFIG [-n NUM_CONNS [NUM_CONNS ...]] [-r]
                        [-nr] [-t TIMEOUTS [TIMEOUTS ...]]

Execute nodegame benchmark and write benchmark data to csv file.

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Benchmark configuration file in INI format containing
                        variables that likely do not change between
                        benchmarks.
  -n NUM_CONNS [NUM_CONNS ...], --num_conns NUM_CONNS [NUM_CONNS ...]
                        Number of simultaneous connections to consider for the
                        benchmark, can be a list.
  -r, --reliable        Boolean flag to turn on reliable messaging.
  -nr, --no_run         Boolean flag to disable launching the game. Will just
                        process existing log files.
  -t TIMEOUTS [TIMEOUTS ...], --timeouts TIMEOUTS [TIMEOUTS ...]
                        Timeouts to consider for the benchmark when reliable
                        messaging is used, can be a list.
```

## File format of metrics.csv

`metrics.csv` defines the following data headers:

- `id`: Unix timestamp of the experiment in milliseconds. It is very unlikely
  that two different runs have the same timestamp, hence the use as an
  identifier is justified.
- `machine`: Name of the current machine as reported by Python's
  [`platform.platform()`](https://docs.python.org/3.4/library/platform.html#platform.platform).
- `num_conns`: Number of simultaneous connections during this run of the
  experiment.  This is the number specified by the `-n` flag.
- `is_reliable`: Reports whether reliable messaging was turned on or off. This
  is specified by the presence or absence of the `-r` flag.
- `timeout`: Reports the timeout used during the current run. Only meaningful
  if reliable messaging was turned on. Controlled via the `-t` flag.
- `benchmark_ret_code`: Return code of the benchmark process. A number
  different from 0 indicates that there was a problem.
- `test_ret_code`: Return code of the test process. A number different from 0
  indicates that there was a problem.
- `cpu_time_user`: User CPU time as reported by
  [`psutil.Process.cpu_times()`](https://pythonhosted.org/psutil/#psutil.Process.cpu_times).
  This time also includes CPU time spent by children processes of the current
  process.
- `cpu_time_system`: System CPU time as reported by
  [`psutil.Process.cpu_times()`](https://pythonhosted.org/psutil/#psutil.Process.cpu_times).
  This time also includes CPU time spent by children processes of the current
  process.
- `mem_info_rss`: Resident Set Size (RSS) usage as reported by
  [`psutil.Process.memory_info()`](https://pythonhosted.org/psutil/#psutil.Process.memory_info).
  This usage also includes memory usage by children processes of the current
  process.
- `mem_info_vms`: Virtual Memory Size (VMS) usage as reported by
  [`psutil.Process.memory_info()`](https://pythonhosted.org/psutil/#psutil.Process.memory_info).
  This usage also includes memory usage by children processes of the current
  process.
- `avg_client_time`: When reliable messaging is enabled, this is the average
  time to process a client message. Time is measured as the duration between
  receiving a client message and sending the corresponding ACK message.
  Currently this is only measured on the server and hence is not meaningful.
- `avg_server_time`: When reliable messaging is enabled, this is the average
  time for a round trip for messages from the server. The duration reported is
  the difference between sending a message from a server and receiving the ACK
  for it.


## Example Runs

Reads the config file and run 1 benchmark where there is 1 game:

    ./run_.py -c config.json -n 1


Here we consider 1, 2, 4 and 8 simultaneous connections, reliable
messaging to be activated, and timeouts of 1000, 2000 and 4000
milliseconds.

    ./run_benchmark.py -c config.json -n 1 2 4 8 -r -t 1000 2000 4000


## Requirements and Dependencies

To be able to report CPU and memory usage, `run_benchmark.py` relies
on the third party module `psutil`. You should be able to install it
via:

     pip install psutil

See
[this manual](https://github.com/giampaolo/psutil/blob/master/INSTALL.rst)
for further help.

Furthermore the script relies on features on included with Python 2.7,
so please make sure to have a recent Python installation available.

## License

[MIT](LICENSE)
