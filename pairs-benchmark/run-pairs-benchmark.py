#!/usr/bin/python3
#
# Runs a benchmark of the 'pairs' game.
#
# 'phantomjs' must be in the executable path and 'phantom-pairs.js' must be
# in the current directory.

import sys
import subprocess
import numpy as np

n = 2
url = None

if(len(sys.argv) > 1):
    n = int(sys.argv[1])
if(len(sys.argv) > 2):
    url = sys.argv[2]

# Get the output of the PhantomJS script:
phantom_call = ['phantomjs', 'phantom-pairs.js']
if(n):   phantom_call.append(str(n))
if(url): phantom_call.append(url)
output = subprocess.check_output(phantom_call, universal_newlines=True)

lines_tokens = map(str.split, output.splitlines())

start_ms = np.zeros(n, dtype=np.int)
end_ms   = np.zeros(n, dtype=np.int)

for line in output.splitlines():
    tokens = line.split()
    # tokens should be of this form:
    #  [ 'Opened', '3', 'at', '1379083161743' ],
    #  [ 'Finished', '0', 'at', '1379083169421' ],
    # etc.
    status = tokens[0]
    idx    = int(tokens[1])
    mstime = int(tokens[3])

    if(status == 'Opened'):
        start_ms[idx] = mstime
    elif(status == 'Finished'):
        end_ms[idx]   = mstime
    else:
        raise Exception('Invalid input: "' + line + '"')

run_secs = (end_ms - start_ms) / 1000

#for idx, time in enumerate(run_secs):
#    print('Runtime for connection %5d: %6.2f s' % (idx, time))
#print('--------------------------------------')

print('Minimum: %6.2f s' % np.min(run_secs))
print('Maximum: %6.2f s' % np.max(run_secs))
print('Average: %6.2f s' % np.mean(run_secs))
print('Median:  %6.2f s' % np.median(run_secs))
print('Std Dev: %6.3f s' % np.std(run_secs))
print('Sum:    %7.0f s'  % np.sum(run_secs))
