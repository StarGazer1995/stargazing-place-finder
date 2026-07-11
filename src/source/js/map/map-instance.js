// ═══════════════════════════════════════════════════════════════════════
//  Map — Leaflet 地图实例创建
// ═══════════════════════════════════════════════════════════════════════

let map;

/**
 * 初始化 Leaflet 地图，添加底图和光污染图层。
 * 绑定移动/缩放和点击事件，触发首次数据加载。
 */
function initializeMap() {
    console.log('正在初始化地图...');

    // 创建地图实例 - 关闭所有控件
    map = L.map('map', {
        center: [39.9042, 116.4074], // 北京坐标
        zoom: 8,
        zoomControl: false,  // 关闭缩放控件
        attributionControl: false  // 关闭版权控件
    });

    // 添加底图
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);

    // 添加动态光污染瓦片图层（直接从GeoTIFF采样渲染）
    pollutionTileLayer = L.tileLayer(
        `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.lightPollutionTiles}`,
        {
            maxZoom: 18,
            opacity: 0.75,
            attribution: 'VIIRS DNB 2025'
        }
    ).addTo(map);

    // 不添加任何控件（按用户要求关闭所有控件）

    // 监听地图移动和缩放事件
    map.on('moveend zoomend', debounce(loadCurrentViewData, 300));

    // 监听地图点击事件
    map.on('click', onMapClick);

    // 初始加载数据
    console.log('开始加载光污染数据...');
    loadCurrentViewData();

    console.log('地图初始化完成');
}
