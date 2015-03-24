# experiment-stats

This folder contains two files, `run_experiment.py` and `config.json`. `run_experiment.py` does the heavy lifting, `config.json` is the corresponding config file.

## run_experiment.py
It can be invoked via either `python run_experiment.py` or simply `./run_experiment.py` assuming the execute bit is set.

`run_experiment.py` requires certain command line flags to be set, which are explained by its own help page:

```
$ ./run_experiment.py --help
usage: run_experiment.py [-h] -c CONFIG -n NUM_GAMES [NUM_GAMES ...] [-r]
                         [-t TIMEOUTS [TIMEOUTS ...]]

Execute nodegame experiment and write experiment data to csv file.

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Experiment configuration file in JSON format
                        containing variables that likely do not change between
                        experiments.
  -n NUM_GAMES [NUM_GAMES ...], --num_games NUM_GAMES [NUM_GAMES ...]
                        Number of simultaneous games to consider for the
                        experiment, can be a list.
  -r, --reliable        Boolean flag to turn on reliable messaging.
  -t TIMEOUTS [TIMEOUTS ...], --timeouts TIMEOUTS [TIMEOUTS ...]
                        Timeouts to consider for the experiment when reliable
                        messaging is used, can be a list.
```

So for example a mimimal invocation is `./run_experiment.py -c config.json -n 1` meaning it should read the config file from the same folder and run one experiment where there is 1 game. A more sophisticated invocation is `./run_experiment.py -c config.json -n 1 2 4 8 -r -t 1000 2000 4000` where we consider 1, 2, 4 and 8 simultaneous connections, reliable messaging to be activated, and timeouts of 1000, 2000 and 4000 milliseconds.

## config.json
This file needs to define the following variables:

```javascript
{
    // These two variables define the environment for the corresponding autoplay
    // file. The invocation is equivalent to `cd $launcher_cwd && node $launcher_file`.
    "launcher_cwd": "~/nodegame/",
    "launcher_file": "games/ultimatum/test/launcher-autoplay.js",

    // "exp_log_dir" defines the directory, where the experiment should write its
    // logs to, "msg_log_dir" is the folder where server messages are written and
    // "server_msg_file" is the correponding file in that directory. This file is
    // used to compute message delays and will be overwritten at the start of
    // every experiment.
    "exp_log_dir": "~/nodegame/node_modules/nodegame-benchmark/experiment_stats/logs/",
    "msg_log_dir": "~/nodegame/log/",
    "server_msg_file": "messages.log",

    // "game" defines the game which will be run in the experiemnt, "csv_out_dir"
    // specifies the folder where the experiment data will be written to and
    // "test_cwd" defines from where a sanity check of the experiment data should
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

## Dependencies

To be able to report CPU and memory usage of the experiment, `run_experiment.py` relies on the third party module `psutil`. You should be able to install it via `pip install psutil`, if not please see [this manual](https://github.com/giampaolo/psutil/blob/master/INSTALL.rst) for further help. Furthermore the script relies on features only included with Python 2.7, so please make sure to have a recent Python installation available.
