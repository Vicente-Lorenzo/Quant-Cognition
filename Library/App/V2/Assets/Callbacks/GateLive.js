(function(state) {
    if (state === null || state === undefined) return window.dash_clientside.no_update;
    var rows = state.rows || [];
    return !rows.some(function(row) { return /Waiting|Running|Retrying/.test(String(row.Status || "")); });
})