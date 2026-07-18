(function(rows, data) {
    if (rows === null || rows === undefined) return window.dash_clientside.no_update;
    var selected = rows.map(function(index) { return (data || [])[index]; }).filter(Boolean);
    return !selected.some(function(row) { return row.Kind !== "Service"; });
})