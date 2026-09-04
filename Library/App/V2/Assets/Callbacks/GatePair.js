(function(state) {
    if (state === null || state === undefined) return window.dash_clientside.no_update;
    return !(state.selected && state.selected.length > 1);
})