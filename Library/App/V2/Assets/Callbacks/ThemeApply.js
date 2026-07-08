(function(theme) {
    var mode = theme || "system";
    window.__themeMode = mode;
    var media = window.matchMedia("(prefers-color-scheme: dark)");
    var dark = (mode === "dark") || (mode === "system" && media.matches);
    document.documentElement.setAttribute("data-bs-theme", dark ? "dark" : "light");
    if (!window.__themeListener) {
        window.__themeListener = true;
        media.addEventListener("change", function(event) {
            if (window.__themeMode === "system") document.documentElement.setAttribute("data-bs-theme", event.matches ? "dark" : "light");
        });
    }
    return mode === "system" ? "bi bi-circle-half" : (dark ? "bi bi-moon-stars" : "bi bi-sun");
})