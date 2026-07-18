(function(rows, data) {
    var nu = window.dash_clientside.no_update;
    if (rows === null || rows === undefined) return [nu, nu, nu];
    var selected = rows.map(function(index) { return (data || [])[index]; }).filter(Boolean);
    var status = function(row) { return String(row.Status || ""); };
    var gated = selected.some(function(row) { return /Approving|Reviewing/.test(status(row)); });
    var live = selected.some(function(row) { return /Waiting|Running|Retrying/.test(status(row)); });
    return [!gated, !gated, !live];
})