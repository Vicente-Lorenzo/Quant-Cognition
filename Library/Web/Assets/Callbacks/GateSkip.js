(function(state) {
    if (state === null || state === undefined) return window.dash_clientside.no_update;
    return !(state.rows || []).some(function(row) { return row.Kind !== "Service"; });
})