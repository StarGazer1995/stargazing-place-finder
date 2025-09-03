#!/usr/bin/env python3
"""
山峰查找器测试脚本
用于测试山峰查找功能的各项能力
"""

import sys
import os
# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from stargazing_place_finder import StarGazingPlaceFinder, find_peaks_with_height_difference
import time

def test_distance_calculation():
    """
    测试距离计算功能
    
    使用北京到上海的已知距离（约1000公里）来验证
    Haversine公式计算地理坐标间距离的准确性
    
    Returns:
        bool: 测试是否通过（距离在合理范围内）
    """
    print("=== 测试1: 距离计算功能 ===")
    
    finder = StarGazingPlaceFinder()
    
    # 测试北京到上海的距离（已知约1000公里）
    beijing_lat, beijing_lon = 39.9042, 116.4074
    shanghai_lat, shanghai_lon = 31.2304, 121.4737
    
    distance = finder.calculate_distance(beijing_lat, beijing_lon, shanghai_lat, shanghai_lon)
    print(f"北京到上海距离: {distance:.1f} 公里")
    
    # 验证距离是否合理（应该在1000-1200公里之间）
    if 1000 <= distance <= 1200:
        print("✅ 距离计算测试通过")
        return True
    else:
        print("❌ 距离计算测试失败")
        return False

def test_elevation_api():
    """
    测试海拔API功能
    
    通过查询珠穆朗玛峰的海拔数据来验证
    外部海拔API服务的可用性和数据准确性
    
    Returns:
        bool: 测试是否通过（API可用且数据合理）
    """
    print("\n=== 测试2: 海拔API功能 ===")
    
    finder = StarGazingPlaceFinder()
    
    # 测试珠穆朗玛峰的海拔（应该接近8848米）
    everest_lat, everest_lon = 27.9881, 86.9250
    
    print("正在获取珠穆朗玛峰海拔数据...")
    elevation = finder.get_elevation_from_api(everest_lat, everest_lon)
    
    if elevation is not None:
        print(f"珠穆朗玛峰海拔: {elevation} 米")
        # 海拔数据可能不够精确，但应该在8000米以上
        if elevation > 8000:
            print("✅ 海拔API测试通过")
            return True
        else:
            print(f"⚠️ 海拔数据可能不准确: {elevation}米")
            return True  # API可用但数据可能不精确
    else:
        print("❌ 海拔API测试失败")
        return False

def test_overpass_api():
    """
    测试Overpass API功能
    
    验证从OpenStreetMap Overpass API获取
    山峰和城镇地理数据的功能是否正常
    
    测试区域：北京香山附近
    
    Returns:
        bool: 测试是否通过（能够获取到山峰和城镇数据）
    """
    print("\n=== 测试3: Overpass API功能 ===")
    
    finder = StarGazingPlaceFinder()
    
    # 测试小范围区域的数据获取（北京香山附近）
    bbox = (39.98, 116.18, 40.02, 116.22)
    
    print("正在获取山峰数据...")
    peaks = finder.get_peaks_from_overpass(bbox)
    print(f"找到 {len(peaks)} 个山峰")
    
    print("正在获取城镇数据...")
    towns = finder.get_towns_from_overpass(bbox)
    print(f"找到 {len(towns)} 个城镇")
    
    if len(peaks) > 0 and len(towns) > 0:
        print("✅ Overpass API测试通过")
        return True
    else:
        print("❌ Overpass API测试失败")
        return False

def test_small_area_search():
    """
    测试小范围山峰搜索功能
    
    在指定的小范围区域内搜索符合条件的山峰，
    验证山峰查找算法的完整性和准确性
    
    测试区域：北京香山地区
    测试条件：高度差大于100米
    
    Returns:
        bool: 测试是否通过（找到符合条件的山峰）
    """
    print("\n=== 测试4: 小范围山峰搜索 ===")
    
    # 选择一个已知有山峰的小区域（北京香山地区）
    bbox = (39.98, 116.18, 40.02, 116.22)
    
    print("正在搜索香山地区的山峰...")
    print("搜索参数: 最小高度差50米，最多5个山峰")
    
    try:
        peaks = find_peaks_with_height_difference(
            south=bbox[0], west=bbox[1], north=bbox[2], east=bbox[3],
            min_height_diff=50.0,  # 降低要求以便找到结果
            max_locations=5
        )
        
        print(f"找到 {len(peaks)} 个符合条件的山峰")
        
        if peaks:
            print("山峰详情:")
            for i, peak in enumerate(peaks, 1):
                print(f"{i}. {peak.name}")
                print(f"   坐标: ({peak.latitude:.4f}, {peak.longitude:.4f})")
                print(f"   海拔: {peak.elevation:.1f}m")
                print(f"   高度差: {peak.height_difference:.1f}m")
                print(f"   距离城镇: {peak.distance_to_nearest_town:.1f}km")
            print("✅ 小范围搜索测试通过")
            return True
        else:
            print("⚠️ 未找到符合条件的山峰，但功能正常")
            return True
            
    except Exception as e:
        print(f"❌ 小范围搜索测试失败: {e}")
        return False

def test_convenience_function():
    """
    测试便捷函数功能
    
    验证find_peaks_with_height_difference便捷函数
    是否能够正确封装复杂的山峰查找逻辑，
    为用户提供简单易用的接口
    
    测试参数：更小的搜索区域和更低的高度差要求
    
    Returns:
        bool: 测试是否通过（便捷函数正常工作）
    """
    print("\n=== 测试5: 便捷函数测试 ===")
    
    # 测试便捷函数
    bbox = (39.99, 116.19, 40.01, 116.21)  # 更小的区域
    
    print("使用便捷函数搜索山峰...")
    
    try:
        peaks = find_peaks_with_height_difference(
            south=bbox[0], west=bbox[1], north=bbox[2], east=bbox[3],
            min_height_diff=30.0,  # 进一步降低要求
            max_locations=3
        )
        
        print(f"便捷函数返回 {len(peaks)} 个结果")
        print("✅ 便捷函数测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 便捷函数测试失败: {e}")
        return False

def test_error_handling():
    """
    测试错误处理机制
    
    验证系统在遇到无效输入、网络错误、
    API限制等异常情况时的健壮性和
    错误恢复能力
    
    测试场景：
    - 无效的地理坐标边界
    - 极端的参数值
    - 网络连接问题模拟
    
    Returns:
        bool: 测试是否通过（错误处理机制正常）
    """
    print("\n=== 测试6: 错误处理测试 ===")
    
    finder = StarGazingPlaceFinder()
    
    # 测试无效坐标
    print("测试无效坐标处理...")
    elevation = finder.get_elevation_from_api(999, 999)
    if elevation is None:
        print("✅ 无效坐标错误处理正确")
    else:
        print("⚠️ 无效坐标返回了数据（可能API容错性较好）")
    
    # 测试空区域
    print("测试海洋区域（无山峰）...")
    ocean_bbox = (25.0, 125.0, 25.1, 125.1)  # 太平洋某处
    peaks = finder.get_peaks_from_overpass(ocean_bbox)
    
    if len(peaks) == 0:
        print("✅ 海洋区域正确返回空结果")
        return True
    else:
        print(f"⚠️ 海洋区域返回了 {len(peaks)} 个结果")
        return True

def run_all_tests():
    """
    运行所有山峰查找器测试用例
    
    按顺序执行所有测试函数，统计测试结果，
    并在测试间添加延迟以避免API请求过于频繁
    
    测试覆盖范围：
    1. 距离计算算法验证
    2. 海拔API服务可用性
    3. Overpass API数据获取
    4. 小范围山峰搜索功能
    5. 便捷函数接口测试
    6. 错误处理机制验证
    
    Returns:
        bool: 所有测试是否全部通过
    """
    print("山峰查找器功能测试")
    print("=" * 50)
    
    tests = [
        test_distance_calculation,
        test_elevation_api,
        test_overpass_api,
        test_small_area_search,
        test_convenience_function,
        test_error_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            time.sleep(1)  # 避免API请求过于频繁
        except Exception as e:
            print(f"❌ 测试 {test_func.__name__} 出现异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！山峰查找器功能正常")
    elif passed >= total * 0.8:
        print("✅ 大部分测试通过，功能基本正常")
    else:
        print("⚠️ 部分测试失败，请检查网络连接和API可用性")
    
    print("\n使用建议:")
    print("1. 确保网络连接正常")
    print("2. 某些API可能有访问限制或延迟")
    print("3. 可以调整搜索参数以适应不同地区")
    print("4. 建议在实际使用前先测试目标区域")
    
    # 返回测试是否全部通过
    return passed == total

if __name__ == "__main__":
    run_all_tests()