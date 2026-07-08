(function(...states) {
    return states.map(function(state) {
        return JSON.stringify(state === null || state === undefined ? {} : state, null, 2);
    });
})