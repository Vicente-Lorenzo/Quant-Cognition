(function () {
    "use strict";
    var pattern = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/;
    var formatters = {};
    var parts = {year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23"};

    var zone = function () {
        return document.documentElement.getAttribute("data-zone") || "Browser";
    };

    var formatter = function (name) {
        if (formatters[name]) return formatters[name];
        var options = Object.assign({}, parts);
        if (name !== "Browser") options.timeZone = name;
        try { formatters[name] = new Intl.DateTimeFormat("en-CA", options); }
        catch (error) { formatters[name] = new Intl.DateTimeFormat("en-CA", Object.assign({}, parts, {timeZone: "UTC"})); }
        return formatters[name];
    };

    var format = function (text) {
        if (typeof text !== "string" || !pattern.test(text)) return text;
        var moment = new Date(text.replace(" ", "T") + "Z");
        if (isNaN(moment.getTime())) return text;
        var values = {};
        formatter(zone()).formatToParts(moment).forEach(function (part) { values[part.type] = part.value; });
        return values.year + "-" + values.month + "-" + values.day + " " + values.hour + ":" + values.minute + ":" + values.second;
    };

    var apply = function (root) {
        if (!root || root.nodeType !== 1) return;
        if (root.hasAttribute("data-utc")) root.textContent = format(root.getAttribute("data-utc"));
        var nodes = root.querySelectorAll("[data-utc]");
        for (var index = 0; index < nodes.length; index++) nodes[index].textContent = format(nodes[index].getAttribute("data-utc"));
    };

    window.AppZone = {pattern: pattern, format: format, zone: zone, refresh: function () { apply(document.body); }};

    var observe = function () {
        new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) { mutation.addedNodes.forEach(apply); });
        }).observe(document.body, {childList: true, subtree: true});
        apply(document.body);
    };

    if (document.body) observe();
    else document.addEventListener("DOMContentLoaded", observe);
})();