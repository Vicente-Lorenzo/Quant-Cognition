(function(clicks, current) {
    var open = String(current || "").indexOf("app-nav-open") >= 0;
    return open ? "app-nav" : "app-nav app-nav-open";
})