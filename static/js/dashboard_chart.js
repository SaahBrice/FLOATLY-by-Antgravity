/**
 * Dashboard Chart Component for Floatly
 * 
 * Alpine.js component for rendering Chart.js charts on the dashboard
 */

function dashboardChart() {
    return {
        chart: null,
        period: 1,
        chartType: 'line',
        loading: true,
        initialized: false,
        chartData: null,
        summary: {
            total_deposits: 0,
            total_withdrawals: 0,
            total_profit: 0,
            net_flow: 0
        },

        init() {
            // Prevent double initialization
            if (this.initialized) return;
            this.initialized = true;

            // Wait for Chart.js to fully load
            const checkChart = () => {
                if (typeof Chart !== 'undefined') {
                    this.fetchData();
                } else {
                    setTimeout(checkChart, 100);
                }
            };
            setTimeout(checkChart, 200);

            // Watch for chart type changes
            this.$watch('chartType', () => {
                if (this.chartData) {
                    this.renderChart(this.chartData.labels, this.chartData.datasets);
                }
            });
        },

        formatCFA(amount) {
            if (!amount && amount !== 0) return '0';
            return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(amount);
        },

        setPeriod(days) {
            this.period = days;
            this.fetchData();
        },

        async fetchData() {
            this.loading = true;

            // Get kiosk from URL params
            const urlParams = new URLSearchParams(window.location.search);
            const kiosk = urlParams.get('kiosk') || '';

            try {
                const response = await fetch(`/api/chart-data/?period=${this.period}&kiosk=${kiosk}`);
                const data = await response.json();

                if (data.error) {
                    console.error('Chart data error:', data.error);
                    this.loading = false;
                    return;
                }

                this.summary = data.summary;
                this.chartData = { labels: data.labels, datasets: data.datasets };
                this.renderChart(data.labels, data.datasets);
            } catch (error) {
                console.error('Failed to fetch chart data:', error);
            }

            this.loading = false;
        },

        renderChart(labels, datasets) {
            const ctx = document.getElementById('dashboardChart');
            if (!ctx) return;

            // Destroy existing chart
            if (this.chart) {
                this.chart.destroy();
            }

            const isLine = this.chartType === 'line';

            this.chart = new Chart(ctx, {
                type: isLine ? 'line' : 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Cash In',
                            data: datasets.deposits,
                            borderColor: '#22c55e',
                            backgroundColor: isLine ? 'rgba(34, 197, 94, 0.1)' : 'rgba(34, 197, 94, 0.6)',
                            fill: isLine,
                            tension: 0.4,
                            borderWidth: 2,
                            pointRadius: isLine ? 3 : 0,
                            pointBackgroundColor: '#22c55e'
                        },
                        {
                            label: 'Cash Out',
                            data: datasets.withdrawals,
                            borderColor: '#f97316',
                            backgroundColor: isLine ? 'rgba(249, 115, 22, 0.1)' : 'rgba(249, 115, 22, 0.6)',
                            fill: isLine,
                            tension: 0.4,
                            borderWidth: 2,
                            pointRadius: isLine ? 3 : 0,
                            pointBackgroundColor: '#f97316'
                        },
                        {
                            label: 'Profit',
                            data: datasets.profits,
                            borderColor: '#a855f7',
                            backgroundColor: isLine ? 'rgba(168, 85, 247, 0.1)' : 'rgba(168, 85, 247, 0.6)',
                            fill: isLine,
                            tension: 0.4,
                            borderWidth: 2,
                            pointRadius: isLine ? 3 : 0,
                            pointBackgroundColor: '#a855f7'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            backgroundColor: 'rgba(15, 23, 42, 0.95)',
                            titleColor: '#fff',
                            bodyColor: '#94a3b8',
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            borderWidth: 1,
                            padding: 12,
                            cornerRadius: 8,
                            callbacks: {
                                label: (context) => {
                                    return `${context.dataset.label}: ${new Intl.NumberFormat('fr-FR').format(context.raw)} CFA`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                color: 'rgba(255, 255, 255, 0.4)',
                                font: { size: 10 }
                            }
                        },
                        y: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.05)'
                            },
                            ticks: {
                                color: 'rgba(255, 255, 255, 0.4)',
                                font: { size: 10 },
                                callback: (value) => {
                                    if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
                                    if (value >= 1000) return (value / 1000).toFixed(0) + 'K';
                                    return value;
                                }
                            }
                        }
                    }
                }
            });
        }
    };
}
