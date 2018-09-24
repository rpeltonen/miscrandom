var stations = [];
stations.push({x: 0, y: 0, reach: 10});
stations.push({x: 20, y: 20, reach: 5});
stations.push({x: 10, y: 0, reach: 12});

var devices = [];
devices.push({x: 0, y: 0});
devices.push({x: 100, y: 100});
devices.push({x: 15, y: 10});
devices.push({x: 18, y: 18});

var output = "";

devices.forEach(function(device) {
    output += findBestStation(stations, device.x, device.y) + "<br>";
});

document.write(output);

function findBestStation(stations, x, y) {
    var bestStation = null;
    
    stations.forEach(function(station) {
        var power = getSignalPower(x, y, station);
        if (power > 0 && (bestStation == null || power > bestStation.power)) {
            bestStation = {x: station.x, y: station.y, power: power};
        }
    });
    
    if (bestStation != null) {
        return `Best link station for point ${x},${y} is ${bestStation.x},${bestStation.y} with power ${bestStation.power}`;
    } else {
        return `No link station within reach for point ${x},${y}`;
    }
}

function getSignalPower(x, y, station) {
    var distanceToStation = getDistanceToPoint(x, y, station.x, station.y);
    if (distanceToStation > station.reach) {
        return 0;
    } else {
        return Math.pow(station.reach - distanceToStation, 2);
    }
}

function getDistanceToPoint(x1, y1, x2, y2) {
    /* Using Pythagorean theorem */
    return Math.sqrt(Math.pow(Math.abs(x1 - x2), 2) + Math.pow(Math.abs(y1 - y2), 2));
}
