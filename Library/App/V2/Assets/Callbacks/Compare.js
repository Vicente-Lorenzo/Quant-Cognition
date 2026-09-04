(function(clicks, state) {
    var nu = window.dash_clientside.no_update;
    if (!state || !state.base || !state.selected || state.selected.length < 2) return nu;
    var base = String(state.base).replace(/\/+$/, "");
    return base + "/" + state.selected.join("+");
})