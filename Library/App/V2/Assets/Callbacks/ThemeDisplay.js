(function(theme) {
    var mode = theme || "system";
    var icon = mode === "system" ? "bi bi-circle-half" : (mode === "dark" ? "bi bi-moon-stars" : "bi bi-sun");
    var label = mode.charAt(0).toUpperCase() + mode.slice(1);
    return [icon, label];
})