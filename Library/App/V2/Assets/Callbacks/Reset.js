(function(...states) {
    return states.map(state => {
        let t = Object.assign({}, state || {});
        t.index = (t.index || 0) + 1;
        t.counter = (t.counter || 0) + 1;
        return t;
    });
})