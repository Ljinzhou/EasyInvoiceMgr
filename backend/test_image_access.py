"""
图片访问功能验证脚本
用于诊断发票图片加载问题
"""

import requests
import os

def test_image_access():
    """测试图片访问功能"""
    
    print("=" * 60)
    print("🔍 发票图片加载问题诊断工具")
    print("=" * 60)
    
    # 测试1：检查后端服务是否运行
    print("\n📡 测试1: 检查后端服务...")
    try:
        response = requests.get('http://localhost:5000/api/health', timeout=5)
        print(f"   ✅ 后端服务正常运行 (状态码: {response.status_code})")
    except Exception as e:
        print(f"   ❌ 后端服务无法连接: {e}")
        print("   💡 请先启动后端: cd backend && python app.py")
        return False
    
    # 测试2：检查CORS配置
    print("\n🌐 测试2: 检查CORS配置...")
    try:
        response = requests.options(
            'http://localhost:5000/uploads/test.png',
            headers={
                'Origin': 'http://localhost:3000',
                'Access-Control-Request-Method': 'GET'
            },
            timeout=5
        )
        
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
        }
        
        if cors_headers['Access-Control-Allow-Origin']:
            print(f"   ✅ CORS已正确配置")
            print(f"      允许的来源: {cors_headers['Access-Control-Allow-Origin']}")
            print(f"      允许的方法: {cors_headers['Access-Control-Allow-Methods']}")
        else:
            print(f"   ⚠️ CORS响应头未找到")
            print(f"   响应头: {dict(response.headers)}")
            
    except Exception as e:
        print(f"   ❌ CORS测试失败: {e}")
    
    # 测试3：检查uploads目录和文件
    print("\n📁 测试3: 检查上传文件目录...")
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    
    if os.path.exists(uploads_dir):
        files = os.listdir(uploads_dir)
        print(f"   ✅ uploads目录存在: {uploads_dir}")
        print(f"   📊 文件数量: {len(files)}")
        
        if files:
            print(f"\n   📄 最近上传的文件:")
            for i, file in enumerate(files[:5], 1):  # 只显示前5个
                file_path = os.path.join(uploads_dir, file)
                size = os.path.getsize(file_path)
                print(f"      {i}. {file} ({size} bytes)")
                
                # 测试4：尝试访问该文件
                print(f"\n🔗 测试4: 尝试访问文件 /uploads/{file}...")
                try:
                    response = requests.get(
                        f'http://localhost:5000/uploads/{file}',
                        timeout=10,
                        headers={'Origin': 'http://localhost:3000'}
                    )
                    
                    if response.status_code == 200:
                        content_type = response.headers.get('Content-Type', '未知')
                        print(f"   ✅ 文件访问成功!")
                        print(f"      状态码: {response.status_code}")
                        print(f"      Content-Type: {content_type}")
                        print(f"      文件大小: {len(response.content)} bytes")
                        print(f"\n   🎉 完整URL (前端应使用): http://localhost:5000/uploads/{file}")
                        
                    elif response.status_code == 404:
                        print(f"   ❌ 文件不存在 (404)")
                    else:
                        print(f"   ❌ 访问失败 (状态码: {response.status_code})")
                        print(f"   响应内容: {response.text[:200]}")
                        
                except Exception as e:
                    print(f"   ❌ 请求失败: {e}")
                    
        else:
            print("   ⚠️ 目录为空 - 尚无上传文件")
            print("   💡 请通过前端界面上传一个测试文件")
            
    else:
        print(f"   ❌ uploads目录不存在: {uploads_dir}")
        print("   💡 请重启后端服务，系统会自动创建该目录")
    
    # 测试总结
    print("\n" + "=" * 60)
    print("📋 诊断完成")
    print("=" * 60)
    print("\n如果仍然无法显示图片，请检查:")
    print("1. 后端控制台日志中的错误信息")
    print("2. 浏览器开发者工具 → Network 标签页")
    print("3. 确认浏览器地址为 http://localhost:3000 (不是 https)")
    print("\n常见问题:")
    print("- 如果看到CORS错误 → 后端CORS配置问题 (已修复✅)")
    print("- 如果看到404错误 → 文件未保存或路径错误")
    print("- 如果请求被阻止 → 防火墙或网络问题")
    
    return True


if __name__ == '__main__':
    test_image_access()
