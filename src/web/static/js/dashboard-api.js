(function () {
    "use strict";

    window.dashboardApi = {
        async fetchDashboardData(category) {
            const params = new URLSearchParams();
            if (category) {
                params.set("category", category);
            }
            const url = `/api/dashboard-data${params.toString() ? `?${params}` : ""}`;
            const response = await fetch(url, {
                headers: {
                    Accept: "application/json",
                },
            });
            if (!response.ok) {
                throw new Error(`Dashboard API failed with status ${response.status}`);
            }
            return response.json();
        },
    };
}());
