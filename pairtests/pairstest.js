// Usage: phantomjs pairstest.js [num_connections [url]]

var webpage = require('webpage'),
    system = require('system');

function logObject(obj) {
    for (var key in obj) {
        if (obj.hasOwnProperty(key)) {
            console.log('*', key, ':', obj[key]);
        }
    }
}

var url = 'http://localhost:8080/pairs/';
var n = 2;
var i, page;
var countClosed = 0;

if (system.args.length >= 2) {
    n = +system.args[1];
}
if (system.args.length >= 3) {
    url = system.args[2];
}

// Disable cookies
phantom.cookiesEnabled = false;

console.log('Opening ' + n + ' connections to "' + url + '"...');

for (i = 1; i <= n; i ++) {
    page = webpage.create();
    (function(pg, pgNum) {
        var timeoutId;

        pg.onConsoleMessage = function(msg) {
            if (msg === 'Game over') {
                // Game Over
                console.log('Page ' + pgNum + ' finished.');

                // Don't capture the screen of the finished client
                clearTimeout(timeoutId);

                countClosed ++;
                if (countClosed >= n) {
                    console.log('All pages finished. Exiting...');
                    phantom.exit();
                }
                else {
                    console.log('Still waiting for ' + (n - countClosed) + ' clients to finish.');
                }
            }

            if (msg.toLowerCase().indexOf('error') >= 0) {
                // Error
                console.log('Error message: ' + msg);
            }
        };

        pg.onError = function(msg, trace) {
            var msgStack = ['ERROR: ' + msg];
            if (trace && trace.length) {
                msgStack.push('TRACE:');
                trace.forEach(function(t) {
                    msgStack.push(' -> ' + t.file + ': ' + t.line + (t.function ? ' (in function "' + t.function + '")' : ''));
                });
            }
            console.error(msgStack.join('\n'));    var msgStack = ['ERROR: ' + msg];
        };

        pg.open(url, function() {
            console.log('Opened page ' + pgNum + '.');
        });

        timeoutId = setTimeout(function() {
            console.log();
            console.log('Capturing page ' + pgNum + '.');
            pg.render('screenshot_' + pgNum + '.png');

            stateObj = pg.evaluate(function() {
                return {
                    player: node.player,
                    pl:     node.game.pl
                };
            });

            console.log('player: ');
            logObject(stateObj.player);
            console.log('player.stage: ');
            logObject(stateObj.player.stage);
            console.log('pl.db: ');
            logObject(stateObj.pl.db);
            console.log();
        }, 240 * 1000);
    })(page, i);
}
