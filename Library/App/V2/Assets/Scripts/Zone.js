(function () {
    "use strict";
    var pattern = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/;
    var formatters = {};
    var fields = {year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23"};

    var zone = function () {
        return document.documentElement.getAttribute("data-zone") || "Browser";
    };

    var formatter = function (name) {
        if (formatters[name]) return formatters[name];
        var options = Object.assign({}, fields);
        if (name !== "Browser") options.timeZone = name;
        try { formatters[name] = new Intl.DateTimeFormat("en-CA", options); }
        catch (error) { formatters[name] = new Intl.DateTimeFormat("en-CA", Object.assign({}, fields, {timeZone: "UTC"})); }
        return formatters[name];
    };

    var parts = function (moment) {
        var values = {};
        formatter(zone()).formatToParts(moment).forEach(function (part) { values[part.type] = part.value; });
        return values;
    };

    var epoch = function (seconds) {
        return parts(new Date(seconds * 1000));
    };

    var format = function (text) {
        if (typeof text !== "string" || !pattern.test(text)) return text;
        var moment = new Date(text.replace(" ", "T") + "Z");
        if (isNaN(moment.getTime())) return text;
        var values = parts(moment);
        return values.year + "-" + values.month + "-" + values.day + " " + values.hour + ":" + values.minute + ":" + values.second;
    };

    var write = function (node, text) {
        var child = node.firstChild;
        if (child && child === node.lastChild && child.nodeType === 3) child.nodeValue = text;
        else node.textContent = text;
    };

    var stamp = function (node) {
        if (!node || node.nodeType !== 1 || !node.hasAttribute("data-utc")) return;
        var text = format(node.getAttribute("data-utc"));
        if (node.textContent !== text) write(node, text);
        if (node.hasAttribute("title") && node.getAttribute("title") !== text) node.setAttribute("title", text);
    };

    var apply = function (root) {
        if (!root || root.nodeType !== 1) return;
        stamp(root);
        var nodes = root.querySelectorAll("[data-utc]");
        for (var index = 0; index < nodes.length; index++) stamp(nodes[index]);
    };

    window.AppZone = {pattern: pattern, format: format, epoch: epoch, zone: zone, refresh: function () { apply(document.body); }};

    var observe = function () {
        new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                if (mutation.type === "characterData") stamp(mutation.target.parentElement);
                else if (mutation.type === "attributes") stamp(mutation.target);
                else { stamp(mutation.target); mutation.addedNodes.forEach(apply); }
            });
        }).observe(document.body, {childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["data-utc"]});
        apply(document.body);
    };

    if (document.body) observe();
    else document.addEventListener("DOMContentLoaded", observe);
})();