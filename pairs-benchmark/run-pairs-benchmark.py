#!/usr/bin/python2
#
# Runs a benchmark on the 'pairs' game.
#
# IMPORTANT: Set the path parameters below for your setup.
#
# 'node' and 'phantomjs' must be in the executable path,
# 'phantom-pairs.js' must be in the current directory.

import os, sys, time, re
import subprocess as sub
import numpy as np

# CHANGE THIS FOR YOUR SETUP:
nodegame_path =                 '../../nodegame/'
server_path   = nodegame_path + 'node_modules/nodegame-server/'
msglog_path   = server_path   + 'log/messages'

# Program parameters:
n = 2
url = None
debug = True

if len(sys.argv) > 1:
    n = int(sys.argv[1])
if len(sys.argv) > 2:
    url = sys.argv[2]

# Remove old message-log:
if os.path.exists(msglog_path):
    print ' * Removing old message log:', msglog_path
    os.remove(msglog_path)

# Start server:
print ' * Starting the server with the "pairs" game...'
fnull = open(os.devnull, 'w')
server_proc = sub.Popen(['node', 'server-pairs.js'], cwd=nodegame_path, stdout=fnull)
time.sleep(3)

# Call the PhantomJS script and get its output:
print ' * Running the PhantomJS script with', n, 'connections...'
phantom_call = ['phantomjs', 'phantom-pairs.js', str(n)]
if url: phantom_call.append(url)
output = sub.check_output(phantom_call, universal_newlines=True)
print ' * The PhantomJS script has finished.'

# Stop server:
print ' * Stopping server.'
server_proc.kill()

# Analyze output:
base_ms  = None
start_ms = np.zeros(n)
end_ms   = np.zeros(n)
for line in output.splitlines():
    if debug:
        print 'Got line: ', line

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

run_secs = (end_ms - start_ms) / 1000

# Print runtime statistics:

if debug:
    print
    print 'base_ms =', base_ms
    print 'start_ms =', start_ms
    print 'end_ms =', end_ms
    print 'run_secs =', run_secs
    print
    for idx, time in enumerate(run_secs):
        print 'Runtime for connection %5d:%7.2f s' % (idx, time)

print
print 'Game runtime statistics:'
print 'Minimum:%7.2f  s' % np.min(run_secs)
print 'Maximum:%7.2f  s' % np.max(run_secs)
print 'Average:%7.2f  s' % np.mean(run_secs)
print 'Median:%8.2f  s'  % np.median(run_secs)
print 'Std Dev:%8.3f s'  % np.std(run_secs)
print 'Sum:%8.0f     s'  % np.sum(run_secs)

# Analyze message-log:
msg_counts = {}
pattern = re.compile(r'.*"action":"(\w+)".*"target":"(\w+)".*', flags=re.DOTALL)
with open(msglog_path, 'r') as msglog:
    for line in msglog.readlines():
        # Get message type, e.g. 'say.DATA':
        msg_type = pattern.sub(r'\1.\2', line)

        # Keep count of message type:
        if msg_type not in msg_counts:
            msg_counts[msg_type] = 1
        else:
            msg_counts[msg_type] += 1

# Print message counts:
print
print 'Message type frequencies:'
for msg_type in sorted(msg_counts.keys()):
    print '%7d %s' % (msg_counts[msg_type], msg_type)
