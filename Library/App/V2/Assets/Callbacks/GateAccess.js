(function(state) {
    var nu = window.dash_clientside.no_update;
    if (state === null || state === undefined) return [nu, nu, nu];
    var selected = state.rows || [];
    var editable = function(row) { return row.Access === "Edit"; };
    var single = selected.length === 1 && editable(selected[0]);
    var every = selected.length > 0 && selected.every(editable);
    return [!single, !single, !every];
})