(function(rows, data) {
    var nu = window.dash_clientside.no_update;
    if (rows === null || rows === undefined) return [nu, nu, nu, nu, nu];
    var selected = rows.map(function(index) { return (data || [])[index]; }).filter(Boolean);
    var single = selected.length === 1;
    var any = selected.length > 0;
    var enabled = function(row) { return row.Enabled === true || row.Enabled === "true"; };
    var anyEnabled = selected.some(enabled);
    var anyDisabled = selected.some(function(row) { return !enabled(row); });
    var anyRunnable = selected.some(function(row) { return row.Kind !== "Service"; });
    return [!single, !anyRunnable, !anyDisabled, !anyEnabled, !any];
})