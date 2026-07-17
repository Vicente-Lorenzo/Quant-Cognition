(function() {
    var hash = window.location.hash;
    if (hash) return hash.replace(/^#/, "");
    return window.dash_clientside.no_update;
})