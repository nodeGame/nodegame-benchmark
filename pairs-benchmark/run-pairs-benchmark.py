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

import os, sys, time, json, csv
import subprocess as sub
import numpy as np

# Load configuration:
config_path = 'conf/config.py'
if len(sys.argv) > 1:
    config_path = sys.argv[1]
config = {}
execfile(config_path, config)

# Begin CSV file:
print 'Writing data to CSV-file:', config['csv_path']
csvfile = open(config['csv_path'], 'w')
msg_counts = {
    'say.DATA': 0,
    'say.GAMECOMMAND': 0,
    'say.HI': 0,
    'say.PCONNECT': 0,
    'say.PDISCONNECT': 0,
    'say.PLAYER_UPDATE': 0,
    'say.SETUP': 0,
    'say.TXT': 0,
    'set.DATA': 0
}
csvwriter = csv.DictWriter(csvfile,
    ['run', 'timestamp', 'room'] + sorted(msg_counts.keys()) +
    ['runtimeA', 'runtimeB'],
    quoting=csv.QUOTE_NONNUMERIC)
csvwriter.writeheader()

# Constants:
fnull = open(os.devnull, 'w')
phantom_call = ['../node_modules/.bin/phantomjs', 'phantom-pairs.js', str(config['num_connections'])]
if config['url']: phantom_call.append(config['url'])

# Do runs:
for run_idx in xrange(1, config['num_runs'] + 1):
    print
    print 'Commencing run', run_idx, '/', config['num_runs']

    # Remove old message-log:
    if os.path.exists(config['msglog_path']):
        print ' * Removing old message log:', config['msglog_path']
        os.remove(config['msglog_path'])
    
    # Start server:
    print ' * Starting the server with the "pairs" game...'
    server_proc = sub.Popen(['node', 'server-pairs.js'], cwd=config['nodegame_path'], stdout=fnull)
    time.sleep(3)
    
    # Call the PhantomJS script:
    print ' * Running the PhantomJS script with', config['num_connections'], 'connections...'
    phantom_proc = sub.Popen(phantom_call, stdout=sub.PIPE, universal_newlines=True)
    
    # Get and analyze the script's output:
    base_ms  = None
    start_ms = np.zeros(config['num_connections'])
    end_ms   = np.zeros(config['num_connections'])
    id_to_page = {}
    while True:
        line = phantom_proc.stdout.readline()
        if not line: break
        line = line.strip()
    
        if config['debug']:
            print ' *** Got line:', line
    
        tokens = line.split()
        # tokens should be of this form:
        #  [ 'Opened','3','at','1379083161743' ], or
        #  [ 'Finished','0','at','1379083169421','with','ID','159318448277190' ],
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
            client_id = tokens[6]
            id_to_page[client_id] = idx
        else:
            raise Exception('Invalid input: "' + line + '"')
    
    if config['debug']:
        print ' *** id_to_page:', id_to_page
    
    phantom_proc.wait()
    print ' * The PhantomJS script has finished.'
    
    # Stop server:
    print ' * Stopping server.'
    server_proc.kill()
    
    run_secs = (end_ms - start_ms) / 1000
    
    # Print runtime statistics:
    
    if config['debug']:
        print
        for idx, secs in enumerate(run_secs):
            print ' *** Runtime for connection %5d:%7.2f s' % (idx, secs)
    
    print
    print ' * Game runtime statistics:'
    print ' *  Minimum:%7.2f  s' % np.min(run_secs)
    print ' *  Maximum:%7.2f  s' % np.max(run_secs)
    print ' *  Average:%7.2f  s' % np.mean(run_secs)
    print ' *  Median:%8.2f  s'  % np.median(run_secs)
    print ' *  Std Dev:%8.3f s'  % np.std(run_secs)
    print ' *  Sum:%8.0f     s'  % np.sum(run_secs)
    
    # Analyze message-log:
    num_rooms = (config['num_connections'] + 1) / 2
    room_msg_counts = [msg_counts.copy() for i in xrange(num_rooms)]
    client_room = {}
    room_players = [None] * num_rooms
    with open(config['msglog_path'], 'r') as msglog:
        # Get room membership of players:
        for line in msglog.readlines():
            # Parse JSON:
            msgobj = json.loads(line)['message']
    
            # Remember room of players and admins:
            if (msgobj['action'] == 'say' and
             msgobj['target'] == 'TXT' and
             msgobj['text'] == 'ROOMNO'):
                msgdata = msgobj['data']
                player_a = msgdata['pids'][0]
                player_b = msgdata['pids'][1]
                roomidx = msgdata['roomNo']
                room_players[roomidx] = (player_a, player_b)
    
                for client_id in msgdata['pids'] + msgdata['aids']:
                    client_room[client_id] = roomidx

        if config['debug']:
            print ' *** room_players: ', room_players
    
        msglog.seek(0)
    
        # Count messages per room:
        for line in msglog.readlines():
            # Parse JSON:
            msgobj = json.loads(line)['message']
    
            # Get message type, e.g. 'say.DATA':
            msg_type = "{0}.{1}".format(msgobj['action'],
                                        msgobj['target'])
    
            if msgobj['from'] in client_room:
                roomidx = client_room[msgobj['from']]
            elif msgobj['to'] in client_room:
                roomidx = client_room[msgobj['to']]
            else:
                continue
    
            # Keep count of message type:
            if msg_type in msg_counts:
                room_msg_counts[roomidx][msg_type] += 1
    
    # Write to CSV-file:
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    for roomidx in xrange(num_rooms):
        playerA, playerB = room_players[roomidx]
        fields = {
            'run': run_idx,
            'timestamp': timestamp,
            'room': roomidx,
            'runtimeA': run_secs[id_to_page[playerA]],
            'runtimeB': run_secs[id_to_page[playerB]]
        }
        fields.update(room_msg_counts[roomidx])

        csvwriter.writerow(fields)

csvfile.close()
