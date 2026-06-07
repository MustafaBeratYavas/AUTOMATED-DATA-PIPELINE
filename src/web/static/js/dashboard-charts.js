(function () {
    "use strict";

    const currencyFormatter = new Intl.NumberFormat("tr-TR", {
        style: "currency",
        currency: "TRY",
        currencyDisplay: "code",
        maximumFractionDigits: 0,
    });

    const numberFormatter = new Intl.NumberFormat("tr-TR");

    function formatCurrency(value) {
        return currencyFormatter.format(value || 0);
    }

    function formatNumber(value) {
        return numberFormatter.format(value || 0);
    }

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function isDark() {
        return document.documentElement.getAttribute("data-theme") === "dark";
    }

    function themeColors() {
        var dark = isDark();
        return {
            textColor:      dark ? "#cbd5e1" : "#334155",
            textMuted:      dark ? "#64748b" : "#94a3b8",
            axisLine:       dark ? "#334155" : "#e2e8f0",
            splitLine:      dark ? "#1e293b" : "#f1f5f9",
            tooltipBg:      dark ? "#1e293b" : "#ffffff",
            tooltipBorder:  dark ? "#334155" : "#e2e8f0",
            cardBg:         dark ? "#151d2e" : "#ffffff",
        };
    }

    function baseTooltip(tc) {
        return {
            backgroundColor: tc.tooltipBg,
            borderColor: tc.tooltipBorder,
            borderWidth: 1,
            textStyle: {
                color: tc.textColor,
                fontSize: 12,
                fontFamily: "Inter, system-ui, sans-serif",
            },
            padding: [10, 14],
            extraCssText: "border-radius:10px;box-shadow:0 8px 32px rgba(0,0,0,0.18);",
        };
    }

    var chartInstances = {};

    function getOrCreateChart(container, key) {
        if (chartInstances[key]) {
            chartInstances[key].dispose();
        }
        var instance = echarts.init(container, null, { renderer: "canvas" });
        chartInstances[key] = instance;
        return instance;
    }

    function resizeAll() {
        Object.values(chartInstances).forEach(function (chart) {
            if (chart && !chart.isDisposed()) {
                chart.resize();
            }
        });
    }

    function showEmpty(container, message) {
        container.innerHTML = "";
        var node = document.createElement("div");
        node.className = "empty-state";
        node.innerHTML =
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3h18v18H3z"/><path d="M3 9h18M9 21V9"/></svg>' +
            "<span>" + message + "</span>";
        container.appendChild(node);
    }

    function renderMarketplaceChart(container, data) {
        if (!data || !data.length) {
            showEmpty(container, "No priced marketplace rows are available for this selection.");
            return;
        }

        var rows = data.slice(0, 15).reverse();
        var tc = themeColors();
        var chart = getOrCreateChart(container, "marketplace");

        container.style.minHeight = Math.max(460, rows.length * 42 + 100) + "px";
        chart.resize();

        var marketplaces = rows.map(function (d) { return d.marketplace; });
        var wins         = rows.map(function (d) { return d.cheapest_win_count; });
        var listings     = rows.map(function (d) { return d.listing_count; });

        chart.setOption({
            tooltip: Object.assign(baseTooltip(tc), {
                trigger: "axis",
                axisPointer: { type: "shadow", shadowStyle: { color: "rgba(99,102,241,0.06)" } },
                formatter: function (params) {
                    var idx = params[0].dataIndex;
                    var d = rows[idx];
                    return '<div style="font-weight:700;margin-bottom:6px">' + escapeHtml(d.marketplace) + "</div>" +
                        '<div style="display:flex;justify-content:space-between;gap:24px">' +
                        "<span>Lowest-price wins</span><strong>" + d.cheapest_win_count + "</strong></div>" +
                        '<div style="display:flex;justify-content:space-between;gap:24px">' +
                        "<span>Listings</span><strong>" + formatNumber(d.listing_count) + "</strong></div>" +
                        '<div style="display:flex;justify-content:space-between;gap:24px">' +
                        "<span>Median price</span><strong>" + formatCurrency(d.median_price) + "</strong></div>" +
                        '<div style="display:flex;justify-content:space-between;gap:24px">' +
                        "<span>Price index</span><strong>" + (d.average_price_index != null ? d.average_price_index : "-") + "</strong></div>";
                },
            }),
            grid: {
                left: 8,
                right: 32,
                top: 16,
                bottom: 16,
                containLabel: true,
            },
            xAxis: {
                type: "value",
                axisLabel: { color: tc.textMuted, fontSize: 11 },
                axisLine: { show: false },
                axisTick: { show: false },
                splitLine: { lineStyle: { color: tc.splitLine } },
            },
            yAxis: {
                type: "category",
                data: marketplaces,
                axisLabel: {
                    color: tc.textColor,
                    fontSize: 12,
                    fontWeight: 600,
                    width: 140,
                    overflow: "truncate",
                    ellipsis: "...",
                },
                axisLine: { show: false },
                axisTick: { show: false },
            },
            series: [
                {
                    name: "Lowest-price wins",
                    type: "bar",
                    data: wins,
                    barMaxWidth: 22,
                    itemStyle: {
                        borderRadius: [0, 6, 6, 0],
                        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                            { offset: 0, color: "#6366f1" },
                            { offset: 1, color: "#06b6d4" },
                        ]),
                    },
                    emphasis: {
                        itemStyle: {
                            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                                { offset: 0, color: "#818cf8" },
                                { offset: 1, color: "#22d3ee" },
                            ]),
                        },
                    },
                    label: {
                        show: true,
                        position: "right",
                        color: tc.textMuted,
                        fontSize: 11,
                        fontWeight: 700,
                        formatter: function (p) {
                            return p.value > 0 ? p.value : "";
                        },
                    },
                    animationDelay: function (idx) { return idx * 60; },
                },
                {
                    name: "Listings",
                    type: "bar",
                    data: listings,
                    barMaxWidth: 14,
                    itemStyle: {
                        borderRadius: [0, 4, 4, 0],
                        color: isDark() ? "rgba(99,102,241,0.25)" : "rgba(99,102,241,0.12)",
                    },
                    emphasis: {
                        itemStyle: {
                            color: "rgba(99,102,241,0.3)",
                        },
                    },
                    animationDelay: function (idx) { return idx * 60 + 30; },
                },
            ],
            animationEasing: "cubicOut",
            animationDuration: 800,
        });
    }

    function renderSpreadChart(container, data) {
        if (!data || !data.length) {
            showEmpty(container, "No products with two or more marketplace prices are available.");
            return;
        }

        var rows = data.slice(0, 12).reverse();
        var tc = themeColors();
        var chart = getOrCreateChart(container, "spread");

        container.style.minHeight = Math.max(460, rows.length * 56 + 100) + "px";
        chart.resize();

        var products = rows.map(function (d) {
            return d.product_code || "Unknown SKU";
        });

        var rangeData = rows.map(function (d) {
            return [d.min_price, d.max_price];
        });

        var medianData = rows.map(function (d) { return d.median_price; });
        var minPrices = rows.map(function (d) { return d.min_price; });

        chart.setOption({
            tooltip: Object.assign(baseTooltip(tc), {
                trigger: "axis",
                axisPointer: { type: "shadow", shadowStyle: { color: "rgba(245,158,11,0.06)" } },
                formatter: function (params) {
                    var idx = params[0].dataIndex;
                    var d = rows[idx];
                    var code = d.product_code || "Unknown SKU";
                    return '<div style="font-weight:700;margin-bottom:6px">' + escapeHtml(code) + "</div>" +
                        '<div style="display:flex;justify-content:space-between;gap:24px">' +
                        "<span>Min</span><strong>" + formatCurrency(d.min_price) + "</strong></div>" +
                        '<div style="display:flex;justify-content:space-between;gap:24px">' +
                        "<span>Median</span><strong>" + formatCurrency(d.median_price) + "</strong></div>" +
                        '<div style="display:flex;justify-content:space-between;gap:24px">' +
                        "<span>Max</span><strong>" + formatCurrency(d.max_price) + "</strong></div>" +
                        '<div style="display:flex;justify-content:space-between;gap:24px">' +
                        "<span>Spread</span><strong>" + d.spread_percent + "%</strong></div>" +
                        '<div style="display:flex;justify-content:space-between;gap:24px;margin-top:4px">' +
                        "<span>Cheapest</span><strong>" + escapeHtml(d.cheapest_marketplaces.join(", ")) + "</strong></div>";
                },
            }),
            grid: {
                left: 190,
                right: 32,
                top: 16,
                bottom: 16,
                containLabel: false,
            },
            xAxis: {
                type: "value",
                axisLabel: {
                    color: tc.textMuted,
                    fontSize: 11,
                    formatter: function (v) { return formatCurrency(v); },
                },
                axisLine: { show: false },
                axisTick: { show: false },
                splitLine: { lineStyle: { color: tc.splitLine } },
            },
            yAxis: {
                type: "category",
                data: products,
                axisLabel: {
                    color: tc.textColor,
                    fontSize: 10,
                    fontWeight: 600,
                    fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace",
                    width: 172,
                    overflow: "truncate",
                    ellipsis: "",
                    margin: 10,
                },
                axisLine: { show: false },
                axisTick: { show: false },
            },
            series: [
                {
                    name: "_base",
                    type: "bar",
                    stack: "range",
                    data: minPrices,
                    barMaxWidth: 16,
                    itemStyle: { color: "transparent" },
                    emphasis: { itemStyle: { color: "transparent" } },
                    tooltip: { show: false },
                },
                {
                    name: "Price Range",
                    type: "bar",
                    stack: "range",
                    data: rows.map(function (d) { return d.max_price - d.min_price; }),
                    barMaxWidth: 16,
                    itemStyle: {
                        borderRadius: [0, 6, 6, 0],
                        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                            { offset: 0, color: "#f59e0b" },
                            { offset: 1, color: "#ef4444" },
                        ]),
                    },
                    emphasis: {
                        itemStyle: {
                            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                                { offset: 0, color: "#fbbf24" },
                                { offset: 1, color: "#f87171" },
                            ]),
                        },
                    },
                    animationDelay: function (idx) { return idx * 70; },
                },
                {
                    name: "Median",
                    type: "scatter",
                    data: medianData,
                    symbol: "circle",
                    symbolSize: 10,
                    itemStyle: {
                        color: "#6366f1",
                        borderColor: tc.cardBg,
                        borderWidth: 2,
                    },
                    z: 10,
                    animationDelay: function (idx) { return idx * 70 + 400; },
                },
            ],
            animationEasing: "cubicOut",
            animationDuration: 800,
        });
    }

    function renderHeatmap(container, data) {
        if (!data.categories || !data.categories.length || !data.marketplaces || !data.marketplaces.length) {
            showEmpty(container, "No category and marketplace coverage data is available.");
            return;
        }

        var tc = themeColors();
        var chart = getOrCreateChart(container, "heatmap");

        container.style.minHeight = Math.max(460, data.marketplaces.length * 38 + 140) + "px";
        chart.resize();

        var heatData = [];
        var cellMap = {};
        data.cells.forEach(function (cell) {
            cellMap[cell.marketplace + "|||" + cell.category] = cell.listing_count;
        });
        data.marketplaces.forEach(function (mp, mi) {
            data.categories.forEach(function (cat, ci) {
                var count = cellMap[mp + "|||" + cat] || 0;
                heatData.push([ci, mi, count]);
            });
        });

        var darkHeatColors = ["#0b1120", "#1e1b4b", "#312e81", "#4338ca", "#6366f1", "#818cf8"];
        var lightHeatColors = ["#f8fafc", "#e0e7ff", "#c7d2fe", "#a5b4fc", "#818cf8", "#6366f1"];

        chart.setOption({
            tooltip: Object.assign(baseTooltip(tc), {
                position: "top",
                formatter: function (params) {
                    var mp = data.marketplaces[params.value[1]];
                    var cat = data.categories[params.value[0]];
                    var count = params.value[2];
                    return '<div style="font-weight:700;margin-bottom:4px">' + escapeHtml(mp) + "</div>" +
                        '<div style="display:flex;justify-content:space-between;gap:20px">' +
                        "<span>" + escapeHtml(cat) + "</span><strong>" + formatNumber(count) + " listings</strong></div>";
                },
            }),
            grid: {
                left: 8,
                right: 80,
                top: 16,
                bottom: 8,
                containLabel: true,
            },
            xAxis: {
                type: "category",
                data: data.categories,
                position: "top",
                axisLabel: { color: tc.textColor, fontSize: 12, fontWeight: 700 },
                axisLine: { show: false },
                axisTick: { show: false },
                splitLine: { show: false },
            },
            yAxis: {
                type: "category",
                data: data.marketplaces,
                axisLabel: {
                    color: tc.textColor,
                    fontSize: 11,
                    fontWeight: 600,
                    width: 130,
                    overflow: "truncate",
                    ellipsis: "...",
                },
                axisLine: { show: false },
                axisTick: { show: false },
                splitLine: { show: false },
            },
            visualMap: {
                min: 0,
                max: data.max_count || 1,
                calculable: true,
                orient: "vertical",
                right: 0,
                top: "center",
                itemWidth: 14,
                itemHeight: 180,
                text: ["High", "Low"],
                textStyle: { color: tc.textMuted, fontSize: 11 },
                inRange: {
                    color: isDark() ? darkHeatColors : lightHeatColors,
                },
            },
            series: [{
                type: "heatmap",
                data: heatData,
                label: {
                    show: true,
                    color: tc.textColor,
                    fontSize: 12,
                    fontWeight: 700,
                    formatter: function (p) { return p.value[2] > 0 ? formatNumber(p.value[2]) : ""; },
                },
                itemStyle: {
                    borderColor: tc.cardBg,
                    borderWidth: 3,
                    borderRadius: 4,
                },
                emphasis: {
                    itemStyle: {
                        borderColor: "#6366f1",
                        borderWidth: 2,
                        shadowBlur: 12,
                        shadowColor: "rgba(99,102,241,0.3)",
                    },
                },
            }],
            animationDuration: 600,
            animationEasing: "cubicOut",
        });
    }

    var resizeTimeout;
    window.addEventListener("resize", function () {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(resizeAll, 200);
    });

    window.dashboardCharts = {
        renderMarketplaceChart: renderMarketplaceChart,
        renderSpreadChart: renderSpreadChart,
        renderHeatmap: renderHeatmap,
        formatNumber: formatNumber,
        refreshTheme: function () {
            Object.keys(chartInstances).forEach(function (key) {
                var chart = chartInstances[key];
                if (chart && !chart.isDisposed()) {
                    chart.dispose();
                }
            });
            chartInstances = {};
        },
        resizeAll: resizeAll,
    };
}());
