(function () {
    "use strict";

    var SEPARATOR = " · ";
    var RANGE = /^\s*(-?\d+(?:\.\d+)?)\s*(?:\.\.|-)\s*(-?\d+(?:\.\d+)?)\s*(?::\s*(\d+(?:\.\d+)?)\s*)?$/;
    var MODES = ["Auto", "Range", "List"];

    var pending = {};

    var address = function (cell) {
        return [cell.dataset.strategy, cell.dataset.scope, cell.dataset.kind, cell.dataset.section,
                cell.dataset.stage || "", cell.dataset.name || ""].join("|");
    };

    var publish = function (host) {
        var store = host && host.getAttribute("data-store");
        if (!store || !window.dash_clientside || !window.dash_clientside.set_props) return;
        try { window.dash_clientside.set_props(JSON.parse(store), {data: Object.assign({}, pending)}); } catch (error) {}
    };

    var numeric = function (text) {
        return text !== "" && !isNaN(Number(text));
    };

    var kindOf = function (slot) {
        var text = (slot || "").trim();
        if (text.toLowerCase() === "auto") return "Auto";
        if (RANGE.test(text)) return "Range";
        return "List";
    };

    var element = function (tag, className, parent, text) {
        var node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        if (parent) parent.appendChild(node);
        return node;
    };

    var token = function (text, cell, editor) {
        var chip = element("span", "grid-chip", null, text);
        var kill = element("i", "grid-chip-kill", chip, "×");
        kill.onclick = function (event) {
            event.stopPropagation();
            chip.remove();
            harvest(cell, editor);
        };
        return chip;
    };

    var counted = function (from, to, step) {
        var span = Number(to) - Number(from), stride = Number(step);
        if (!isFinite(span) || !isFinite(stride) || stride <= 0 || span < 0) return "";
        return String(Math.floor(span / stride + 1e-9) + 1) + " values";
    };

    var listSlot = function (group, slot, cell, editor) {
        var body = element("span", "grid-slot-body", group);
        (slot || "").split("|").filter(function (option) { return option !== ""; })
            .forEach(function (option) { body.appendChild(token(option, cell, editor)); });
        var add = element("span", "grid-chip grid-chip-add", body, "+");
        add.onclick = function (event) {
            event.stopPropagation();
            if (body.querySelector(".grid-chip-input")) return;
            var entry = element("input", "grid-chip-input", null);
            entry.placeholder = "value";
            body.insertBefore(entry, add);
            entry.focus();
            var settle = function (keep) {
                entry.onblur = null;
                var value = entry.value.trim();
                entry.remove();
                if (!keep || value === "") return;
                body.insertBefore(token(value, cell, editor), add);
                harvest(cell, editor);
            };
            entry.onblur = function () { settle(true); };
            entry.onkeydown = function (stroke) {
                stroke.stopPropagation();
                if (stroke.key === "Enter") { stroke.preventDefault(); settle(true); }
                if (stroke.key === "Escape") { stroke.preventDefault(); settle(false); }
            };
        };
    };

    var rangeSlot = function (group, slot, cell, editor) {
        var found = RANGE.exec(slot || "") || [null, "", "", ""];
        var body = element("span", "grid-slot-body grid-range", group);
        var tally = element("span", "grid-range-count", null);
        var fields = {};
        [["from", "From", found[1]], ["to", "To", found[2]], ["step", "Step", found[3] || "1"]].forEach(function (spec) {
            var field = element("label", "grid-range-field", body);
            element("span", "grid-range-label", field, spec[1]);
            var input = element("input", "grid-range-input", field);
            input.type = "number";
            input.step = "any";
            input.value = spec[2];
            input.onclick = function (event) { event.stopPropagation(); };
            input.oninput = function () {
                tally.textContent = counted(fields.from.value, fields.to.value, fields.step.value);
                harvest(cell, editor);
            };
            input.onkeydown = function (stroke) { stroke.stopPropagation(); };
            fields[spec[0]] = input;
        });
        body.appendChild(tally);
        tally.textContent = counted(fields.from.value, fields.to.value, fields.step.value);
        body.__read__ = function () {
            var from = fields.from.value.trim(), to = fields.to.value.trim(), step = fields.step.value.trim();
            if (from === "" || to === "") return "";
            return from + ".." + to + ":" + (step === "" ? "1" : step);
        };
    };

    var autoSlot = function (group, cell) {
        var body = element("span", "grid-slot-body grid-auto", group);
        element("span", "grid-chip grid-chip-auto", body, "Auto");
        element("span", "grid-auto-note", body, "uses the indicator's declared ladder");
        body.__read__ = function () { return "Auto"; };
    };

    var slotEditor = function (group, slot, cell, editor) {
        var mode = group.dataset.mode;
        [...group.querySelectorAll(".grid-slot-body")].forEach(function (node) { node.remove(); });
        if (mode === "Range") rangeSlot(group, slot, cell, editor);
        else if (mode === "Auto") autoSlot(group, cell);
        else listSlot(group, slot, cell, editor);
    };

    var chips = function (cell, editor) {
        editor.innerHTML = "";
        (cell.dataset.value || "").split(SEPARATOR).forEach(function (slot) {
            var group = element("span", "grid-slot", editor);
            group.dataset.mode = kindOf(slot);
            var picker = element("span", "grid-modes", group);
            MODES.forEach(function (mode) {
                var pick = element("span", "grid-mode" + (group.dataset.mode === mode ? " grid-mode-on" : ""), picker, mode);
                pick.onclick = function (event) {
                    event.stopPropagation();
                    group.dataset.mode = mode;
                    [...picker.children].forEach(function (node) { node.classList.toggle("grid-mode-on", node === pick); });
                    slotEditor(group, mode === kindOf(slot) ? slot : "", cell, editor);
                    harvest(cell, editor);
                };
            });
            slotEditor(group, slot, cell, editor);
        });
    };

    var harvest = function (cell, editor) {
        var slots = [];
        editor.querySelectorAll(".grid-slot").forEach(function (group) {
            var body = group.querySelector(".grid-slot-body");
            if (body && body.__read__) { slots.push(body.__read__()); return; }
            var options = [];
            group.querySelectorAll(".grid-chip:not(.grid-chip-add)").forEach(function (chip) {
                options.push(chip.firstChild.textContent.trim());
            });
            slots.push(options.join("|"));
        });
        var text = slots.filter(function (slot) { return slot !== ""; }).join(SEPARATOR);
        cell.dataset.value = text;
        mark(cell, text);
    };

    var mark = function (cell, text) {
        pending[address(cell)] = text;
        cell.classList.add("grid-cell-pending");
        var dot = cell.querySelector(".grid-dot");
        if (dot) dot.className = "grid-dot cell-here";
        publish(cell.closest(".grid-host"));
    };

    var scalar = function (cell, editor) {
        var input = element("input", "grid-input", editor);
        input.type = numeric(cell.dataset.value) ? "number" : "text";
        if (input.type === "number") input.step = "any";
        input.value = cell.dataset.value || "";
        input.focus();
        input.select();
        var settle = function (keep) {
            input.onblur = null;
            if (!keep) { close(cell, cell.dataset.value || ""); return; }
            var text = input.value.trim();
            cell.dataset.value = text;
            close(cell, text);
            mark(cell, text);
        };
        input.onblur = function () { settle(true); };
        input.onkeydown = function (event) {
            if (event.key === "Enter") { event.preventDefault(); settle(true); }
            if (event.key === "Escape") { event.preventDefault(); settle(false); }
        };
    };

    var paint = function (host, text, cell) {
        host.innerHTML = "";
        if (!text) { host.textContent = "—"; return; }
        if (cell.dataset.kind !== "Optimization") { host.textContent = text; return; }
        text.split(SEPARATOR).forEach(function (slot, index) {
            if (index) element("span", "grid-slot-sep", host, "·");
            var trimmed = slot.trim();
            if (trimmed.toLowerCase() === "auto") { element("span", "grid-pill grid-pill-auto", host, "Auto"); return; }
            var found = RANGE.exec(trimmed);
            if (found) {
                element("span", "grid-pill grid-pill-range", host,
                        found[1] + " → " + found[2] + (found[3] ? " · " + found[3] : ""));
                return;
            }
            trimmed.split("|").filter(function (option) { return option !== ""; })
                .forEach(function (option) { element("span", "grid-pill", host, option); });
        });
    };

    var close = function (cell, text) {
        cell.classList.remove("grid-cell-editing");
        var editor = cell.querySelector(".grid-editor");
        if (editor) editor.remove();
        var value = cell.querySelector(".grid-value");
        if (value) { paint(value, text, cell); value.style.display = ""; }
    };

    var open = function (cell) {
        if (cell.classList.contains("grid-cell-editing")) return;
        [...document.querySelectorAll(".grid-cell-editing")].forEach(function (other) {
            close(other, other.dataset.value || "");
        });
        cell.classList.add("grid-cell-editing");
        var value = cell.querySelector(".grid-value");
        if (value) value.style.display = "none";
        var editor = element("span", "grid-editor", cell);
        if (cell.dataset.kind === "Optimization") chips(cell, editor);
        else scalar(cell, editor);
    };

    var fold = function (node, kind) {
        if (kind === "band") node.closest(".grid-band").classList.toggle("grid-folded");
        else if (kind === "section") {
            var folded = node.classList.toggle("grid-folded");
            var cursor = node.nextElementSibling;
            while (cursor && !cursor.classList.contains("grid-section")) {
                cursor.style.display = folded ? "none" : "";
                cursor = cursor.nextElementSibling;
            }
        } else if (kind === "column") {
            var column = node.dataset.column;
            var host = node.closest(".grid");
            var hidden = node.classList.toggle("grid-folded");
            host.querySelectorAll('[data-column="' + column + '"]').forEach(function (cell) {
                cell.classList.toggle("grid-column-folded", hidden);
            });
        }
    };

    var wire = function (host) {
        if (host.__wired__) return;
        host.__wired__ = true;
        host.addEventListener("click", function (event) {
            var folder = event.target.closest("[data-fold]");
            if (folder) { fold(folder, folder.dataset.fold); return; }
            var cell = event.target.closest(".grid-cell");
            if (!cell || cell.classList.contains("grid-column-folded")) return;
            if (cell.classList.contains("grid-cell-void")) return;
            open(cell);
        });
    };

    var scan = function () {
        document.querySelectorAll(".grid-host").forEach(wire);
    };

    var observer = new MutationObserver(scan);
    var start = function () {
        scan();
        observer.observe(document.body, {childList: true, subtree: true});
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
    else start();

    window.QuantGrid = {reset: function () { pending = {}; }};
})();