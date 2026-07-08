(function(clicks, theme) {
    var order = ["light", "dark", "system"];
    var index = order.indexOf(theme || "system");
    return order[(index + 1) % order.length];
})