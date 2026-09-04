(function(clicks) {
    var nu = window.dash_clientside.no_update;
    if (!clicks) return nu;
    var carrier = document.querySelector("script.lightweight-payload");
    if (!carrier) return nu;
    var payload;
    try { payload = JSON.parse(carrier.textContent || "{}"); } catch (error) { return nu; }
    var sheets = payload.sheets || [];
    if (!sheets.length) return nu;
    var title = ((document.querySelector(".page-title") || {}).textContent || payload.title || "result").trim().replace(/[^\w.-]+/g, "-").slice(0, 60);
    var files = sheets.map(function(sheet) {
        return {name: String(sheet.name || "sheet").toLowerCase() + ".csv", body: window.Quant.csv(sheet)};
    });
    if (files.length === 1) window.Quant.save(new Blob(["\ufeff" + files[0].body], {type: "text/csv;charset=utf-8;"}), title + "." + files[0].name);
    else window.Quant.save(window.Quant.archive(files), title + ".tables.zip");
    return nu;
})