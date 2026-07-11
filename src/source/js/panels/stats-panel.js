// ═══════════════════════════════════════════════════════════════════════
//  Stats Panel — 暗空统计面板、波特尔等级分布
// ═══════════════════════════════════════════════════════════════════════

/**
 * 计算数据统计
 * @param {Array} data - 光污染数据
 * @returns {Object} 统计信息
 */
function calculateStats(data) {
    if (!data || data.length === 0) {
        return {
            darkSkyArea: 0,
            darkSkyPercentage: 0,
            bortleDistribution: {}
        };
    }

    const totalPoints = data.length;
    const darkSkyPoints = data.filter(point => point.bortleClass <= 3).length;
    const darkSkyPercentage = (darkSkyPoints / totalPoints * 100).toFixed(1);

    // 计算波特尔等级分布
    const bortleDistribution = {};
    for (let i = 1; i <= 9; i++) {
        const count = data.filter(point => point.bortleClass === i).length;
        bortleDistribution[i] = {
            count: count,
            percentage: (count / totalPoints * 100).toFixed(1)
        };
    }

    return {
        darkSkyArea: darkSkyPoints,
        darkSkyPercentage: darkSkyPercentage,
        bortleDistribution: bortleDistribution
    };
}

/**
 * 更新统计面板
 * @param {Object} stats - 统计数据
 */
function updateStatsPanel(stats = null) {
    const darkSkyStatsDiv = document.querySelector('.dark-sky-stats');
    const bortleDistributionDiv = document.querySelector('.bortle-distribution');

    if (!darkSkyStatsDiv || !bortleDistributionDiv) return;

    if (!stats) {
        darkSkyStatsDiv.innerHTML = `
            <h4>${getText('darkSkyStats')}</h4>
            <p>${getText('totalDarkSkyArea')}: --</p>
            <p>${getText('darkSkyPercentage')}: --%</p>
        `;

        bortleDistributionDiv.innerHTML = `
            <h4>${getText('bortleDistribution')}</h4>
            <p>暂无数据</p>
        `;
        return;
    }

    // 更新暗空区域统计
    darkSkyStatsDiv.innerHTML = `
        <h4>${getText('darkSkyStats')}</h4>
        <p>${getText('totalDarkSkyArea')}: ${stats.darkSkyArea} 个区域</p>
        <p>${getText('darkSkyPercentage')}: ${stats.darkSkyPercentage}%</p>
    `;

    // 更新波特尔等级分布
    let distributionHTML = `<h4>${getText('bortleDistribution')}</h4>`;
    for (let i = 1; i <= 9; i++) {
        const dist = stats.bortleDistribution[i] || { count: 0, percentage: '0.0' };
        const color = getBortleColor(i);
        distributionHTML += `
            <div class="bortle-bar">
                <span class="label">Class ${i}</span>
                <div class="bar">
                    <div class="fill" style="width: ${dist.percentage}%; background-color: ${color};"></div>
                </div>
                <span class="percentage">${dist.percentage}%</span>
            </div>
        `;
    }
    bortleDistributionDiv.innerHTML = distributionHTML;

    // Show panel in browse mode when data is available
    if (!isAnalysisMode && !isTelescopeMode) {
        const statsPanel = document.querySelector('.stats-panel');
        if (statsPanel) statsPanel.style.display = 'block';
    }
}
