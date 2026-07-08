(function(theme) {
    var current = theme || "dark";
    document.documentElement.setAttribute("data-bs-theme", current);
    return current === "dark" ? "bi bi-moon-stars" : "bi bi-sun";
})