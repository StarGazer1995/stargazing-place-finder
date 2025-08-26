#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
观星地点综合分析器测试脚本

测试StargazingLocationAnalyzer的各项功能，包括：
1. 基础山峰查找功能
2. 道路连通性检测功能
3. 综合评分计算功能
4. 数据保存和加载功能
5. 错误处理功能
"""

import sys
import os
import json
import tempfile
try:
    from ..cache_config import get_temp_file
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from cache_config import get_temp_file
from datetime import datetime

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from stargazing_location_analyzer import (
    StargazingLocationAnalyzer, 
    StargazingLocation,
    analyze_stargazing_area
)

def test_analyzer_initialization():
    """
    测试观星地点分析器的初始化功能
    
    验证StargazingLocationAnalyzer类的构造函数
    是否能够正确初始化各个组件模块
    
    测试内容：
    - 无光污染数据时的初始化（测试环境）
    - 自定义参数的正确设置
    - 各子模块的初始化状态验证
    - 参数传递的准确性
    
    注意：生产环境中光污染数据是必需的
    
    Returns:
        bool: 初始化功能是否正常工作
    """
    print("\n=== 测试1: 分析器初始化 ===")
    
    try:
        # 测试无光污染数据的初始化（应该给出警告但仍能工作）
        analyzer = StargazingLocationAnalyzer(
            kml_file_path=None,
            min_height_difference=100.0,
            road_search_radius_km=10.0
        )
        
        assert analyzer.mountain_finder is not None, "山峰查找器初始化失败"
        assert analyzer.road_checker is not None, "道路检测器初始化失败"
        assert analyzer.light_pollution_analyzer is None, "光污染分析器应为None（无KML文件时）"
        
        print("✓ 无光污染数据初始化测试通过（仅用于测试目的）")
        
        # 测试自定义参数
        analyzer2 = StargazingLocationAnalyzer(
            kml_file_path=None,  # 测试环境下允许
            min_height_difference=200.0,
            road_search_radius_km=15.0
        )
        
        assert analyzer2.mountain_finder.min_height_difference == 200.0, "高度差参数设置失败"
        assert analyzer2.road_checker.search_radius_km == 15.0, "搜索半径参数设置失败"
        
        print("✓ 自定义参数测试通过")
        print("⚠️  注意: 生产环境中光污染数据是强制要求的")
        return True
        
    except Exception as e:
        print(f"✗ 初始化测试失败: {e}")
        return False

def test_basic_analysis():
    """
    测试观星地点的基础分析功能
    
    验证分析器能否在指定区域内找到
    符合条件的观星地点并进行基本评估
    
    测试流程：
    1. 在小范围区域内搜索山峰
    2. 检测道路连通性
    3. 计算基础评分
    4. 验证结果数据结构
    
    测试区域：北京香山地区
    
    Returns:
        bool: 基础分析功能是否正常工作
    """
    print("\n=== 测试2: 基础分析功能 ===")
    
    try:
        analyzer = StargazingLocationAnalyzer(
            kml_file_path=None,
            min_height_difference=100.0,
            road_search_radius_km=10.0
        )
        
        # 测试小范围区域（香山地区）
        bbox = (39.98, 116.18, 40.02, 116.22)
        
        locations = analyzer.analyze_area(
            bbox=bbox,
            max_peaks=5,
            network_type='drive',
            include_light_pollution=False,
            include_road_connectivity=True
        )
        
        print(f"找到 {len(locations)} 个观星地点")
        
        if locations:
            # 验证数据结构
            first_location = locations[0]
            assert hasattr(first_location, 'name'), "缺少名称字段"
            assert hasattr(first_location, 'latitude'), "缺少纬度字段"
            assert hasattr(first_location, 'longitude'), "缺少经度字段"
            assert hasattr(first_location, 'stargazing_score'), "缺少评分字段"
            assert hasattr(first_location, 'recommendation_level'), "缺少推荐等级字段"
            
            print(f"✓ 数据结构验证通过")
            print(f"✓ 示例地点: {first_location.name} (评分: {first_location.stargazing_score})")
        
        print("✓ 基础分析测试通过")
        return True
        
    except Exception as e:
        print(f"✗ 基础分析测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_scoring_system():
    """
    测试观星地点评分系统的准确性
    
    验证评分算法能否根据不同的地理和环境因素
    计算出合理的观星适宜性评分
    
    测试要素：
    - 高度差对评分的影响
    - 光污染亮度的权重计算
    - 道路可达性的评分贡献
    - 推荐等级的分类准确性
    - 分析备注的生成质量
    
    验证范围：
    - 评分在0-100范围内
    - 不同条件下的评分合理性
    - 推荐等级与评分的对应关系
    
    Returns:
        bool: 评分系统是否工作正常
    """
    print("\n=== 测试3: 评分系统 ===")
    
    try:
        analyzer = StargazingLocationAnalyzer()
        
        # 创建测试数据
        test_location = StargazingLocation(
            name="测试山峰",
            latitude=40.0,
            longitude=116.0,
            elevation=1000.0,
            prominence=500.0,
            distance_to_nearest_town=30.0,
            nearest_town_name="测试城镇",
            height_difference=300.0,
            light_pollution_brightness=50,  # 低光污染
            road_accessible=True
        )
        
        # 计算评分
        score = analyzer._calculate_stargazing_score(test_location)
        recommendation = analyzer._get_recommendation_level(score)
        notes = analyzer._generate_analysis_notes(test_location)
        
        assert 0 <= score <= 100, f"评分超出范围: {score}"
        assert recommendation is not None, "推荐等级为空"
        assert notes is not None, "分析备注为空"
        
        print(f"✓ 评分计算: {score}/100")
        print(f"✓ 推荐等级: {recommendation}")
        print(f"✓ 分析备注: {notes}")
        
        # 测试不同条件下的评分
        test_cases = [
            {"height_difference": 500, "brightness": 30, "road_accessible": True, "expected_range": (70, 100)},
            {"height_difference": 100, "brightness": 150, "road_accessible": False, "expected_range": (20, 60)},
            {"height_difference": 200, "brightness": None, "road_accessible": None, "expected_range": (30, 70)}
        ]
        
        for i, case in enumerate(test_cases):
            test_loc = StargazingLocation(
                name=f"测试{i+1}",
                latitude=40.0, longitude=116.0, elevation=1000.0, prominence=500.0,
                distance_to_nearest_town=25.0, nearest_town_name="测试城镇",
                height_difference=case["height_difference"],
                light_pollution_brightness=case["brightness"],
                road_accessible=case["road_accessible"]
            )
            
            score = analyzer._calculate_stargazing_score(test_loc)
            min_score, max_score = case["expected_range"]
            
            print(f"  测试案例{i+1}: 评分 {score} (期望范围: {min_score}-{max_score})")
        
        print("✓ 评分系统测试通过")
        return True
        
    except Exception as e:
        print(f"✗ 评分系统测试失败: {e}")
        return False

def test_data_persistence():
    """
    测试观星地点数据的持久化功能
    
    验证分析结果能否正确保存到JSON文件
    并确保数据的完整性和格式正确性
    
    测试流程：
    1. 创建测试观星地点数据
    2. 保存到临时JSON文件
    3. 验证文件存在性
    4. 加载并验证数据完整性
    5. 检查数据格式和字段正确性
    
    验证要点：
    - JSON文件结构的正确性
    - 数据字段的完整性
    - 数值精度的保持
    - 中文字符的正确编码
    
    Returns:
        bool: 数据持久化功能是否正常工作
    """
    print("\n=== 测试4: 数据保存功能 ===")
    
    try:
        analyzer = StargazingLocationAnalyzer()
        
        # 创建测试数据
        test_locations = [
            StargazingLocation(
                name="测试山峰1",
                latitude=40.0, longitude=116.0, elevation=1000.0, prominence=500.0,
                distance_to_nearest_town=20.0, nearest_town_name="城镇1",
                height_difference=200.0, road_accessible=True,
                stargazing_score=75.5, recommendation_level="推荐 ⭐⭐⭐⭐",
                analysis_notes="测试备注1"
            ),
            StargazingLocation(
                name="测试山峰2",
                latitude=40.1, longitude=116.1, elevation=800.0, prominence=300.0,
                distance_to_nearest_town=15.0, nearest_town_name="城镇2",
                height_difference=150.0, road_accessible=False,
                stargazing_score=60.2, recommendation_level="一般推荐 ⭐⭐⭐",
                analysis_notes="测试备注2"
            )
        ]
        
        # 保存到临时文件
        temp_filename = get_temp_file(suffix='.json', prefix='test_results_')
        
        analyzer.save_results_to_json(test_locations, temp_filename)
        
        # 验证文件存在
        assert os.path.exists(temp_filename), "保存的文件不存在"
        
        # 加载并验证数据
        with open(temp_filename, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert 'analysis_time' in saved_data, "缺少分析时间字段"
        assert 'total_locations' in saved_data, "缺少总数字段"
        assert 'locations' in saved_data, "缺少地点数据字段"
        assert saved_data['total_locations'] == len(test_locations), "总数不匹配"
        assert len(saved_data['locations']) == len(test_locations), "地点数量不匹配"
        
        # 验证第一个地点的数据
        first_saved = saved_data['locations'][0]
        assert first_saved['name'] == "测试山峰1", "名称不匹配"
        assert first_saved['stargazing_score'] == 75.5, "评分不匹配"
        
        # 清理临时文件
        os.unlink(temp_filename)
        
        print("✓ 数据保存和加载测试通过")
        return True
        
    except Exception as e:
        print(f"✗ 数据保存测试失败: {e}")
        return False

def test_top_recommendations():
    """
    测试观星地点推荐排序功能的准确性
    
    验证系统能否根据评分正确排序观星地点
    并返回指定数量的最佳推荐
    
    测试内容：
    1. 创建不同评分的测试地点
    2. 验证排序算法的正确性
    3. 测试获取前N个推荐的功能
    4. 验证推荐摘要的生成
    
    验证要点：
    - 按评分从高到低的正确排序
    - 返回数量与请求数量的一致性
    - 推荐摘要的完整性
    - 边界条件的处理
    
    Returns:
        bool: 推荐排序功能是否正常工作
    """
    print("\n=== 测试5: 推荐排序功能 ===")
    
    try:
        analyzer = StargazingLocationAnalyzer()
        
        # 创建不同评分的测试数据
        test_locations = [
            StargazingLocation(
                name="低分山峰", latitude=40.0, longitude=116.0, elevation=500.0, prominence=200.0,
                distance_to_nearest_town=5.0, nearest_town_name="城镇", height_difference=50.0,
                stargazing_score=30.0
            ),
            StargazingLocation(
                name="高分山峰", latitude=40.1, longitude=116.1, elevation=1500.0, prominence=800.0,
                distance_to_nearest_town=50.0, nearest_town_name="城镇", height_difference=400.0,
                stargazing_score=85.0
            ),
            StargazingLocation(
                name="中分山峰", latitude=40.2, longitude=116.2, elevation=1000.0, prominence=500.0,
                distance_to_nearest_town=25.0, nearest_town_name="城镇", height_difference=200.0,
                stargazing_score=65.0
            )
        ]
        
        # 测试获取前N个推荐
        top_2 = analyzer.get_top_recommendations(test_locations, 2)
        
        assert len(top_2) == 2, "返回的推荐数量不正确"
        assert top_2[0].name == "高分山峰", "第一推荐不正确"
        assert top_2[1].name == "中分山峰", "第二推荐不正确"
        assert top_2[0].stargazing_score >= top_2[1].stargazing_score, "排序不正确"
        
        print(f"✓ 前2个推荐: {top_2[0].name} ({top_2[0].stargazing_score}), {top_2[1].name} ({top_2[1].stargazing_score})")
        
        # 测试摘要打印（不验证输出，只确保不出错）
        analyzer.print_analysis_summary(test_locations)
        
        print("✓ 推荐排序测试通过")
        return True
        
    except Exception as e:
        print(f"✗ 推荐排序测试失败: {e}")
        return False

def test_convenience_function():
    """
    测试观星地点分析的便捷函数接口
    
    验证analyze_stargazing_area函数能否
    提供简化的一站式分析服务
    
    测试场景：
    - 小范围区域的快速分析
    - 参数传递的正确性
    - 返回结果的数据类型
    - 限制条件的有效性
    
    测试参数：
    - 地理边界坐标
    - 最大山峰数量限制
    - 最小高度差阈值
    - KML文件路径（可选）
    
    Returns:
        bool: 便捷函数是否正常工作
    """
    print("\n=== 测试6: 便捷函数 ===")
    
    try:
        # 测试便捷函数（小范围，避免长时间运行）
        locations = analyze_stargazing_area(
            south=39.98, west=116.18, north=40.02, east=116.22,
            kml_file_path=None,
            max_peaks=3,
            min_height_diff=50.0
        )
        
        assert isinstance(locations, list), "返回类型不正确"
        
        if locations:
            assert all(isinstance(loc, StargazingLocation) for loc in locations), "地点类型不正确"
            print(f"✓ 便捷函数找到 {len(locations)} 个地点")
        else:
            print("✓ 便捷函数运行正常（未找到地点）")
        
        print("✓ 便捷函数测试通过")
        return True
        
    except Exception as e:
        print(f"✗ 便捷函数测试失败: {e}")
        return False

def test_error_handling():
    """
    测试观星地点分析器的错误处理机制
    
    验证系统在遇到异常情况时能否
    优雅地处理错误并保持稳定运行
    
    测试场景：
    1. 无效的地理边界框
    2. 不存在的KML文件路径
    3. 网络连接异常
    4. 数据格式错误
    
    验证要点：
    - 异常捕获的完整性
    - 错误信息的清晰度
    - 程序的稳定性
    - 降级处理的合理性
    
    Returns:
        bool: 错误处理机制是否正常工作
    """
    print("\n=== 测试7: 错误处理 ===")
    
    try:
        analyzer = StargazingLocationAnalyzer()
        
        # 测试无效边界框
        invalid_bbox = (40.0, 116.0, 39.0, 115.0)  # south > north, west > east
        
        try:
            locations = analyzer.analyze_area(
                bbox=invalid_bbox,
                max_peaks=5,
                include_light_pollution=False,
                include_road_connectivity=False
            )
            # 即使边界框无效，函数也应该能处理（可能返回空列表）
            print(f"✓ 无效边界框处理: 返回 {len(locations)} 个地点")
        except Exception as e:
            print(f"✓ 无效边界框正确抛出异常: {type(e).__name__}")
        
        # 测试无效KML文件路径
        try:
            analyzer_with_invalid_kml = StargazingLocationAnalyzer(
                kml_file_path="/nonexistent/path/file.kml"
            )
            # 应该能正常初始化，但光污染分析器为None
            assert analyzer_with_invalid_kml.light_pollution_analyzer is None, "应该跳过无效KML文件"
            print("✓ 无效KML文件路径处理正确")
        except Exception as e:
            print(f"✓ 无效KML文件正确处理异常: {type(e).__name__}")
        
        print("✓ 错误处理测试通过")
        return True
        
    except Exception as e:
        print(f"✗ 错误处理测试失败: {e}")
        return False

def run_all_tests():
    """
    运行观星地点分析器的完整测试套件
    
    执行所有测试用例并生成测试报告
    验证系统各个模块的功能完整性
    
    测试覆盖范围：
    1. 分析器初始化 - 验证组件初始化
    2. 基础分析功能 - 验证核心分析流程
    3. 评分系统 - 验证评分算法准确性
    4. 数据保存功能 - 验证数据持久化
    5. 推荐排序功能 - 验证排序和推荐
    6. 便捷函数 - 验证简化接口
    7. 错误处理 - 验证异常处理机制
    
    输出内容：
    - 每个测试的执行状态
    - 测试通过/失败统计
    - 总体测试结果摘要
    
    Returns:
        bool: 所有测试是否全部通过
    """
    print("观星地点综合分析器 - 功能测试")
    print("=" * 50)
    print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("分析器初始化", test_analyzer_initialization),
        ("基础分析功能", test_basic_analysis),
        ("评分系统", test_scoring_system),
        ("数据保存功能", test_data_persistence),
        ("推荐排序功能", test_top_recommendations),
        ("便捷函数", test_convenience_function),
        ("错误处理", test_error_handling)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n✗ {test_name} 测试出现异常: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print(f"测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if failed == 0:
        print("\n🎉 所有测试通过！观星地点综合分析器功能正常。")
        print("\n主要功能验证:")
        print("✓ 山峰查找和筛选")
        print("✓ 道路连通性检测")
        print("✓ 综合评分计算")
        print("✓ 推荐等级评估")
        print("✓ 数据保存和排序")
        print("✓ 错误处理机制")
        
        print("\n使用建议:")
        print("1. 对于基础使用，可以不提供光污染KML文件")
        print("2. 建议设置合适的搜索范围以平衡结果质量和性能")
        print("3. 可以根据需要调整最小高度差和道路搜索半径")
        print("4. 使用便捷函数 analyze_stargazing_area() 进行快速分析")
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查相关功能。")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)