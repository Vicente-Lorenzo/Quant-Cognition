(function(state) {
    var nu = window.dash_clientside.no_update;
    if (state === null || state === undefined) return [nu, nu, nu];
    var selected = state.rows || [];
    var status = function(row) { return String(row.Status || ""); };
    var gated = selected.some(function(row) { return /Approving|Reviewing/.test(status(row)); });
    var live = selected.some(function(row) { return /Waiting|Running|Retrying/.test(status(row)); });
    return [!gated, !gated, !live];
})