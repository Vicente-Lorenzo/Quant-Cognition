(function() {
    document.addEventListener("dblclick", function(event) {
        if (!event.target.closest || event.target.tagName === "INPUT" || event.target.tagName === "LABEL") return;
        var cell = event.target.closest("td.dash-cell");
        if (!cell) return;
        var wrapper = cell.closest(".table-nav");
        if (!wrapper) return;
        var base = wrapper.getAttribute("data-base");
        if (!base) return;
        var key = wrapper.getAttribute("data-key") || "UID";
        var target = cell.parentElement.querySelector('td.dash-cell[data-dash-column="' + key + '"]');
        if (!target) return;
        var uid = (target.textContent || "").trim();
        if (uid) window.location.assign(base.replace(/\/+$/, "") + "/" + encodeURIComponent(uid));
    });
})();