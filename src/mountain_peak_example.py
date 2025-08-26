#!/usr/bin/env python3
"""
山峰查找器使用示例
展示如何在不同地区查找符合条件的山峰
"""

from mountain_peak_finder import MountainPeakFinder, find_peaks_with_height_difference
import json

def example_beijing_area():
    """
    示例1：搜索北京周边地区的山峰
    """
    print("=== 示例1：北京周边山峰搜索 ===")
    
    # 北京周边区域 (延庆、怀柔、密云等山区)
    bbox = (39.8, 115.8, 40.8, 117.2)
    
    # 查找与周围城镇有150米以上高度差的山峰
    peaks = find_peaks_with_height_difference(
        south=bbox[0], west=bbox[1], north=bbox[2], east=bbox[3],
        min_height_diff=150.0,
        max_peaks=15
    )
    
    print(f"找到 {len(peaks)} 个符合条件的山峰：")
    for i, peak in enumerate(peaks[:5], 1):  # 只显示前5个
        print(f"{i}. {peak.name} - 高度差: {peak.height_difference:.1f}m")
    
    return peaks

def example_zhangjiajie_area():
    """
    示例2：搜索张家界地区的山峰
    """
    print("\n=== 示例2：张家界地区山峰搜索 ===")
    
    # 张家界地区
    bbox = (29.0, 110.0, 29.8, 110.8)
    
    finder = MountainPeakFinder(min_height_difference=200.0)
    peaks = finder.find_peaks_in_area(bbox, max_peaks=10)
    
    print(f"找到 {len(peaks)} 个符合条件的山峰：")
    for i, peak in enumerate(peaks[:3], 1):  # 只显示前3个
        print(f"{i}. {peak.name}")
        print(f"   海拔: {peak.elevation:.1f}m")
        print(f"   与{peak.nearest_town_name}的高度差: {peak.height_difference:.1f}m")
    
    return peaks

def example_huangshan_area():
    """
    示例3：搜索黄山地区的山峰
    """
    print("\n=== 示例3：黄山地区山峰搜索 ===")
    
    # 黄山地区
    bbox = (29.8, 118.0, 30.5, 118.8)
    
    finder = MountainPeakFinder(min_height_difference=100.0)
    peaks = finder.find_peaks_in_area(bbox, max_peaks=12)
    
    if peaks:
        print(f"找到 {len(peaks)} 个符合条件的山峰：")
        # 按海拔高度排序显示
        peaks_by_elevation = sorted(peaks, key=lambda p: p.elevation, reverse=True)
        for i, peak in enumerate(peaks_by_elevation[:3], 1):
            print(f"{i}. {peak.name} - 海拔: {peak.elevation:.1f}m")
    
    return peaks

def example_custom_search():
    """
    示例4：自定义搜索参数
    """
    print("\n=== 示例4：自定义搜索参数 ===")
    
    # 用户可以自定义的区域（这里以泰山地区为例）
    bbox = (35.8, 116.8, 36.5, 117.5)
    
    # 创建查找器，设置更高的高度差要求
    finder = MountainPeakFinder(min_height_difference=300.0)
    
    print("搜索参数：")
    print(f"- 区域: 纬度 {bbox[0]}-{bbox[2]}, 经度 {bbox[1]}-{bbox[3]}")
    print(f"- 最小高度差: {finder.min_height_difference}米")
    
    peaks = finder.find_peaks_in_area(bbox, max_peaks=8)
    
    if peaks:
        print(f"\n找到 {len(peaks)} 个符合条件的山峰：")
        for peak in peaks:
            print(f"- {peak.name}: {peak.height_difference:.1f}m高度差")
        
        # 保存结果到文件
        finder.save_results_to_json(peaks, "taishan_area_peaks.json")
    else:
        print("未找到符合条件的山峰，可以尝试降低高度差要求")
    
    return peaks

def example_batch_search():
    """
    示例5：批量搜索多个地区
    """
    print("\n=== 示例5：批量搜索多个地区 ===")
    
    # 定义多个搜索区域
    regions = {
        "华山地区": (34.3, 109.8, 34.8, 110.3),
        "峨眉山地区": (29.3, 103.2, 29.8, 103.7),
        "庐山地区": (29.4, 115.8, 29.8, 116.2)
    }
    
    all_results = {}
    
    for region_name, bbox in regions.items():
        print(f"\n正在搜索 {region_name}...")
        
        finder = MountainPeakFinder(min_height_difference=120.0)
        peaks = finder.find_peaks_in_area(bbox, max_peaks=5)
        
        all_results[region_name] = {
            "peak_count": len(peaks),
            "peaks": [
                {
                    "name": peak.name,
                    "elevation": peak.elevation,
                    "height_difference": peak.height_difference,
                    "coordinates": [peak.latitude, peak.longitude]
                }
                for peak in peaks
            ]
        }
        
        if peaks:
            best_peak = max(peaks, key=lambda p: p.height_difference)
            print(f"最佳山峰: {best_peak.name} (高度差: {best_peak.height_difference:.1f}m)")
        else:
            print("未找到符合条件的山峰")
    
    # 保存批量搜索结果
    with open("batch_mountain_search_results.json", 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print("\n批量搜索结果已保存到: batch_mountain_search_results.json")
    return all_results

def example_integration_with_stargazing():
    """
    示例6：与观星地点查找集成
    展示如何将山峰查找与观星地点选择结合
    """
    print("\n=== 示例6：观星地点山峰筛选 ===")
    
    # 假设这是一个观星候选区域
    bbox = (40.0, 116.0, 40.5, 116.8)  # 北京北部山区
    
    # 查找适合观星的山峰（远离城镇，高度差大）
    finder = MountainPeakFinder(min_height_difference=200.0)
    peaks = finder.find_peaks_in_area(bbox, max_peaks=10)
    
    if peaks:
        print("适合观星的山峰候选：")
        
        # 筛选距离城镇较远的山峰（更少光污染）
        good_stargazing_peaks = [
            peak for peak in peaks 
            if peak.distance_to_nearest_town > 5.0  # 距离城镇5公里以上
        ]
        
        if good_stargazing_peaks:
            print(f"找到 {len(good_stargazing_peaks)} 个适合观星的山峰：")
            for i, peak in enumerate(good_stargazing_peaks, 1):
                print(f"{i}. {peak.name}")
                print(f"   坐标: ({peak.latitude:.4f}, {peak.longitude:.4f})")
                print(f"   海拔: {peak.elevation:.1f}m")
                print(f"   距离城镇: {peak.distance_to_nearest_town:.1f}km")
                print(f"   高度差: {peak.height_difference:.1f}m")
                print(f"   观星评分: {peak.height_difference + peak.distance_to_nearest_town * 10:.1f}")
                print()
        else:
            print("未找到距离城镇足够远的山峰，可以考虑降低距离要求")
    
    return peaks

if __name__ == "__main__":
    print("山峰查找器使用示例")
    print("=" * 50)
    
    try:
        # 运行各种示例
        example_beijing_area()
        example_zhangjiajie_area()
        example_huangshan_area()
        example_custom_search()
        example_batch_search()
        example_integration_with_stargazing()
        
        print("\n=== 所有示例运行完成 ===")
        print("提示：")
        print("1. 可以调整 min_height_difference 参数来改变高度差要求")
        print("2. 可以调整 max_peaks 参数来限制搜索的山峰数量")
        print("3. 可以调整边界框来改变搜索区域")
        print("4. 结果会自动保存为JSON文件供后续使用")
        
    except Exception as e:
        print(f"运行示例时出错: {e}")
        print("请检查网络连接和API可用性")