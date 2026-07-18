(function(rows) {
    if (rows === null || rows === undefined) return window.dash_clientside.no_update;
    return !rows.length;
})