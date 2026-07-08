(function(clicks, value) {
    try {
        return JSON.parse(value);
    } catch (error) {
        return window.dash_clientside.no_update;
    }
})