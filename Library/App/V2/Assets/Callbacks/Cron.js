(function(schedule) {
    var base = "https://crontab.guru/";
    if (!schedule || !schedule.trim()) return base;
    return base + "#" + schedule.trim().replace(/\s+/g, "_");
})