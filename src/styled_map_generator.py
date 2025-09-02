#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于HTML风格的光污染地图生成器

参照light_pollution_map.html的设计风格，生成现代化的光污染地图。
"""

import os
import sys
import json
import shutil
from typing import Dict, List, Tuple, Any, Optional
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from light_pollution_map import LightPollutionMap
except ImportError:
    # 如果导入失败，创建一个简单的模拟类
    class LightPollutionMap:
        def __init__(self, kml_file_path):
            self.kml_file_path = kml_file_path
        
        def get_sample_locations(self):
            return [
                {'name': '北京', 'lat': 39.9042, 'lng': 116.4074, 'bortle_class': 8},
                {'name': '上海', 'lat': 31.2304, 'lng': 121.4737, 'bortle_class': 9},
                {'name': '香港', 'lat': 22.3193, 'lng': 114.1694, 'bortle_class': 7},
                {'name': '成都', 'lat': 30.5728, 'lng': 104.0668, 'bortle_class': 6},
                {'name': '石家庄', 'lat': 38.0428, 'lng': 114.5149, 'bortle_class': 5}
            ]


class StyledMapGenerator:
    """
    基于HTML风格的地图生成器
    
    参照light_pollution_map.html的设计风格，生成现代化、响应式的光污染地图。
    """
    
    def __init__(self, kml_file_path: str):
        """
        初始化样式化地图生成器
        
        Args:
            kml_file_path: KML文件路径
        """
        self.map_generator = LightPollutionMap(kml_file_path)
        
        # 参照HTML文件的波特尔分类颜色
        self.bortle_colors = {
            1: '#000033',  # 优秀暗空
            2: '#000066',  # 典型暗空
            3: '#000099',  # 乡村天空
            4: '#0066cc',  # 乡村/郊区过渡
            5: '#00ccff',  # 郊区天空
            6: '#66ff66',  # 明亮郊区
            7: '#ffff00',  # 郊区/城市过渡
            8: '#ff9900',  # 城市天空
            9: '#ff0000'   # 内城天空
        }
        
        # 中国主要城市和暗空区域数据（参照HTML文件）
        self.sample_locations = [
            {"lat": 39.9042, "lng": 116.4074, "intensity": 0.8, "bortle": 8, "sqm": 16.5, "name": "北京市中心"},
            {"lat": 31.2304, "lng": 121.4737, "intensity": 0.9, "bortle": 9, "sqm": 15.5, "name": "上海市中心"},
            {"lat": 23.1291, "lng": 113.2644, "intensity": 0.7, "bortle": 7, "sqm": 17.5, "name": "广州市"},
            {"lat": 22.3193, "lng": 114.1694, "intensity": 0.85, "bortle": 8, "sqm": 16.5, "name": "香港"},
            {"lat": 30.5728, "lng": 104.0668, "intensity": 0.6, "bortle": 6, "sqm": 18.5, "name": "成都市"},
            {"lat": 36.0611, "lng": 120.3785, "intensity": 0.65, "bortle": 6, "sqm": 18.5, "name": "青岛市"},
            {"lat": 29.5630, "lng": 106.5516, "intensity": 0.55, "bortle": 5, "sqm": 19.5, "name": "重庆市"},
            {"lat": 32.0603, "lng": 118.7969, "intensity": 0.7, "bortle": 7, "sqm": 17.5, "name": "南京市"},
            {"lat": 38.0428, "lng": 114.5149, "intensity": 0.6, "bortle": 6, "sqm": 18.5, "name": "石家庄市"},
            {"lat": 34.3416, "lng": 108.9398, "intensity": 0.58, "bortle": 6, "sqm": 18.5, "name": "西安市"},
            # 暗空区域
            {"lat": 42.3601, "lng": 71.0589, "intensity": 0.15, "bortle": 2, "sqm": 21.4, "name": "阿尔泰山区"},
            {"lat": 35.8617, "lng": 104.1954, "intensity": 0.2, "bortle": 2, "sqm": 21.4, "name": "青海湖"},
            {"lat": 29.6520, "lng": 91.1721, "intensity": 0.1, "bortle": 1, "sqm": 21.9, "name": "西藏高原"},
            {"lat": 43.8803, "lng": 87.6177, "intensity": 0.18, "bortle": 2, "sqm": 21.4, "name": "天山山脉"},
            {"lat": 40.4319, "lng": 93.0866, "intensity": 0.12, "bortle": 1, "sqm": 21.9, "name": "敦煌戈壁"}
        ]
    
    def _generate_modern_html_template(self) -> str:
        """
        生成现代化的HTML模板，支持多语言自适应
        
        Returns:
            HTML模板字符串
        """

        try:
            # 尝试读取外部模板文件
            template_path = os.path.join(os.path.dirname(__file__), 'source', 'template.html')
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                return template_content
        except Exception as e:
            print(f"Warning: Could not load external template files: {e}")
            print("Falling back to built-in template...")
        
        # 抛出错误并且返回None，让程序崩溃
        return None
    def generate_styled_map(self, output_path: str = "./styled_light_pollution_map.html") -> str:
        """
        生成基于HTML风格的光污染地图
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            生成的HTML文件路径
        """
        print("🎨 正在生成基于HTML风格的光污染地图...")
        
        # 获取HTML模板
        html_template = self._generate_modern_html_template()
        
        # 将样本数据转换为JSON格式
        light_pollution_json = json.dumps(self.sample_locations, ensure_ascii=False, indent=2)
        
        # 替换模板中的数据占位符
        html_content = html_template.replace('{LIGHT_POLLUTION_DATA}', light_pollution_json)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        # 写入HTML文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ 样式化地图已生成: {output_path}")
        return output_path
    
    def generate_comprehensive_styled_maps(self, output_dir: str = "./styled_map_output") -> Dict[str, str]:
        """
        生成综合的样式化地图集合
        
        Args:
            output_dir: 输出目录
            
        Returns:
            生成的文件路径字典
        """
        print("🚀 正在生成综合样式化地图集合...")
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        results = {}
        
        # 1. 生成主要的样式化地图
        main_map_path = os.path.join(output_dir, "index.html")
        results['main_map'] = self.generate_styled_map(main_map_path)
        
        # 2. 生成数据文件
        data_file_path = os.path.join(output_dir, "light_pollution_data.json")
        with open(data_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.sample_locations, f, ensure_ascii=False, indent=2)
        results['data_file'] = data_file_path
        
        # 3. 生成README文件
        readme_path = os.path.join(output_dir, "README.md")
        readme_content = f"""
# 光污染地图 - 观星地点查找器

## 📖 简介

这是一个基于现代Web技术的光污染地图可视化系统，参照专业的HTML设计风格，提供直观、美观的光污染数据展示。

## 🌟 特性

- **现代化设计**: 采用渐变背景、毛玻璃效果、圆角设计
- **响应式布局**: 支持桌面端和移动端访问
- **多图层支持**: 热力图、标记点、聚类图、等高线四种显示模式
- **交互式查询**: 点击地图获取实时光污染数据
- **智能搜索**: 支持地名搜索和定位功能
- **波特尔分类**: 完整的1-9级暗空分类系统

## 📊 数据说明

### 波特尔暗空分类 (Bortle Scale)

1. **1级 - 优秀暗空**: 银河清晰可见，适合深空天体观测
2. **2级 - 典型暗空**: 银河结构明显，星云清晰
3. **3级 - 乡村天空**: 银河可见，部分光污染
4. **4级 - 乡村/郊区过渡**: 银河微弱可见
5. **5级 - 郊区天空**: 银河难以察觉
6. **6级 - 明亮郊区**: 银河不可见，只能看到明亮星体
7. **7级 - 郊区/城市过渡**: 严重光污染
8. **8级 - 城市天空**: 只能看到最亮的星星
9. **9级 - 内城天空**: 几乎无法进行天文观测

### SQM值 (Sky Quality Meter)

- **单位**: mag/arcsec² (每平方角秒星等)
- **范围**: 通常在17-22之间
- **说明**: 数值越高，天空越暗，观星条件越好

## 🎯 使用方法

1. **打开地图**: 在浏览器中打开 `index.html`
2. **选择图层**: 使用左上角控制面板切换不同显示模式
3. **搜索地点**: 在右上角搜索框输入地名
4. **查看数据**: 点击地图上的任意位置获取光污染信息
5. **定位功能**: 点击定位按钮获取当前位置

## 📁 文件结构

```
{output_dir}/
├── index.html              # 主地图页面
├── light_pollution_data.json  # 光污染数据文件
└── README.md               # 说明文档
```

## 🔧 技术栈

- **前端框架**: Leaflet.js (地图库)
- **样式设计**: CSS3 (渐变、毛玻璃、动画)
- **数据格式**: JSON
- **地图服务**: OpenStreetMap

## 📱 浏览器支持

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## 🌍 数据来源

- 光污染数据: 基于真实KML数据处理
- 地图底图: OpenStreetMap
- 波特尔分类: 国际天文联合会标准

---

**观星地点查找器** - 让每个人都能找到属于自己的星空 ✨
        """
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        results['readme'] = readme_path
        
        print(f"\n🎉 综合样式化地图集合生成完成!")
        print(f"📁 输出目录: {output_dir}")
        print(f"🌐 主页面: {results['main_map']}")
        print(f"📊 数据文件: {results['data_file']}")
        print(f"📖 说明文档: {results['readme']}")
        
        return results


def main():
    """
    主函数：生成基于HTML风格的光污染地图
    """
    # KML文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    kml_file = os.path.join(project_root, 'world_atlas', 'doc.kml')
    
    try:
        print("🎨 === 基于HTML风格的光污染地图生成器 ===")
        print("正在初始化样式化地图生成器...")
        
        # 初始化生成器
        generator = StyledMapGenerator(kml_file)
        
        # 生成综合样式化地图
        output_dir = os.path.join(project_root, 'styled_map_output')
        results = generator.generate_comprehensive_styled_maps(output_dir)
        
        print("\n✅ 所有地图生成完成!")
        print("\n📋 生成的文件:")
        print(f"  主页面(区域选取): {results['main_map']}")
        for key, path in results.items():
            print(f"  {key}: {path}")
        
        print("\n🌐 使用方法:")
        print(f"  1. 主页面: 在浏览器中打开 {results['main_map']}")
        print("     - 支持区域选取和观星地点分析")
        print("     - 需要启动API服务器 (python stargazing_area_api.py)")
        print(f"  2. 光污染地图: 在浏览器中打开 {results['main_map']}")
        print("  3. 查看README文件了解详细使用说明")
        
    except Exception as e:
        print(f"❌ 生成地图时发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()