// Usage: phantomjs pairstest.js [num_connections [url]]

var webpage = require('webpage'),
    system = require('system');

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

console.log('Opening ' + n + ' connections to "' + url + '"...');

for (i = 1; i <= n; i ++) {
    page = webpage.create();
    (function(pg, pgNum) {
        pg.onConsoleMessage = function(msg) {
            if (msg === 'Game over') {
                // Game Over
                console.log('Page ' + pgNum + ' finished.');

                pg.close();

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

        setTimeout(function() {
            console.log('Capturing page ' + pgNum + '.');
            pg.render('screenshot_' + pgNum + '.png');
        }, 180 * 1000);
    })(page, i);
}
