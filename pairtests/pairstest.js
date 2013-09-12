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
            //console.log(msg);
            if (msg === 'Game over') {
                // Game Over
                console.log('Page ' + pgNum + ' finished.');

                countClosed ++;
                if (countClosed >= n) {
                    console.log('All pages finished. Exiting...');
                    phantom.exit();
                }
                else {
                    console.log('Still waiting for ' + (n - countClosed) + ' clients to finish.');
                }
            }
        }

        pg.open(url, function() {
            console.log('Opened page ' + pgNum + '.');
        });
    })(page, i);
}
