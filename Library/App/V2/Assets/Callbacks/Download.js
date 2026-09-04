(function(clicks) {
    var nu = window.dash_clientside.no_update;
    if (!clicks) return nu;
    var title = ((document.querySelector(".page-title") || {}).textContent || "result").trim().replace(/[^\w.-]+/g, "-").slice(0, 60);
    var images = window.Quant.capture();
    if (!images.length) return nu;
    if (images.length === 1) window.Quant.save(window.Quant.blob(images[0].canvas), title + "." + images[0].name + ".png");
    else window.Quant.save(window.Quant.archive(images.map(function(image) {
        return {name: image.name + ".png", bytes: window.Quant.decode(image.canvas.toDataURL("image/png"))};
    })), title + ".charts.zip");
    return nu;
})