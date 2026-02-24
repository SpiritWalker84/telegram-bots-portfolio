(function () {
    const loading = document.getElementById("loading");
    const errorEl = document.getElementById("error");
    const weatherEl = document.getElementById("weather");
    const cityNameEl = document.getElementById("city-name");
    const currentTemp = document.getElementById("current-temp");
    const currentDesc = document.getElementById("current-desc");
    const currentFeels = document.getElementById("current-feels");
    const currentWind = document.getElementById("current-wind");
    const tomorrowBlock = document.getElementById("tomorrow-block");
    const tomorrowTemps = document.getElementById("tomorrow-temps");
    const tomorrowDesc = document.getElementById("tomorrow-desc");
    const forecastList = document.getElementById("forecast-list");
    const searchForm = document.getElementById("search-form");
    const cityInput = document.getElementById("city-input");
    const bgLayer = document.getElementById("bg-layer");

    function getQuery() {
        const params = new URLSearchParams(window.location.search);
        return {
            city: params.get("city") || "",
            lat: params.get("lat") || "",
            lon: params.get("lon") || "",
        };
    }

    function buildApiUrl() {
        const q = getQuery();
        const base = "/api/weather";
        if (q.city) return base + "?city=" + encodeURIComponent(q.city);
        if (q.lat && q.lon) return base + "?lat=" + q.lat + "&lon=" + q.lon;
        return base + "?city=Москва";
    }

    function setWeatherTheme(code) {
        document.body.classList.remove(
            "weather-clear", "weather-clouds", "weather-rain", "weather-drizzle",
            "weather-snow", "weather-fog", "weather-mist", "weather-thunderstorm"
        );
        if (code >= 200 && code < 300) document.body.classList.add("weather-thunderstorm");
        else if (code >= 300 && code < 400) document.body.classList.add("weather-drizzle");
        else if (code >= 500 && code < 600) document.body.classList.add("weather-rain");
        else if (code >= 600 && code < 700) document.body.classList.add("weather-snow");
        else if (code >= 700 && code < 800) document.body.classList.add("weather-fog");
        else if (code === 800) document.body.classList.add("weather-clear");
        else if (code > 800) document.body.classList.add("weather-clouds");
        else document.body.classList.add("weather-clear");
    }

    function clearAnimations() {
        bgLayer.querySelectorAll(".snowflake, .raindrop, .cloud, .lightning, .branch, .leaf, .fog-particle, .sunray, .rainbow").forEach(function (el) {
            el.remove();
        });
    }

    function addLightning() {
        var count = 3;
        for (var i = 0; i < count; i++) {
            var bolt = document.createElement("div");
            bolt.className = "lightning";
            bolt.style.left = (15 + i * 30) + "%";
            bolt.style.animationDelay = (i * 2) + "s";
            bolt.style.animationDuration = (3 + Math.random() * 2) + "s";
            bgLayer.appendChild(bolt);
        }
    }

    function addBranches() {
        var positions = [
            { left: "10%", delay: 0 },
            { left: "30%", delay: 1 },
            { left: "60%", delay: 0.5 },
            { left: "85%", delay: 1.5 }
        ];
        positions.forEach(function (p) {
            var branch = document.createElement("div");
            branch.className = "branch";
            branch.style.left = p.left;
            branch.style.animationDelay = p.delay + "s";
            bgLayer.appendChild(branch);
        });
    }

    function addLeaves() {
        var count = 25;
        var frag = document.createDocumentFragment();
        for (var i = 0; i < count; i++) {
            var leaf = document.createElement("div");
            leaf.className = "leaf";
            leaf.style.left = Math.random() * 100 + "%";
            leaf.style.animationDuration = (4 + Math.random() * 4) + "s";
            leaf.style.animationDelay = Math.random() * 2 + "s";
            leaf.style.fontSize = (0.8 + Math.random() * 0.6) + "rem";
            frag.appendChild(leaf);
        }
        bgLayer.appendChild(frag);
    }

    function addFog() {
        var count = 8;
        for (var i = 0; i < count; i++) {
            var fog = document.createElement("div");
            fog.className = "fog-particle";
            fog.style.left = Math.random() * 100 + "%";
            fog.style.bottom = (10 + Math.random() * 20) + "%";
            fog.style.animationDuration = (20 + Math.random() * 15) + "s";
            fog.style.animationDelay = Math.random() * 5 + "s";
            fog.style.opacity = 0.3 + Math.random() * 0.3;
            bgLayer.appendChild(fog);
        }
    }

    function addSunrays() {
        var count = 5;
        for (var i = 0; i < count; i++) {
            var ray = document.createElement("div");
            ray.className = "sunray";
            ray.style.left = (20 + i * 15) + "%";
            ray.style.animationDelay = (i * 0.3) + "s";
            bgLayer.appendChild(ray);
        }
    }

    function addRainbow() {
        var rainbow = document.createElement("div");
        rainbow.className = "rainbow";
        bgLayer.appendChild(rainbow);
    }

    function addSnow() {
        var count = 80;
        var frag = document.createDocumentFragment();
        for (var i = 0; i < count; i++) {
            var flake = document.createElement("div");
            flake.className = "snowflake";
            flake.textContent = "❄";
            flake.style.left = Math.random() * 100 + "%";
            flake.style.animationDuration = (8 + Math.random() * 8) + "s";
            flake.style.animationDelay = Math.random() * 5 + "s";
            flake.style.fontSize = (0.6 + Math.random() * 0.8) + "rem";
            frag.appendChild(flake);
        }
        bgLayer.appendChild(frag);
    }

    function addRain() {
        var count = 90;
        var frag = document.createDocumentFragment();
        for (var i = 0; i < count; i++) {
            var drop = document.createElement("div");
            drop.className = "raindrop";
            drop.style.left = Math.random() * 100 + "%";
            drop.style.animationDuration = (0.3 + Math.random() * 0.4) + "s";
            drop.style.animationDelay = Math.random() * 0.5 + "s";
            frag.appendChild(drop);
        }
        bgLayer.appendChild(frag);
    }

    function addClouds() {
        var positions = [
            { top: "8%", w: 90, h: 45, d: 25 },
            { top: "20%", w: 110, h: 55, d: 35 },
            { top: "35%", w: 70, h: 35, d: 20 },
            { top: "50%", w: 85, h: 40, d: 28 },
        ];
        positions.forEach(function (p, i) {
            var cloud = document.createElement("div");
            cloud.className = "cloud";
            cloud.style.top = p.top;
            cloud.style.left = (i * 25 - 10) + "%";
            cloud.style.width = p.w + "px";
            cloud.style.height = p.h + "px";
            cloud.style.animationDuration = (40 + i * 10) + "s";
            cloud.style.animationDelay = i * 3 + "s";
            cloud.style.borderRadius = "50%";
            cloud.style.boxShadow = "0 0 30px rgba(255,255,255,0.2)";
            bgLayer.appendChild(cloud);
        });
    }

    function runAnimation(code) {
        clearAnimations();
        setWeatherTheme(code);
        if (code >= 600 && code < 700) {
            addSnow();
            addBranches();
        } else if (code >= 500 && code < 600) {
            addRain();
            addBranches();
            addLeaves();
        } else if (code >= 300 && code < 400) {
            addRain();
            addBranches();
        } else if (code >= 200 && code < 300) {
            addRain();
            addLightning();
            addBranches();
        } else if (code >= 700 && code < 800) {
            addClouds();
            addFog();
            addBranches();
        } else if (code >= 801) {
            addClouds();
            addBranches();
            addLeaves();
        } else if (code === 800) {
            addSunrays();
            addBranches();
            addLeaves();
            if (Math.random() > 0.7) addRainbow();
        }
    }

    function formatDate(ymd) {
        if (!ymd) return "";
        var parts = ymd.split("-");
        if (parts.length !== 3) return ymd;
        return parts[2] + "." + parts[1];
    }

    function showLoading() {
        loading.hidden = false;
        errorEl.hidden = true;
        weatherEl.hidden = true;
    }

    function showError(msg) {
        loading.hidden = true;
        weatherEl.hidden = true;
        errorEl.hidden = false;
        errorEl.textContent = msg;
    }

    function showWeather(data) {
        loading.hidden = true;
        errorEl.hidden = true;
        weatherEl.hidden = false;

        var code = data.weatherCode != null ? data.weatherCode : 800;
        runAnimation(code);

        cityNameEl.textContent = data.city || "—";

        var cur = data.current || {};
        currentTemp.textContent = (cur.temp != null ? Math.round(cur.temp) + "°C" : "—");
        currentDesc.textContent = cur.description || "—";
        currentFeels.textContent = "Ощущается: " + (cur.feels_like != null ? Math.round(cur.feels_like) + "°C" : "—");
        currentWind.textContent = "Ветер: " + (cur.wind_speed != null ? cur.wind_speed + " м/с" : "—");

        var tom = data.tomorrow;
        if (tom && (tom.temp_min != null || tom.temp_max != null)) {
            tomorrowBlock.hidden = false;
            tomorrowTemps.textContent = Math.round(tom.temp_min) + " / " + Math.round(tom.temp_max) + "°C";
            tomorrowDesc.textContent = tom.description || "—";
        } else {
            tomorrowBlock.hidden = true;
        }

        var list = data.forecast || [];
        forecastList.innerHTML = "";
        list.forEach(function (day) {
            var item = document.createElement("div");
            item.className = "forecast-item";
            item.innerHTML =
                "<span class=\"forecast-date\">" + formatDate(day.date) + "</span>" +
                "<span class=\"forecast-temps\">" + (day.temp_min != null && day.temp_max != null ? Math.round(day.temp_min) + " / " + Math.round(day.temp_max) + "°C" : "—") + "</span>" +
                "<span class=\"forecast-desc\">" + (day.description || "—") + "</span>";
            forecastList.appendChild(item);
        });

        var q = getQuery();
        if (q.city) cityInput.value = q.city;
    }

    function load() {
        showLoading();
        fetch(buildApiUrl())
            .then(function (r) {
                return r.text().then(function (text) {
                    if (!r.ok) {
                        if (text && text.trim().indexOf("<") === 0) {
                            throw new Error("Сервер погоды недоступен. Проверьте контейнер api (docker compose ps).");
                        }
                        throw new Error("Ошибка загрузки: " + r.status);
                    }
                    var data;
                    try {
                        data = JSON.parse(text);
                    } catch (e) {
                        if (text && text.trim().indexOf("<") === 0) {
                            throw new Error("Сервер погоды вернул страницу вместо данных. Запустите: docker compose up -d");
                        }
                        throw new Error("Неверный ответ сервера.");
                    }
                    return data;
                });
            })
            .then(function (data) {
                if (data.error) throw new Error(data.error);
                showWeather(data);
            })
            .catch(function (err) {
                showError(err.message || "Не удалось загрузить погоду.");
            });
    }

    searchForm.addEventListener("submit", function (e) {
        e.preventDefault();
        var city = (cityInput.value || "").trim();
        if (!city) return;
        var url = new URL(window.location.href);
        url.searchParams.set("city", city);
        url.searchParams.delete("lat");
        url.searchParams.delete("lon");
        window.location.href = url.toString();
    });

    load();
})();
