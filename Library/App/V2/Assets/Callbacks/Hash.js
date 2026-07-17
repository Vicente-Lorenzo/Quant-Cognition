(function(tab) {
    var target = tab ? "#" + tab : "";
    if (window.location.hash === target) return window.dash_clientside.no_update;
    return target;
})