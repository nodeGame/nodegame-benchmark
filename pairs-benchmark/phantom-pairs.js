// Usage: phantomjs phantom-pairs.js [num_connections [url]]

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

if (n <= 0) phantom.exit();

for (i = 0; i < n; i ++) {
    page = webpage.create();
    (function(pg, pgNum) {
        var clientId;

        pg.onConsoleMessage = function(msg) {
            if (msg === 'Game over') {
                // Game Over
                clientId = pg.evaluate(function() { return node.player.id; });
                console.log('Finished ' + pgNum + ' at ' +
                    (new Date).getTime() + ' with ID ' + clientId);

                countClosed ++;
                if (countClosed >= n) {
                    phantom.exit();
                }
            }
        }

        pg.open(url, function() {
            console.log('Opened ' + pgNum + ' at ' + (new Date).getTime());
        });
    })(page, i);
}
