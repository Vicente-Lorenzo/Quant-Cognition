(function () {
    "use strict";

    var SLACK = 24;
    var STAGES = ["app-header-tight", "app-header-lean", "app-header-compact"];

    var close = function (nav) {
        if (nav && String(nav.className).indexOf("app-nav-open") >= 0) nav.className = "app-nav";
    };

    var measure = function () {
        var header = document.querySelector(".app-header");
        var nav = header && header.querySelector(".app-nav");
        var inner = nav && nav.querySelector(".app-nav-inner");
        if (!header || !inner) return;
        var brand = header.querySelector(".app-brand");
        var menu = header.querySelector(".app-menu");
        var toggle = header.querySelector(".app-nav-toggle");
        var was = header.classList.contains("app-header-compact");
        STAGES.forEach(function (stage) { header.classList.remove(stage); });
        var fits = function () {
            return (brand ? brand.getBoundingClientRect().width : 0)
                 + (menu ? menu.getBoundingClientRect().width : 0)
                 + inner.scrollWidth + SLACK <= header.clientWidth;
        };
        for (var index = 0; index < STAGES.length && !fits(); index++) header.classList.add(STAGES[index]);
        if (!header.classList.contains("app-header-compact") || !was) close(nav);
    };

    var schedule = function () {
        cancelAnimationFrame(schedule.frame);
        schedule.frame = requestAnimationFrame(measure);
    };

    var observe = function () {
        schedule();
        window.addEventListener("resize", schedule);
        window.addEventListener("orientationchange", schedule);
        new MutationObserver(schedule).observe(document.body, {childList: true, subtree: true});
        document.addEventListener("click", function (event) {
            var nav = document.querySelector(".app-nav-open");
            if (!nav) return;
            if (event.target.closest && event.target.closest(".app-nav-toggle")) return;
            close(nav);
        }, true);
    };

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", observe);
    else observe();
})();