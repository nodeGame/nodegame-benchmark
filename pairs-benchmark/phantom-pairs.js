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

for (i = 0; i < n; i ++) {
    page = webpage.create();
    (function(pg, pgNum) {
        pg.onConsoleMessage = function(msg) {
            //console.log(msg);
            if (msg === 'Game over') {
                // Game Over
                console.log('Finished ' + pgNum + ' at ' + (new Date).getTime());

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
