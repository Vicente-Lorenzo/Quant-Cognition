(function () {
    "use strict";

    var TOKENS = ["plane", "surface", "ink", "secondary", "muted", "grid", "border", "up", "down", "datum", "band",
                  "accent", "equity", "balance", "entry", "exit", "long", "short", "traded",
                  "benchmark0", "benchmark1", "benchmark2", "benchmark3"];

    var spaces = {};
    var hosts = new WeakMap();
    var pending = new WeakMap();

    var noop = function () {};

    var palette = function (node, override) {
        var styles = getComputedStyle(node);
        var theme = {};
        for (var index = 0; index < TOKENS.length; index++) {
            var token = TOKENS[index];
            var variable = "--lw-" + token.replace(/([0-9]+)$/, "-$1");
            theme[token] = (styles.getPropertyValue(variable) || "").trim() || "#868993";
        }
        if (override) for (var key in override) if (override[key]) theme[key] = override[key];
        theme.font = (styles.fontFamily || "system-ui, sans-serif");
        return theme;
    };

    var tint = function (theme, value, fallback) {
        if (!value) return theme[fallback || "accent"];
        if (value.charAt(0) === "#" || value.indexOf("rgb") === 0 || value.indexOf("hsl") === 0) return value;
        return theme[value] || value;
    };

    var ticks = function (pane) {
        var stamps = {};
        (pane.series || []).forEach(function (series) {
            (series.data || []).forEach(function (point) { stamps[point.time] = true; });
        });
        return Object.keys(stamps).map(Number).sort(function (a, b) { return a - b; }).map(function (time) { return {time: time}; });
    };

    var format = function (kind, value) {
        if (value === undefined || value === null) return "–";
        if (kind === "signal") return value.toFixed(4);
        if (kind === "volume") return Math.round(value).toLocaleString();
        if (kind === "price") return value.toFixed(5);
        if (kind === "percent") return value.toFixed(2) + "%";
        if (kind === "integer") return Math.round(value).toLocaleString();
        return value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
    };

    var space = function (name) {
        if (!spaces[name]) spaces[name] = {charts: [], tables: [], priced: [], deals: [], spans: {}, markers: true, dealmap: false, lines: []};
        return spaces[name];
    };

    var publish = function (outbound, payload) {
        if (!outbound || !window.dash_clientside || !window.dash_clientside.set_props) return;
        try { window.dash_clientside.set_props(outbound, {data: payload}); } catch (error) {}
    };

    var element = function (tag, className, parent) {
        var node = document.createElement(tag);
        if (className) node.className = className;
        if (parent) parent.appendChild(node);
        return node;
    };

    var stamps = function (series) {
        if (!series.__stamps__) series.__stamps__ = LightweightCharts.createSeriesMarkers(series, []);
        return series.__stamps__;
    };

    var clear = function (state) {
        state.lines.forEach(function (entry) { try { entry.series.removePriceLine(entry.line); } catch (error) {} });
        state.lines = [];
        state.priced.forEach(function (series) { stamps(series).setMarkers(state.markers ? series.__markers__ : []); });
    };

    var highlight = function (state, keys, theme) {
        clear(state);
        var chosen = keys.map(function (key) { return state.spans[key]; }).filter(Boolean);
        if (!chosen.length) return;
        var picked = {};
        keys.forEach(function (key) { picked[String(key)] = true; });
        state.priced.forEach(function (series) {
            stamps(series).setMarkers(series.__markers__.map(function (marker) {
                if (picked[String(marker.uid)]) return Object.assign({}, marker, {size: 2.4, text: marker.shape === "square" ? "EXIT" : "ENTRY"});
                return Object.assign({}, marker, {color: theme.border});
            }));
        });
        var colour = chosen[0].direction === "Buy" ? theme.up : theme.down;
        chosen.forEach(function (span) {
            state.priced.forEach(function (series) {
                [["entryPrice", 0], ["exitPrice", 2]].forEach(function (entry) {
                    var price = span[entry[0]];
                    if (price === null || price === undefined) return;
                    state.lines.push({series: series, line: series.createPriceLine({price: price, color: colour, lineWidth: 1, lineStyle: entry[1],
                                                                                   axisLabelVisible: true, axisLabelColor: colour, axisLabelTextColor: theme.plane})});
                });
            });
        });
        var starts = chosen.map(function (span) { return span.entry; });
        var ends = chosen.map(function (span) { return span.exit || span.entry; });
        var from = Math.min.apply(null, starts), to = Math.max.apply(null, ends);
        var pad = Math.max((to - from) * 1.5, 86400);
        state.charts.forEach(function (chart) { chart.timeScale().setVisibleRange({from: from - pad, to: to + pad}); });
    };

    var chart = function (host, data) {
        var theme = palette(host, data.theme);
        var body = host.querySelector(":scope > .lightweight-body");
        var state = space(host.getAttribute("data-workspace") || "default");
        body.innerHTML = "";
        state.markers = !(data.defaults && data.defaults.markers === false);
        state.dealmap = !!(data.defaults && data.defaults.deals);
        state.sides = {Buy: state.dealmap, Sell: state.dealmap};
        var charts = [], registry = [], priced = [], dealSeries = [], frames = [], watchers = [];
        var refreshAxis = function () {
            var live = frames.filter(function (frame) { return !frame.section.classList.contains("lw-collapsed"); });
            var trailing = {};
            live.forEach(function (frame) { trailing[frame.scale] = frame; });
            frames.forEach(function (frame) {
                frame.instance.applyOptions({timeScale: {visible: trailing[frame.scale] === frame}});
            });
        };
        (data.panes || []).forEach(function (pane) {
            var section = element("section", "lw-pane", body);
            section.style.flex = (pane.flex || 20) + " 1 0";
            var bar = element("div", "lw-bar", section);
            var toggle = element("span", "lw-collapse", bar);
            element("span", "lw-icon lw-icon-chevron", toggle);
            toggle.title = "Collapse or expand this panel";
            var label = element("span", "lw-title", bar);
            label.textContent = pane.title || "";
            var chips = element("span", "lw-chips", bar);
            var saver = element("span", "lw-save", bar);
            element("span", "lw-icon lw-icon-image", saver);
            element("span", "lw-save-text", saver).textContent = "PNG";
            saver.title = "Save this panel as a PNG image";
            var holder = element("div", "lw-chart", section);
            var margins = pane.margins || {top: 0.10, bottom: 0.08};
            var ordinal = pane.scale === "index";
            var spine = [];
            var marks = pane.labels || [];
            var ticker = function (value) {
                var position = Math.round(value / 86400);
                var label = marks[position - 1];
                return label === undefined ? String(position) : String(label);
            };
            var instance = LightweightCharts.createChart(holder, {
                autoSize: true,
                layout: {background: {type: "solid", color: theme.surface}, textColor: theme.secondary, fontFamily: theme.font, fontSize: 11, attributionLogo: false},
                grid: {vertLines: {color: theme.grid}, horzLines: {color: theme.grid}},
                rightPriceScale: {borderColor: theme.border, scaleMargins: margins, minimumWidth: 84},
                leftPriceScale: {borderColor: theme.border, scaleMargins: pane.underlay || margins, visible: false},
                timeScale: {borderColor: theme.border, timeVisible: !ordinal, secondsVisible: false,
                            rightOffset: ordinal ? 0 : 4, visible: !!pane.last, minBarSpacing: 0.02,
                            tickMarkFormatter: ordinal ? function (value) { return ticker(value); } : undefined},
                crosshair: {mode: LightweightCharts.CrosshairMode.Normal,
                            vertLine: {color: theme.muted, width: 1, style: 3, labelBackgroundColor: theme.border},
                            horzLine: {color: theme.muted, width: 1, style: 3, labelBackgroundColor: theme.border}},
                handleScale: {axisPressedMouseMove: {time: true, price: false}},
                localization: {priceFormatter: function (value) { return format(pane.format, value); },
                               timeFormatter: ordinal ? function (value) { return ticker(value); } : undefined}
            });
            instance.__scale__ = pane.scale || "time";
            saver.onclick = function () {
                if (!instance.takeScreenshot) return;
                window.Quant.save(window.Quant.blob(instance.takeScreenshot()), (pane.id || "panel") + ".png");
            };
            charts.push(instance);
            if (window.ResizeObserver) {
                var watcher = new ResizeObserver(function () {
                    if (holder.clientWidth >= 2) instance.timeScale().fitContent();
                });
                watcher.observe(holder);
                watchers.push(watcher);
            }
            frames.push({section: section, instance: instance, flex: pane.flex || 20, scale: pane.scale || "time"});
            toggle.onclick = function () {
                var collapsed = section.classList.toggle("lw-collapsed");
                section.style.flex = collapsed ? "0 0 auto" : (pane.flex || 20) + " 1 0";
                refreshAxis();
            };
            var backboneOptions = {lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false};
            if (pane.bound) backboneOptions.autoscaleInfoProvider = function () { return {priceRange: {minValue: -pane.bound, maxValue: pane.bound}}; };
            var backbone = instance.addSeries(LightweightCharts.LineSeries, backboneOptions);
            spine = ordinal ? ticks(pane) : (data.timeline || []);
            if (spine.length) backbone.setData(spine);
            instance.__primary__ = backbone;
            var bandOwner = null, bandHandles = [];
            var bandState = (pane.lines || []).map(function () { return true; });
            var renderBands = function () {
                if (!bandOwner) return;
                bandHandles.forEach(function (handle) { try { bandOwner.series.removePriceLine(handle); } catch (error) {} });
                bandHandles = [];
                (pane.lines || []).forEach(function (level, index) {
                    if (!bandState[index]) return;
                    var colour = tint(theme, level.color, "band");
                    bandHandles.push(bandOwner.series.createPriceLine({price: level.price, color: colour, lineWidth: 1, lineStyle: level.style === undefined ? 2 : level.style,
                                                                      title: level.title, axisLabelVisible: true, axisLabelColor: colour, axisLabelTextColor: theme.plane}));
                });
                if (pane.datum !== undefined && pane.datum !== null) {
                    bandHandles.push(bandOwner.series.createPriceLine({price: pane.datum, color: theme.datum, lineWidth: 1, lineStyle: 0,
                                                                      axisLabelVisible: true, axisLabelColor: theme.border, axisLabelTextColor: theme.ink}));
                }
            };
            (pane.lines || []).forEach(function (level, index) {
                var chip = element("span", "lw-chip", chips);
                var colour = tint(theme, level.color, "band");
                chip.innerHTML = '<span class="lw-swatch" style="background:' + colour + '"></span><span></span> <b></b>';
                chip.children[1].textContent = level.title || "Level";
                chip.children[2].textContent = format(pane.format, level.price);
                chip.onclick = function () { bandState[index] = !bandState[index]; chip.classList.toggle("off", !bandState[index]); renderBands(); };
            });
            var buildSeries = function (spec, kind) {
                var base = {priceLineVisible: false, lastValueVisible: false, priceScaleId: spec.axis === "left" ? "left" : "right"};
                if (spec.axis !== "left" && pane.bound) base.autoscaleInfoProvider = function () { return {priceRange: {minValue: -pane.bound, maxValue: pane.bound}}; };
                var colour = tint(theme, spec.color);
                var series;
                if (kind === "candlestick") {
                    series = instance.addSeries(LightweightCharts.CandlestickSeries, Object.assign({}, base, {upColor: theme.up, downColor: theme.down, borderUpColor: theme.up,
                                                                                    borderDownColor: theme.down, wickUpColor: theme.up, wickDownColor: theme.down}));
                    series.setData(spec.data);
                } else if (kind === "bar") {
                    series = instance.addSeries(LightweightCharts.BarSeries, Object.assign({}, base, {upColor: theme.up, downColor: theme.down}));
                    series.setData(spec.data);
                } else if (kind === "histogram") {
                    series = instance.addSeries(LightweightCharts.HistogramSeries, Object.assign({}, base, {color: colour}));
                    series.setData(spec.data.map(function (point) { return {time: point.time, value: point.value, color: point.color ? tint(theme, point.color) : ((point.value || 0) >= 0 ? theme.up : theme.down)}; }));
                } else if (kind === "area") {
                    series = instance.addSeries(LightweightCharts.AreaSeries, Object.assign({}, base, {lineColor: colour, topColor: colour, bottomColor: "transparent", lineWidth: spec.width || 2}));
                    series.setData(spec.data);
                } else if (kind === "baseline") {
                    series = instance.addSeries(LightweightCharts.BaselineSeries, Object.assign({}, base, {topLineColor: theme.up, bottomLineColor: theme.down, lineWidth: spec.width || 2}));
                    series.setData(spec.data);
                } else {
                    series = instance.addSeries(LightweightCharts.LineSeries, Object.assign({}, base, {color: colour, lineWidth: spec.width || 2, lineType: 0}));
                    series.setData(spec.data);
                }
                if (spec.markers && spec.markers.length) {
                    series.__markers__ = spec.markers.map(function (marker) { return Object.assign({}, marker, {color: tint(theme, marker.color, "up")}); });
                    stamps(series).setMarkers(state.markers ? series.__markers__ : []);
                }
                if (spec.visible === false) series.applyOptions({visible: false});
                return series;
            };
            (pane.series || []).forEach(function (spec) {
                var series = buildSeries(spec, spec.type);
                if (spec.markers && spec.markers.length) priced.push(series);
                var lookup = new Map();
                (spec.data || []).forEach(function (point) { lookup.set(point.time, point.close !== undefined ? point.close : point.value); });
                if (!instance.__lookup__) instance.__lookup__ = lookup;
                var entry = {series: series, chart: instance, lookup: lookup, format: pane.format, type: spec.type};
                if (!bandOwner && spec.axis !== "left") { bandOwner = entry; renderBands(); }
                var chip = element("span", "lw-chip" + (spec.visible === false ? " off" : ""), chips);
                chip.innerHTML = '<span class="lw-swatch"></span><span></span> <b></b>';
                chip.children[0].style.background = spec.type === "candlestick" ? theme.up : tint(theme, spec.color);
                chip.children[1].textContent = spec.name || spec.key;
                chip.onclick = function () {
                    var on = entry.series.options().visible !== false;
                    entry.series.applyOptions({visible: !on});
                    chip.classList.toggle("off", on);
                };
                entry.chip = chip;
                registry.push(entry);
                if (spec.toggle) {
                    var kind = spec.type;
                    var toggle = element("span", "lw-chip", chips);
                    var paint = function () {
                        toggle.innerHTML = "<span></span> <b></b>";
                        toggle.children[0].textContent = spec.name || spec.key;
                        toggle.children[1].textContent = kind === "histogram" ? "▮ Bars" : "▬ Lines";
                    };
                    paint();
                    toggle.onclick = function () {
                        var visible = entry.series.options().visible !== false;
                        instance.removeSeries(entry.series);
                        kind = kind === "line" ? "histogram" : "line";
                        entry.series = buildSeries(Object.assign({}, spec, {visible: visible}), kind);
                        if (entry === bandOwner) { bandHandles = []; renderBands(); }
                        paint();
                    };
                }
            });
            if (pane.id === "price") {
                if (priced.length) {
                    var markerChip = element("span", "lw-chip" + (state.markers ? "" : " off"), chips);
                    markerChip.innerHTML = '<span class="lw-swatch" style="background:' + theme.secondary + '"></span><span>Markers</span>';
                    markerChip.onclick = function () {
                        state.markers = !state.markers;
                        priced.forEach(function (series) { stamps(series).setMarkers(state.markers ? series.__markers__ : []); });
                        markerChip.classList.toggle("off", !state.markers);
                    };
                }
                (data.deals && data.deals.length ? [["Buy", "secondary"], ["Sell", "secondary"]] : []).forEach(function (entry) {
                    var side = entry[0];
                    if (!data.deals.some(function (deal) { return deal.side === side; })) return;
                    var chip = element("span", "lw-chip" + (state.dealmap ? "" : " off"), chips);
                    chip.innerHTML = '<span class="lw-swatch" style="background:' + tint(theme, entry[1], "up") + '"></span><span>' + side + ' Deals</span>';
                    chip.onclick = function () {
                        state.sides[side] = !state.sides[side];
                        dealSeries.forEach(function (series) {
                            if (series.__side__ === side) series.applyOptions({visible: state.sides[side]});
                        });
                        chip.classList.toggle("off", !state.sides[side]);
                    };
                });
            }
        });
        if (charts.length) {
            (data.deals || []).forEach(function (deal) {
                var colour = tint(theme, deal.color, "up");
                var line = charts[0].addSeries(LightweightCharts.LineSeries, {color: colour, lineWidth: 3, priceLineVisible: false, lastValueVisible: false,
                                                    crosshairMarkerVisible: false, visible: state.sides[deal.side] !== false && state.dealmap,
                                                    autoscaleInfoProvider: function () { return null; }});
                line.setData(deal.points);
                line.__side__ = deal.side;
                stamps(line).setMarkers(deal.points.map(function (point) { return {time: point.time, position: "inBar", color: colour, shape: "circle", size: 0.8}; }));
                dealSeries.push(line);
            });
        }
        var syncing = false;
        var stamps_ = (data.timeline || []).map(function (point) { return point.time; });
        var brush = null;
        if (stamps_.length > 1 && charts.length) {
            var span = element("div", "lw-range", body);
            body.insertBefore(span, body.firstChild);
            var opening = element("span", "lw-range-edge", span);
            var track = element("div", "lw-range-track", span);
            var closing = element("span", "lw-range-edge", span);
            var window_ = element("div", "lw-range-window", track);
            element("span", "lw-range-grip lw-range-grip-left", window_);
            element("span", "lw-range-grip lw-range-grip-right", window_);
            var last = stamps_.length - 1;
            var moment = function (index) {
                var stamp = stamps_[Math.max(0, Math.min(last, Math.round(index)))];
                return new Date(stamp * 1000).toISOString().slice(0, 10);
            };
            var current = {from: 0, to: last};
            brush = function (range) {
                if (!range) return;
                current = {from: Math.max(0, range.from), to: Math.min(last, range.to)};
                var width = Math.max(0.6, ((current.to - current.from) / last) * 100);
                window_.style.left = Math.max(0, (current.from / last) * 100) + "%";
                window_.style.width = Math.min(100, width) + "%";
                opening.textContent = moment(current.from);
                closing.textContent = moment(current.to);
            };
            var drag = function (event, mode) {
                event.preventDefault();
                var rect = track.getBoundingClientRect();
                var origin = event.clientX, start = current.from, stop = current.to;
                var move = function (motion) {
                    var shift = ((motion.clientX - origin) / rect.width) * last;
                    var from = start, to = stop;
                    if (mode === "pan") { from = start + shift; to = stop + shift; }
                    else if (mode === "left") from = Math.min(start + shift, stop - 1);
                    else to = Math.max(stop + shift, start + 1);
                    if (from < 0) { to -= from; from = 0; }
                    if (to > last) { from -= to - last; to = last; }
                    syncing = true;
                    charts.forEach(function (instance) {
                        if ((instance.__scale__ || "time") !== "time") return;
                        instance.timeScale().setVisibleLogicalRange({from: Math.max(0, from), to: Math.min(last, to)});
                    });
                    syncing = false;
                    brush({from: from, to: to});
                };
                var release = function () {
                    window.removeEventListener("pointermove", move);
                    window.removeEventListener("pointerup", release);
                };
                window.addEventListener("pointermove", move);
                window.addEventListener("pointerup", release);
            };
            window_.addEventListener("pointerdown", function (event) { if (event.target === window_) drag(event, "pan"); });
            window_.querySelector(".lw-range-grip-left").addEventListener("pointerdown", function (event) { drag(event, "left"); });
            window_.querySelector(".lw-range-grip-right").addEventListener("pointerdown", function (event) { drag(event, "right"); });
        }

        var kin = function (instance) {
            return charts.filter(function (other) { return (other.__scale__ || "time") === (instance.__scale__ || "time"); });
        };

        charts.forEach(function (instance) {
            instance.timeScale().subscribeVisibleLogicalRangeChange(function (range) {
                if (brush && (instance.__scale__ || "time") === "time") brush(range);
                if (syncing || !range) return;
                syncing = true;
                kin(instance).forEach(function (other) { if (other !== instance) other.timeScale().setVisibleLogicalRange(range); });
                syncing = false;
            });
            instance.subscribeCrosshairMove(function (param) {
                var stamp = param.time;
                registry.forEach(function (entry) {
                    var value = stamp === undefined ? undefined : entry.lookup.get(stamp);
                    entry.chip.querySelector("b").textContent = value === undefined || value === null ? "" : format(entry.format, value);
                });
                kin(instance).forEach(function (other) {
                    if (other === instance) return;
                    if (param.point && stamp !== undefined && other.__primary__) {
                        var value = other.__lookup__ ? other.__lookup__.get(stamp) : undefined;
                        other.setCrosshairPosition(value === undefined || value === null ? 0 : value, stamp, other.__primary__);
                    } else other.clearCrosshairPosition();
                });
            });
        });
        state.charts = state.charts.concat(charts);
        state.priced = state.priced.concat(priced);
        state.deals = state.deals.concat(dealSeries);
        Object.assign(state.spans, data.spans || {});
        requestAnimationFrame(function () { charts.forEach(function (instance) { instance.timeScale().fitContent(); }); refreshAxis(); });
        return {
            theme: theme,
            dispose: function () {
                watchers.forEach(function (watcher) { try { watcher.disconnect(); } catch (error) {} });
                charts.forEach(function (instance) { try { instance.remove(); } catch (error) {} });
                state.charts = state.charts.filter(function (entry) { return charts.indexOf(entry) < 0; });
                state.priced = state.priced.filter(function (entry) { return priced.indexOf(entry) < 0; });
                state.deals = state.deals.filter(function (entry) { return dealSeries.indexOf(entry) < 0; });
                state.lines = [];
            }
        };
    };

    var table = function (host, data) {
        var theme = palette(host, data.theme);
        var body = host.querySelector(":scope > .lightweight-body");
        var state = space(host.getAttribute("data-workspace") || "default");
        var outbound = data.outbound;
        var edition = data.edition;
        var navigation = data.navigation || {};
        body.innerHTML = "";
        Object.assign(state.spans, data.spans || {});
        var sheets = data.sheets || [];
        var frame = element("div", "lw-table", body);
        var bar = element("div", "lw-bar", frame);
        var title = element("span", "lw-title", bar);
        title.textContent = data.title || "Report";
        var tabs = element("span", "lw-chips", bar);
        var sheetSaver = element("span", "lw-save", bar);
        element("span", "lw-icon lw-icon-image", sheetSaver);
        element("span", "lw-save-text", sheetSaver).textContent = "PNG";
        sheetSaver.title = "Save this table as a PNG image";
        var sheetExporter = element("span", "lw-save", bar);
        element("span", "lw-icon lw-icon-csv", sheetExporter);
        element("span", "lw-save-text", sheetExporter).textContent = "CSV";
        sheetExporter.title = "Export this table as CSV";
        var count = element("span", "lw-count", bar);
        var scroller = element("div", "lw-grid", frame);
        if (!sheets.length) {
            element("div", "lw-empty", scroller).textContent = "No rows";
            publish(outbound, {selected: [], indices: [], total: 0, shown: 0, sheet: null});
            return {theme: theme, dispose: noop};
        }
        var current = sheets[0], order = null, ascending = true, view = [], chosen = {}, anchor = null;
        var grid = element("table", null, scroller);
        var head = element("thead", null, grid);
        var trunk = element("tbody", null, grid);
        var lead = element("tr", "lw-spacer", trunk);
        var leadCell = element("td", null, lead);
        var tail = element("tr", "lw-spacer", trunk);
        var tailCell = element("td", null, tail);
        var height = 26, window_ = 60, ticking = false;

        var selected = function () {
            var keys = [];
            for (var index in chosen) if (chosen[index]) {
                var links = (current.keys || [])[index] || [];
                for (var entry = 0; entry < links.length; entry++) if (keys.indexOf(links[entry]) < 0) keys.push(links[entry]);
            }
            return keys;
        };

        var picked = function () {
            var names = current.columns.map(function (definition) { return definition.name; });
            var records = [];
            for (var index in chosen) if (chosen[index]) {
                var cells = current.rows[index] || [], record = {};
                for (var column = 0; column < names.length; column++) record[names[column]] = cells[column];
                records.push(record);
            }
            return records;
        };

        var report = function () {
            var indices = Object.keys(chosen).filter(function (index) { return chosen[index]; }).map(Number);
            publish(outbound, {selected: selected(), indices: indices, rows: picked(), total: current.height || current.rows.length,
                               shown: view.length, sheet: current.name, base: navigation.base || null, key: navigation.key || null});
        };

        var sync = function () {
            var keys = selected();
            if (state.charts.length) highlight(state, keys, theme);
            report();
        };

        var identity = function (index) {
            var carried = (current.keys || [])[index];
            if (carried && carried.length) return carried[0];
            var names = current.columns.map(function (definition) { return definition.name; });
            var column = names.indexOf(navigation.key || "UID");
            return column < 0 ? null : (current.rows[index] || [])[column];
        };

        var edit = function (cell, record, column) {
            if (cell.firstChild && cell.firstChild.tagName === "INPUT") return;
            var definition = current.columns[column];
            var original = record.cells[column] == null ? "" : String(record.cells[column]);
            var settled = false;
            cell.textContent = "";
            var input = element("input", "lw-input", cell);
            input.value = original;
            var settle = function (commit) {
                if (settled) return;
                settled = true;
                var value = input.value;
                var changed = commit && value !== original;
                cell.textContent = changed ? value : original;
                if (!changed) return;
                record.cells[column] = value;
                current.rows[record.index][column] = value;
                publish(edition, {uid: identity(record.index), column: definition.name, value: value,
                                  sheet: current.name, stamp: performance.now()});
            };
            input.onblur = function () { settle(true); };
            input.onkeydown = function (event) {
                event.stopPropagation();
                if (event.key === "Enter") { event.preventDefault(); settle(true); }
                else if (event.key === "Escape") { event.preventDefault(); settle(false); }
            };
            input.onclick = function (event) { event.stopPropagation(); };
            input.ondblclick = function (event) { event.stopPropagation(); };
            input.focus();
            input.select();
        };

        var editor = function (cell, record, column) {
            return function (event) { event.stopPropagation(); edit(cell, record, column); };
        };

        var paint = function () {
            var total = view.length;
            var top = Math.max(0, Math.floor(scroller.scrollTop / height) - 10);
            var last = Math.min(total, top + window_ + 20);
            while (trunk.children.length > 2) trunk.removeChild(trunk.children[1]);
            leadCell.style.height = (top * height) + "px";
            leadCell.colSpan = current.columns.length;
            tailCell.style.height = Math.max(0, (total - last) * height) + "px";
            tailCell.colSpan = current.columns.length;
            var fragment = document.createDocumentFragment();
            for (var index = top; index < last; index++) {
                var record = view[index];
                var row = document.createElement("tr");
                row.setAttribute("data-index", record.index);
                if (chosen[record.index]) row.className = "on";
                if (((current.keys || [])[record.index] || []).length) row.classList.add("link");
                for (var column = 0; column < current.columns.length; column++) {
                    var cell = document.createElement("td");
                    var definition = current.columns[column];
                    if (definition.align) cell.style.textAlign = definition.align;
                    if (definition.markdown) cell.innerHTML = record.cells[column];
                    else cell.textContent = record.cells[column];
                    if (!definition.markdown && cell.textContent) cell.title = cell.textContent;
                    if (definition.editable && edition) {
                        cell.classList.add("lw-writable");
                        cell.ondblclick = editor(cell, record, column);
                    }
                    row.appendChild(cell);
                }
                fragment.appendChild(row);
            }
            trunk.insertBefore(fragment, tail);
            tally();
        };

        var tally = function () {
            count.textContent = (current.height || 0) + " total · " + view.length + " shown · "
                + Object.keys(chosen).filter(function (index) { return chosen[index]; }).length + " selected";
        };

        var mark = function () {
            var rows = trunk.querySelectorAll("tr[data-index]");
            for (var index = 0; index < rows.length; index++) {
                rows[index].classList.toggle("on", !!chosen[Number(rows[index].getAttribute("data-index"))]);
            }
            tally();
        };

        var arrange = function () {
            view = current.rows.map(function (cells, index) { return {index: index, cells: cells}; });
            if (order !== null) {
                var numeric = view.every(function (record) {
                    var value = (record.cells[order] || "").replace(/[,\s]/g, "");
                    return value === "" || !isNaN(Number(value));
                });
                view.sort(function (left, right) {
                    var a = left.cells[order] || "", b = right.cells[order] || "";
                    if (numeric) { a = Number(a.replace(/[,\s]/g, "")) || 0; b = Number(b.replace(/[,\s]/g, "")) || 0; }
                    if (a === b) return 0;
                    return (a < b ? -1 : 1) * (ascending ? 1 : -1);
                });
            }
            paint();
        };

        var columns = function () {
            head.innerHTML = "";
            var row = element("tr", null, head);
            current.columns.forEach(function (definition, index) {
                var cell = element("th", null, row);
                cell.textContent = definition.label || definition.name;
                if (definition.width) cell.style.width = definition.width;
                if (definition.align) cell.style.textAlign = definition.align;
                if (order === index) cell.classList.add(ascending ? "asc" : "desc");
                cell.onclick = function () {
                    if (order === index) ascending = !ascending;
                    else { order = index; ascending = true; }
                    columns();
                    arrange();
                };
            });
        };

        var stem = function () {
            return ((document.querySelector(".page-title") || {}).textContent || data.title || "table").trim().replace(/[^\w.-]+/g, "-").slice(0, 60);
        };
        sheetSaver.onclick = function () {
            window.Quant.save(window.Quant.blob(window.Quant.sheetCanvas(current)), stem() + "." + String(current.name || "sheet").toLowerCase() + ".png");
        };
        sheetExporter.onclick = function () {
            window.Quant.save(new Blob(["﻿" + window.Quant.csv(current)], {type: "text/csv;charset=utf-8;"}),
                              stem() + "." + String(current.name || "sheet").toLowerCase() + ".csv");
        };

        var draw = function (sheet) {
            current = Object.assign({}, sheet, {columns: (sheet.columns || []).map(function (entry) {
                return typeof entry === "string" ? {name: entry, label: entry} : entry;
            })});
            order = null;
            ascending = true;
            chosen = {};
            anchor = null;
            scroller.scrollTop = 0;
            columns();
            arrange();
            if (state.charts.length) clear(state);
            report();
        };

        var cap = function () {
            scroller.style.height = "";
            paint();
            var content = scroller.scrollHeight + 2;
            var ceiling = parseFloat(getComputedStyle(host).maxHeight);
            var reserve = frame.getBoundingClientRect().height - scroller.getBoundingClientRect().height;
            var limit = isNaN(ceiling) ? content : Math.max(120, ceiling - reserve);
            scroller.style.height = Math.min(content, limit) + "px";
            paint();
        };

        var fit = function () {
            if (!host.classList.contains("lightweight-fill")) return cap();
            var page = host.closest(".page") || document.body;
            var bar = page.querySelector(".table-bar");
            var footer = document.querySelector(".app-footer");
            var reserve = (bar ? bar.getBoundingClientRect().height : 0) + (footer ? footer.getBoundingClientRect().height : 0) + 32;
            var available = window.innerHeight - scroller.getBoundingClientRect().top - reserve;
            scroller.style.height = Math.max(180, Math.floor(available)) + "px";
            paint();
        };
        var resize = function () { clearTimeout(resize.timer); resize.timer = setTimeout(fit, 150); };
        window.addEventListener("resize", resize);

        scroller.addEventListener("scroll", function () {
            if (ticking) return;
            ticking = true;
            requestAnimationFrame(function () { ticking = false; paint(); });
        });

        trunk.addEventListener("click", function (event) {
            var row = event.target.closest("tr[data-index]");
            if (!row) return;
            var index = Number(row.getAttribute("data-index"));
            if (event.shiftKey && anchor !== null) {
                var positions = view.map(function (record) { return record.index; });
                var from = positions.indexOf(anchor), to = positions.indexOf(index);
                if (from > to) { var swap = from; from = to; to = swap; }
                for (var step = from; step <= to; step++) chosen[positions[step]] = true;
            } else if (event.ctrlKey || event.metaKey) {
                chosen[index] = !chosen[index];
                anchor = index;
            } else {
                var only = chosen[index] && Object.keys(chosen).filter(function (key) { return chosen[key]; }).length === 1;
                chosen = {};
                if (!only) chosen[index] = true;
                anchor = only ? null : index;
            }
            mark();
            sync();
        });

        trunk.addEventListener("dblclick", function (event) {
            var row = event.target.closest("tr[data-index]");
            if (!row || !navigation.base) return;
            var uid = identity(Number(row.getAttribute("data-index")));
            if (uid) window.location.assign(String(navigation.base).replace(/\/+$/, "") + "/" + encodeURIComponent(uid));
        });

        sheets.forEach(function (sheet, index) {
            var tab = element("span", "lw-chip" + (index ? " off" : ""), tabs);
            tab.textContent = sheet.name;
            tab.onclick = function () {
                for (var entry = 0; entry < tabs.children.length; entry++) tabs.children[entry].classList.add("off");
                tab.classList.remove("off");
                draw(sheet);
            };
        });
        if (sheets.length < 2) tabs.style.display = "none";
        draw(sheets[0]);
        requestAnimationFrame(fit);
        state.tables.push(frame);
        return {
            theme: theme,
            dispose: function () {
                window.removeEventListener("resize", resize);
                state.tables = state.tables.filter(function (entry) { return entry !== frame; });
            }
        };
    };

    var stretch = function (host) {
        if (!host || host.dataset.fill !== "1") return function () {};
        var apply = function () {
            var top = host.getBoundingClientRect().top;
            var footer = document.querySelector(".app-footer");
            var reserved = footer ? footer.offsetHeight : 0;
            var content = host.closest(".content");
            var padding = content ? parseFloat(getComputedStyle(content).paddingBottom) || 0 : 0;
            host.style.height = Math.max(240, Math.floor(window.innerHeight - top - reserved - padding)) + "px";
        };
        apply();
        var pending = null;
        var schedule = function () { if (pending) cancelAnimationFrame(pending); pending = requestAnimationFrame(apply); };
        window.addEventListener("resize", schedule);
        window.addEventListener("orientationchange", schedule);
        return function () {
            window.removeEventListener("resize", schedule);
            window.removeEventListener("orientationchange", schedule);
        };
    };

    var payload = function (host) {
        var node = host.querySelector(":scope > script.lightweight-payload") || document.getElementById("lightweight-payload");
        if (!node) return null;
        var raw = node.textContent || "{}";
        try { return {data: JSON.parse(raw), raw: raw}; } catch (error) { return null; }
    };

    var unmount = function (host) {
        var instance = hosts.get(host);
        if (!instance) return;
        try { if (instance.release) instance.release(); } catch (error) {}
        try { instance.dispose(); } catch (error) {}
        hosts.delete(host);
    };

    var mount = function (host) {
        if (!window.LightweightCharts) {
            if (pending.get(host)) return;
            pending.set(host, true);
            setTimeout(function () { pending.delete(host); if (host.isConnected) mount(host); }, 60);
            return;
        }
        var carrier = payload(host);
        if (!carrier) return;
        var existing = hosts.get(host);
        if (existing && existing.raw === carrier.raw) return;
        unmount(host);
        if (!host.querySelector(":scope > .lightweight-body")) element("div", "lightweight-body", host);
        var role = host.getAttribute("data-role") || "chart";
        var instance;
        try { instance = role === "table" ? table(host, carrier.data) : chart(host, carrier.data); }
        catch (error) { console.error("Lightweight Operation: Failed", error); return; }
        instance.raw = carrier.raw;
        instance.role = role;
        instance.release = stretch(host);
        hosts.set(host, instance);
    };

    var scan = function (root) {
        if (!root || root.nodeType !== 1) return;
        if (root.hasAttribute && root.hasAttribute("data-role") && root.hasAttribute("data-workspace")) mount(root);
        var nodes = root.querySelectorAll ? root.querySelectorAll("[data-role][data-workspace]") : [];
        for (var index = 0; index < nodes.length; index++) mount(nodes[index]);
    };

    var sweep = function (root) {
        if (!root || root.nodeType !== 1) return;
        if (root.hasAttribute && root.hasAttribute("data-role") && root.hasAttribute("data-workspace")) unmount(root);
        var nodes = root.querySelectorAll ? root.querySelectorAll("[data-role][data-workspace]") : [];
        for (var index = 0; index < nodes.length; index++) unmount(nodes[index]);
    };

    var refresh = function () {
        var nodes = document.querySelectorAll("[data-role][data-workspace]");
        for (var index = 0; index < nodes.length; index++) {
            var host = nodes[index];
            unmount(host);
            mount(host);
        }
    };

    var schedule = (function () {
        var timer = null;
        return function () {
            clearTimeout(timer);
            timer = setTimeout(function () { scan(document.body); }, 30);
        };
    })();

    var carried = function (node) {
        while (node) {
            if (node.classList && node.classList.contains("lightweight-payload")) return true;
            node = node.parentNode;
        }
        return false;
    };

    new MutationObserver(function (mutations) {
        for (var index = 0; index < mutations.length; index++) {
            var mutation = mutations[index];
            for (var removed = 0; removed < mutation.removedNodes.length; removed++) sweep(mutation.removedNodes[removed]);
            if (carried(mutation.target)) { schedule(); continue; }
            for (var added = 0; added < mutation.addedNodes.length; added++) {
                if (mutation.addedNodes[added].nodeType === 1) { schedule(); break; }
            }
        }
    }).observe(document.body, {childList: true, subtree: true, characterData: true});

    new MutationObserver(function () { refresh(); }).observe(document.documentElement, {attributes: true, attributeFilter: ["data-bs-theme"]});

    window.Quant = window.Quant || {};
    window.Quant.lightweight = {mount: mount, unmount: unmount, refresh: refresh, scan: scan, spaces: spaces};

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { scan(document.body); });
    else scan(document.body);
})();