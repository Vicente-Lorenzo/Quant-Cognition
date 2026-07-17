(function(clicks, config, rows, data) {
    var nu = window.dash_clientside.no_update;
    if (!config || config.navigable === false) return nu;
    if (!rows || !rows.length || !data) return nu;
    var key = config.key || "UID";
    var base = (config.base || window.location.pathname).replace(/\/+$/, "");
    var uids = [];
    for (var i = 0; i < rows.length; i++) {
        var row = data[rows[i]];
        if (row && row[key] != null) uids.push(row[key]);
    }
    if (!uids.length) return nu;
    if (uids.length === 1) return base + "/" + encodeURIComponent(uids[0]);
    for (var j = 0; j < uids.length; j++) window.open(base + "/" + encodeURIComponent(uids[j]), "_blank");
    return nu;
})