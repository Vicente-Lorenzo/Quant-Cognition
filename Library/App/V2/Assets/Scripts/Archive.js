(function () {
    var table = (function () {
        var lookup = new Uint32Array(256);
        for (var index = 0; index < 256; index++) {
            var value = index;
            for (var bit = 0; bit < 8; bit++) value = value & 1 ? 0xEDB88320 ^ (value >>> 1) : value >>> 1;
            lookup[index] = value >>> 0;
        }
        return lookup;
    })();

    var crc32 = function (bytes) {
        var crc = 0xFFFFFFFF;
        for (var index = 0; index < bytes.length; index++) crc = table[(crc ^ bytes[index]) & 0xFF] ^ (crc >>> 8);
        return (crc ^ 0xFFFFFFFF) >>> 0;
    };

    var stamp = function (moment) {
        var time = ((moment.getHours() << 11) | (moment.getMinutes() << 5) | (moment.getSeconds() / 2)) >>> 0;
        var date = (((moment.getFullYear() - 1980) << 9) | ((moment.getMonth() + 1) << 5) | moment.getDate()) >>> 0;
        return {time: time & 0xFFFF, date: date & 0xFFFF};
    };

    var writer = function (size) {
        var buffer = new Uint8Array(size), cursor = 0;
        return {
            byte: function (value) { buffer[cursor++] = value & 0xFF; },
            short: function (value) { buffer[cursor++] = value & 0xFF; buffer[cursor++] = (value >>> 8) & 0xFF; },
            long: function (value) { for (var shift = 0; shift < 4; shift++) buffer[cursor++] = (value >>> (shift * 8)) & 0xFF; },
            bytes: function (source) { buffer.set(source, cursor); cursor += source.length; },
            at: function () { return cursor; },
            done: function () { return buffer.subarray(0, cursor); }
        };
    };

    window.Quant = window.Quant || {};

    window.Quant.archive = function (files) {
        var encoder = new TextEncoder();
        var entries = files.map(function (file) {
            var name = encoder.encode(file.name);
            var body = file.bytes instanceof Uint8Array ? file.bytes : encoder.encode(String(file.body || ""));
            return {name: name, body: body, crc: crc32(body)};
        });
        var total = entries.reduce(function (sum, entry) { return sum + 30 + entry.name.length + entry.body.length + 46 + entry.name.length; }, 22);
        var out = writer(total);
        var moment = stamp(new Date());
        var offsets = [];
        entries.forEach(function (entry) {
            offsets.push(out.at());
            out.long(0x04034B50); out.short(20); out.short(0); out.short(0);
            out.short(moment.time); out.short(moment.date);
            out.long(entry.crc); out.long(entry.body.length); out.long(entry.body.length);
            out.short(entry.name.length); out.short(0);
            out.bytes(entry.name); out.bytes(entry.body);
        });
        var directory = out.at();
        entries.forEach(function (entry, index) {
            out.long(0x02014B50); out.short(20); out.short(20); out.short(0); out.short(0);
            out.short(moment.time); out.short(moment.date);
            out.long(entry.crc); out.long(entry.body.length); out.long(entry.body.length);
            out.short(entry.name.length); out.short(0); out.short(0); out.short(0); out.short(0);
            out.long(0); out.long(offsets[index]);
            out.bytes(entry.name);
        });
        var span = out.at() - directory;
        out.long(0x06054B50); out.short(0); out.short(0);
        out.short(entries.length); out.short(entries.length);
        out.long(span); out.long(directory); out.short(0);
        return new Blob([out.done()], {type: "application/zip"});
    };

    window.Quant.save = function (blob, name) {
        var url = URL.createObjectURL(blob);
        var link = document.createElement("a");
        link.href = url;
        link.download = name;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    };


    window.Quant.csv = function (sheet) {
        var quote = function (value) {
            var text = value === null || value === undefined ? "" : String(value);
            var risky = text.indexOf('"') >= 0 || text.indexOf(",") >= 0 || text.indexOf(String.fromCharCode(10)) >= 0 || text.indexOf(String.fromCharCode(13)) >= 0;
            return risky ? '"' + text.replace(/"/g, '""') + '"' : text;
        };
        var names = (sheet.columns || []).map(function (column) { return column.name; });
        var lines = [names.map(quote).join(",")];
        (sheet.rows || []).forEach(function (row) { lines.push(row.map(quote).join(",")); });
        return lines.join(String.fromCharCode(13) + String.fromCharCode(10));
    };

    window.Quant.blob = function (canvas) {
        return new Blob([window.Quant.decode(canvas.toDataURL("image/png"))], {type: "image/png"});
    };

    window.Quant.sheetCanvas = function (sheet, limit) {
        var body = getComputedStyle(document.body);
        var pad = 10, line = 22, font = "13px " + (body.fontFamily || "sans-serif");
        var names = (sheet.columns || []).map(function (column) { return column.name; });
        var rows = (sheet.rows || []).slice(0, limit || 2000);
        var grille = [names].concat(rows);
        var measure = document.createElement("canvas").getContext("2d");
        measure.font = font;
        var widths = names.map(function (_, column) {
            var widest = 0;
            grille.forEach(function (row) { widest = Math.max(widest, measure.measureText(String(row[column] === undefined ? "" : row[column])).width); });
            return Math.ceil(widest) + pad * 2;
        });
        var canvas = document.createElement("canvas");
        canvas.width = Math.max(1, widths.reduce(function (a, b) { return a + b; }, 0));
        canvas.height = grille.length * line + pad * 2;
        var paint = canvas.getContext("2d");
        paint.font = font;
        paint.textBaseline = "middle";
        paint.fillStyle = body.backgroundColor || "#ffffff";
        paint.fillRect(0, 0, canvas.width, canvas.height);
        grille.forEach(function (row, index) {
            var y = pad + index * line + line / 2, x = 0;
            if (index === 0) { paint.fillStyle = "rgba(128,128,128,0.16)"; paint.fillRect(0, pad, canvas.width, line); }
            paint.fillStyle = body.color || "#000000";
            for (var column = 0; column < names.length; column++) {
                paint.fillText(String(row[column] === undefined ? "" : row[column]), x + pad, y);
                x += widths[column];
            }
        });
        return canvas;
    };

    window.Quant.payload = function () {
        var carrier = document.querySelector("script.lightweight-payload");
        if (!carrier) return null;
        try { return JSON.parse(carrier.textContent || "{}"); } catch (error) { return null; }
    };

    window.Quant.capture = function () {
        var data = window.Quant.payload() || {};
        var runtime = window.Quant.lightweight;
        var images = [];
        var spaces = runtime && runtime.spaces ? runtime.spaces : {};
        for (var key in spaces) {
            var charts = spaces[key].charts || [];
            charts.forEach(function (chart, index) {
                if (!chart.takeScreenshot) return;
                var pane = (data.panes || [])[index] || {};
                images.push({name: String(pane.id || "pane-" + (index + 1)), canvas: chart.takeScreenshot()});
            });
        }
        if (!images.length && document.querySelector(".lw-grid")) {
            (data.sheets || []).forEach(function (sheet) {
                images.push({name: String(sheet.name || "sheet").toLowerCase(), canvas: window.Quant.sheetCanvas(sheet)});
            });
        }
        return images;
    };

    window.Quant.decode = function (dataurl) {
        var comma = dataurl.indexOf(",");
        var binary = atob(dataurl.slice(comma + 1));
        var bytes = new Uint8Array(binary.length);
        for (var index = 0; index < binary.length; index++) bytes[index] = binary.charCodeAt(index);
        return bytes;
    };
})();