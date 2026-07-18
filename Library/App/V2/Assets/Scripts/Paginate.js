(function() {
    var fit = function() {
        document.querySelectorAll(".table-fill .dash-table-container").forEach(function(container) {
            var identifier = container.getAttribute("id");
            if (!identifier || identifier[0] !== "{") return;
            var body = container.querySelector(".dash-spreadsheet-inner tbody");
            if (!body || !body.rows || !body.rows.length) return;
            var sample = body.rows[body.rows.length - 1];
            var rowHeight = sample.getBoundingClientRect().height;
            if (!rowHeight) return;
            var page = container.closest(".page") || document.body;
            var bar = page.querySelector(".table-bar");
            var footer = document.querySelector(".app-footer");
            var reserve = (bar ? bar.getBoundingClientRect().height : 0) + (footer ? footer.getBoundingClientRect().height : 0) + 32;
            var available = window.innerHeight - container.querySelector("tbody").getBoundingClientRect().top - reserve;
            var size = Math.max(5, Math.floor(available / rowHeight));
            if (size === container.__pageSize) return;
            container.__pageSize = size;
            try { window.dash_clientside.set_props(JSON.parse(identifier), {page_size: size}); } catch (error) {}
        });
    };
    var pending;
    var schedule = function() { clearTimeout(pending); pending = setTimeout(fit, 250); };
    var relevant = function(node) { return node && node.nodeType === 1 && (node.classList.contains("table-fill") || (node.querySelector && node.querySelector(".table-fill"))); };
    window.addEventListener("resize", schedule);
    new MutationObserver(function(mutations) {
        for (var index = 0; index < mutations.length; index++) {
            var mutation = mutations[index];
            if (mutation.target.closest && mutation.target.closest(".table-fill")) { schedule(); return; }
            for (var added = 0; added < mutation.addedNodes.length; added++) {
                if (relevant(mutation.addedNodes[added])) { schedule(); return; }
            }
        }
    }).observe(document.body, {childList: true, subtree: true});
})();