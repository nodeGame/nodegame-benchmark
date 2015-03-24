# nodegame-benchmark

Benchmark and Testing for nodeGame.

## Overview

Reads settings from configuration, starts the nodeGame server,
connects phantoms to the desired channel, compute statistics about the
number and timing of messages exchanged, and also statistics about CPU
and memory use if the dependency `psutil` is installed. 

All statistics are saved into csv files, as specified in the settings.

When a gameover message is intercepted, any automated test defined by
the game in the package.json file are going to be run, and results are
displayed to the user.


## Usage

1. Copy the file `config-sample.json` to `config.json`
2. Edit `config.json` with the correct settings for your environment (see below)
3. Run the benchmark either as `python run_benchmark.py` or simply
`./run_benchamrk.py`

### config.json

This file needs to define the following variables:

```javascript
{
    // These two variables define the environment for the corresponding autoplay
    // file. The invocation is equivalent to `cd $launcher_cwd && node $launcher_file`.
    "launcher_cwd": "~/nodegame/",
    "launcher_file": "games/ultimatum/test/launcher-autoplay.js",

    // "exp_log_dir" defines the directory, where the benchmark should write its
    // logs to, "msg_log_dir" is the folder where server messages are written and
    // "server_msg_file" is the correponding file in that directory. This file is
    // used to compute message delays and will be overwritten at the start of
    // every benchmark.
    "exp_log_dir": "~/nodegame/node_modules/nodegame-benchmark/logs/",
    "msg_log_dir": "~/nodegame/log/",
    "server_msg_file": "messages.log",

    // "game" defines the game which will be run in the experiemnt, "csv_out_dir"
    // specifies the folder where the benchmark data will be written to and
    // "test_cwd" defines from where a sanity check of the benchmark data should
    // be executed, this is equivalent to `cd $test_cwd && npm test`.
    "game": "ultimatum",
    "csv_out_dir": "~/nodegame/games/ultimatum/data/",
    "test_cwd": "~/nodegame/games/ultimatum/",

    // "game_settings_file" defines the path to a settings.js file where game
    // related properties are defined. Here numGames and sioTransports are of
    // interest which can be defined via "num_games_kwd" and "sio_transports_kwd".
    // numGames takes it value via the given `--num_games` flag, sioTransports
    // are defined explicitly. Possible values are the following: ["websocket",
    // "flashsocket", "htmlfile", "xhr-polling", "jsonp-polling"].
    "game_settings_file": "~/nodegame/games/ultimatum/test/settings.js",
    "num_games_kwd": "numGames",
    "sio_transports_kwd": "sioTransports",
    "sio_transports": ["websocket", "flashsocket", "htmlfile", "xhr-polling", "jsonp-polling"],

    // This section defines the variables.js file where properties such as reliable
    // messaging and the correponding timeouts are defined. For this to work the
    // correct variable names are be defined via "rel_msgs_var" and "rel_retry_var".
    // "default_timeout" defines the default timeout that will be written when the
    // `--timeouts` flag is not defined.
    "variables_file": "~/nodegame/node_modules/nodegame-client/lib/modules/variables.js",
    "rel_msgs_var": "k.reliableMessaging",
    "rel_retry_var": "k.reliableRetryInterval",
    "default_timeout": 4000
}
```


## Options for run_benchmark

```
$ ./run_benchmark.py --help
usage: run_benchmark.py [-h] -c CONFIG -n NUM_GAMES [NUM_GAMES ...] [-r]
                         [-t TIMEOUTS [TIMEOUTS ...]]

Execute nodegame benchmark and write benchmark data to csv file.

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Benchmark configuration file in JSON format
                        containing variables that likely do not change between
                        benchmarks.
  -n NUM_GAMES [NUM_GAMES ...], --num_games NUM_GAMES [NUM_GAMES ...]
                        Number of simultaneous games to consider for the
                        benchmark, can be a list.
  -r, --reliable        Boolean flag to turn on reliable messaging.
  -t TIMEOUTS [TIMEOUTS ...], --timeouts TIMEOUTS [TIMEOUTS ...]
                        Timeouts to consider for the benchmark when reliable
                        messaging is used, can be a list.
```

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

Copyright (C) 2015 Stefano Balietti

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
