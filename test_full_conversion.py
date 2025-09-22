import sys
sys.path.append('src')
from main import ShpToOpenDriveConverter
import logging
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_full_conversion():
    """测试完整的转换流程"""
    print("=== 测试完整的Shapefile到OpenDrive转换流程 ===")
    
    try:
        # 1. 设置输入和输出路径
        input_shp = 'E:/Code/ShpToOpenDrive/data/test_lane/TestLane.shp'
        output_xodr = 'E:/Code/ShpToOpenDrive/output/full_test_output.xodr'
        config_file = 'E:/Code/ShpToOpenDrive/config/lane_format.json'
        
        print(f"\n1. 输入文件: {input_shp}")
        print(f"   输出文件: {output_xodr}")
        print(f"   配置文件: {config_file}")
        
        # 检查输入文件是否存在
        if not os.path.exists(input_shp):
            print(f"✗ 输入文件不存在: {input_shp}")
            return False
        
        # 创建输出目录
        output_dir = os.path.dirname(output_xodr)
        os.makedirs(output_dir, exist_ok=True)
        
        # 2. 加载配置文件
        print("\n2. 加载配置文件...")
        config = None
        if os.path.exists(config_file):
            try:
                import json
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print("✓ 配置文件加载成功")
            except Exception as e:
                print(f"⚠ 配置文件加载失败: {e}，使用默认配置")
                config = None
        else:
            print("⚠ 配置文件不存在，使用默认配置")
        
        # 3. 创建转换器实例
        print("\n3. 创建转换器实例...")
        converter = ShpToOpenDriveConverter(config)
        
        # 4. 执行完整转换
        print("\n4. 执行完整转换...")
        success = converter.convert(
            input_shp,
            output_xodr
        )
        
        if success:
            print("✓ 转换成功完成！")
            
            # 5. 检查输出文件
            print("\n5. 检查输出文件...")
            if os.path.exists(output_xodr):
                file_size = os.path.getsize(output_xodr)
                print(f"✓ 输出文件已生成: {output_xodr}")
                print(f"  文件大小: {file_size} 字节")
                
                # 读取文件前几行查看内容
                try:
                    with open(output_xodr, 'r', encoding='utf-8') as f:
                        first_lines = [f.readline().strip() for _ in range(5)]
                    print("  文件内容预览:")
                    for i, line in enumerate(first_lines, 1):
                        if line:
                            print(f"    {i}: {line[:80]}{'...' if len(line) > 80 else ''}")
                except Exception as e:
                    print(f"  ⚠ 无法读取文件内容: {e}")
            else:
                print("✗ 输出文件未生成")
                return False
            
            # 6. 获取转换统计信息
            print("\n6. 转换统计信息:")
            try:
                stats = converter.get_conversion_stats()
                for key, value in stats.items():
                    print(f"  {key}: {value}")
            except AttributeError:
                print("  转换器不支持统计信息功能")
            
            return True
        else:
            print("✗ 转换失败")
            return False
        
    except Exception as e:
        print(f"\n✗ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_different_configs():
    """测试不同配置下的转换"""
    print("\n=== 测试不同配置下的转换 ===")
    
    configs = [
        ('默认配置', None),
        ('Lane格式配置', 'E:/Code/ShpToOpenDrive/config/lane_format.json')
    ]
    
    for config_name, config_path in configs:
        print(f"\n--- 测试 {config_name} ---")
        
        try:
            # 加载配置
            config = None
            if config_path and os.path.exists(config_path):
                try:
                    import json
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    print(f"✓ 已加载配置: {config_path}")
                except Exception as e:
                    print(f"⚠ 配置加载失败: {e}")
                    config = None
            else:
                print("✓ 使用默认配置")
            
            converter = ShpToOpenDriveConverter(config)
            
            # 执行转换
            input_shp = 'E:/Code/ShpToOpenDrive/data/test_lane/TestLane.shp'
            output_xodr = f'E:/Code/ShpToOpenDrive/output/test_{config_name.replace(" ", "_")}.xodr'
            
            success = converter.convert(input_shp, output_xodr)
            
            if success:
                print(f"✓ {config_name} 转换成功")
                if os.path.exists(output_xodr):
                    file_size = os.path.getsize(output_xodr)
                    print(f"  输出文件大小: {file_size} 字节")
            else:
                print(f"✗ {config_name} 转换失败")
                
        except Exception as e:
            print(f"✗ {config_name} 测试出错: {e}")

if __name__ == "__main__":
    # 测试完整转换流程
    success = test_full_conversion()
    
    if success:
        print("\n🎉 完整转换流程测试成功！")
        
        # 测试不同配置
        test_with_different_configs()
    else:
        print("\n❌ 完整转换流程测试失败！")