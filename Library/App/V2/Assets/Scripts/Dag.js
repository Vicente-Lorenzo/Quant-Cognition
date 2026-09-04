(function () {
    "use strict";

    var DELAY = 450;

    var open = function (host, uid) {
        window.location.assign(String(host.getAttribute("data-open")).replace(/\/+$/, "") + "/" + encodeURIComponent(uid));
    };

    var wire = function (host, plot) {
        if (plot._dag || typeof plot.on !== "function") return;
        plot._dag = {uid: null, stamp: 0};
        plot.on("plotly_click", function (event) {
            var point = (event.points || [])[0];
            var name = point ? (point.customdata || point.text) : null;
            var uid = name ? String(name) : null;
            if (!uid) return;
            var now = performance.now();
            if (plot._dag.uid === uid && now - plot._dag.stamp < DELAY) return open(host, uid);
            plot._dag = {uid: uid, stamp: now};
        });
    };

    var sweep = function () {
        var hosts = document.querySelectorAll("[data-open]");
        for (var index = 0; index < hosts.length; index++) {
            var plot = hosts[index].querySelector(".js-plotly-plot");
            if (plot) wire(hosts[index], plot);
        }
    };

    var observe = function () {
        sweep();
        new MutationObserver(sweep).observe(document.body, {childList: true, subtree: true});
    };

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", observe);
    else observe();
})();