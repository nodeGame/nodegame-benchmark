#!/usr/bin/python2
#
# Runs a benchmark on the 'pairs' game.
#
# Usage: python run-pairs-benchmark.py [configfile]
#
# IMPORTANT: Set the path parameters below for your setup.
#
# 'node' and 'phantomjs' must be in the executable path,
# 'phantom-pairs.js' must be in the current directory.

import os, sys, time, re, csv
import subprocess as sub
import numpy as np

# Load configuration:
config_path = 'conf/config.py'
if len(sys.argv) > 1:
    config_path = sys.argv[1]
config = {}
execfile(config_path, config)

# Remove old message-log:
if os.path.exists(config['msglog_path']):
    print ' * Removing old message log:', config['msglog_path']
    os.remove(config['msglog_path'])

# Start server:
print ' * Starting the server with the "pairs" game...'
fnull = open(os.devnull, 'w')
server_proc = sub.Popen(['node', 'server-pairs.js'], cwd=config['nodegame_path'], stdout=fnull)
time.sleep(3)

# Call the PhantomJS script:
print ' * Running the PhantomJS script with', config['n'], 'connections...'
phantom_call = ['../node_modules/.bin/phantomjs', 'phantom-pairs.js', str(config['n'])]
if config['url']: phantom_call.append(config['url'])
phantom_proc = sub.Popen(phantom_call, stdout=sub.PIPE, universal_newlines=True)

# Get and analyze the script's output:
base_ms  = None
start_ms = np.zeros(config['n'])
end_ms   = np.zeros(config['n'])
while True:
    line = phantom_proc.stdout.readline()
    if not line: break
    line = line.strip()

    if config['debug']:
        print ' *** Got line:', line

    tokens = line.split()
    # tokens should be of this form:
    #  [ 'Opened', '3', 'at', '1379083161743' ], or
    #  [ 'Finished', '0', 'at', '1379083169421' ],
    # etc.
    status = tokens[0]
    idx    = int(tokens[1])
    mstime = int(tokens[3])

    if base_ms is None:
        base_ms = mstime

    if status == 'Opened':
        start_ms[idx] = mstime - base_ms
    elif status == 'Finished':
        end_ms[idx]   = mstime - base_ms
    else:
        raise Exception('Invalid input: "' + line + '"')

phantom_proc.wait()
print ' * The PhantomJS script has finished.'

# Stop server:
print ' * Stopping server.'
server_proc.kill()

run_secs = (end_ms - start_ms) / 1000

# Print runtime statistics:

if config['debug']:
    print
    for idx, time in enumerate(run_secs):
        print ' *** Runtime for connection %5d:%7.2f s' % (idx, time)

print
print 'Game runtime statistics:'
print 'Minimum:%7.2f  s' % np.min(run_secs)
print 'Maximum:%7.2f  s' % np.max(run_secs)
print 'Average:%7.2f  s' % np.mean(run_secs)
print 'Median:%8.2f  s'  % np.median(run_secs)
print 'Std Dev:%8.3f s'  % np.std(run_secs)
print 'Sum:%8.0f     s'  % np.sum(run_secs)

# Analyze message-log:
msg_counts = {
    'say.DATA': 0,
    'say.GAMECOMMAND': 0,
    'say.HI': 0,
    'say.PCONNECT': 0,
    'say.PDISCONNECT': 0,
    'say.PLAYER_UPDATE': 0,
    'say.SETUP': 0,
    'set.DATA': 0
}
pattern = re.compile(r'.*"action":"(\w+)".*"target":"(\w+)".*', flags=re.DOTALL)
with open(config['msglog_path'], 'r') as msglog:
    for line in msglog.readlines():
        # Get message type, e.g. 'say.DATA':
        msg_type = pattern.sub(r'\1.\2', line)

        # Keep count of message type:
        if msg_type in msg_counts:
            msg_counts[msg_type] += 1

# Print message counts:
print
print 'Message type frequencies:'
for msg_type in sorted(msg_counts.keys()):
    print '%7d %s' % (msg_counts[msg_type], msg_type)

# Write to CSV-file:
print
print 'Writing data to CSV-file:', config['csv_path']
with open(config['csv_path'], 'w') as csvfile:
    csvwriter = csv.DictWriter(csvfile,
        ['timestamp'] + sorted(msg_counts.keys()) +
        ['runtime.min', 'runtime.max', 'runtime.avg', 'runtime.median',
         'runtime.stddev', 'runtime.sum'],
        quoting=csv.QUOTE_NONNUMERIC)

    csvwriter.writeheader()

    fields = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
        'runtime.min': np.min(run_secs),
        'runtime.max': np.max(run_secs),
        'runtime.avg': np.mean(run_secs),
        'runtime.median': np.median(run_secs),
        'runtime.stddev': np.std(run_secs),
        'runtime.sum': np.sum(run_secs)
    }
    fields.update(msg_counts)
    csvwriter.writerow(fields)
