(function () {
    "use strict";

    var state = {
        selectedCategory: "",
    };

    var elements = {
        categoryFilter:   document.getElementById("categoryFilter"),
        refreshButton:    document.getElementById("refreshButton"),
        themeToggle:      document.getElementById("themeToggle"),
        statusBar:        document.getElementById("statusBar"),
        statusMessage:    document.getElementById("statusMessage"),
        metricTotalRows:  document.getElementById("metricTotalRows"),
        metricPricedRows: document.getElementById("metricPricedRows"),
        metricProducts:   document.getElementById("metricProducts"),
        metricMarketplaces: document.getElementById("metricMarketplaces"),
        metricLastScraped:  document.getElementById("metricLastScraped"),
        marketplaceChart: document.getElementById("marketplaceChart"),
        spreadChart:      document.getElementById("spreadChart"),
        heatmapChart:     document.getElementById("heatmapChart"),
        tabButtons:       Array.from(document.querySelectorAll(".chart-tab")),
        chartPanels:      Array.from(document.querySelectorAll(".chart-panel")),
    };

    function getCurrentTheme() {
        return document.documentElement.getAttribute("data-theme") || "light";
    }

    function setTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("dashboard-theme", theme);
    }

    if (elements.themeToggle) {
        elements.themeToggle.addEventListener("click", function () {
            var next = getCurrentTheme() === "dark" ? "light" : "dark";
            setTheme(next);
            window.dashboardCharts.refreshTheme();
            loadDashboard();
        });
    }

    function setLoading(isLoading) {
        elements.refreshButton.disabled = isLoading;
        elements.refreshButton.querySelector("span").textContent = isLoading ? "Loading…" : "Refresh";

        if (elements.statusBar) {
            elements.statusBar.classList.toggle("is-loading", isLoading);
            elements.statusBar.classList.remove("is-error");
        }
    }

    function setStatus(message, isError) {
        if (elements.statusMessage) {
            elements.statusMessage.textContent = message || "Ready";
        }
        if (elements.statusBar) {
            elements.statusBar.classList.toggle("is-error", !!isError);
            elements.statusBar.classList.remove("is-loading");
        }
    }

    function showSkeleton(container) {
        container.innerHTML =
            '<div class="skeleton skeleton-chart"></div>';
    }

    function populateCategories(categories) {
        var current = elements.categoryFilter.value;
        while (elements.categoryFilter.options.length > 1) {
            elements.categoryFilter.remove(1);
        }
        categories.forEach(function (category) {
            var option = document.createElement("option");
            option.value = category;
            option.textContent = category;
            elements.categoryFilter.appendChild(option);
        });
        if (categories.indexOf(current) !== -1) {
            elements.categoryFilter.value = current;
        }
    }

    function animateValue(element, endValue, isNumeric) {
        if (!isNumeric || isNaN(endValue)) {
            element.textContent = endValue;
            element.style.animation = "countUp 0.4s ease forwards";
            return;
        }

        var start = 0;
        var end = parseInt(endValue, 10);
        var duration = 700;
        var startTime = null;

        element.style.animation = "countUp 0.4s ease forwards";

        function step(timestamp) {
            if (!startTime) startTime = timestamp;
            var progress = Math.min((timestamp - startTime) / duration, 1);
            var eased = 1 - Math.pow(1 - progress, 3);
            var current = Math.floor(eased * end);
            element.textContent = window.dashboardCharts.formatNumber(current);
            if (progress < 1) {
                requestAnimationFrame(step);
            } else {
                element.textContent = window.dashboardCharts.formatNumber(end);
            }
        }

        requestAnimationFrame(step);
    }

    function renderSummary(summary) {
        animateValue(elements.metricTotalRows, summary.total_rows, true);
        animateValue(elements.metricPricedRows, summary.priced_rows, true);
        animateValue(elements.metricProducts, summary.product_count, true);
        animateValue(elements.metricMarketplaces, summary.marketplace_count, true);
        animateValue(elements.metricLastScraped, summary.last_scraped_at || "-", false);
    }

    function renderDashboard(data) {
        populateCategories(data.filters.categories || []);
        renderSummary(data.summary);

        window.dashboardCharts.renderMarketplaceChart(
            elements.marketplaceChart,
            data.marketplace_competitiveness || []
        );
        window.dashboardCharts.renderSpreadChart(
            elements.spreadChart,
            data.product_price_spread || []
        );
        window.dashboardCharts.renderHeatmap(
            elements.heatmapChart,
            data.category_marketplace_heatmap || { categories: [], marketplaces: [], cells: [], max_count: 0 }
        );

        setTimeout(function () {
            window.dashboardCharts.resizeAll();
        }, 50);
    }

    function activateTab(targetId) {
        elements.tabButtons.forEach(function (button) {
            var isActive = button.dataset.target === targetId;
            button.classList.toggle("is-active", isActive);
            button.setAttribute("aria-selected", String(isActive));
        });

        elements.chartPanels.forEach(function (panel) {
            var isActive = panel.id === targetId;
            panel.classList.toggle("is-active", isActive);
            panel.hidden = !isActive;

            if (isActive) {
                panel.style.animation = "none";
                void panel.offsetHeight;
                panel.style.animation = "";
            }
        });

        setTimeout(function () {
            window.dashboardCharts.resizeAll();
        }, 50);
    }

    async function loadDashboard() {
        setLoading(true);
        setStatus("Loading dashboard data…");

        showSkeleton(elements.marketplaceChart);
        showSkeleton(elements.spreadChart);
        showSkeleton(elements.heatmapChart);

        try {
            var data = await window.dashboardApi.fetchDashboardData(state.selectedCategory);
            renderDashboard(data);
            var scope = state.selectedCategory
                ? state.selectedCategory + " category"
                : "all categories";
            setStatus("Dashboard updated for " + scope + ".");
        } catch (error) {
            setStatus("Unable to load dashboard data: " + error.message, true);
            [elements.marketplaceChart, elements.spreadChart, elements.heatmapChart].forEach(function (container) {
                container.innerHTML = '<div class="chart-error">' +
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48">' +
                    '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>' +
                    "<span>Unable to load chart data.</span></div>";
            });
        } finally {
            setLoading(false);
        }
    }

    elements.tabButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            activateTab(button.dataset.target);
        });
    });

    elements.categoryFilter.addEventListener("change", function () {
        state.selectedCategory = elements.categoryFilter.value;
        loadDashboard();
    });

    elements.refreshButton.addEventListener("click", function () {
        loadDashboard();
    });

    activateTab("marketplacePanel");
    loadDashboard();
}());
