(function(...states) {
    var triggers = states.map(function(state) {
        var t = Object.assign({}, state || {});
        t.index = (t.index || 0) + 1;
        t.counter = (t.counter || 0) + 1;
        return t;
    });
    setTimeout(function() { window.location.reload(); }, 300);
    return triggers;
})