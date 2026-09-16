(function(zone) {
    var active = zone || "Browser";
    document.documentElement.setAttribute("data-zone", active);
    if (window.AppZone) window.AppZone.refresh();
    return active;
})