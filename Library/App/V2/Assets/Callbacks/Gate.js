(function(state) {
    var nu = window.dash_clientside.no_update;
    if (state === null || state === undefined) return [nu, nu, nu];
    var selected = state.rows || [];
    var single = selected.length === 1;
    var any = selected.length > 0;
    var anyRunnable = selected.some(function(row) { return row.Kind !== "Service"; });
    return [!single, !anyRunnable, !any];
})