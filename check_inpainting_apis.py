"""
检查可用的图像编辑/Inpainting API
"""
import requests
import os
from pathlib import Path

# 读取API Key
env_file = Path('.env').read_text(encoding='utf-8')
openrouter_key = None
for line in env_file.split('\n'):
    if line.startswith('OPENROUTER_API_KEY='):
        openrouter_key = line.split('=', 1)[1].strip()
        break

print("=" * 80)
print("🔍 图像编辑/Inpainting API 可用性调研")
print("=" * 80)

# 1. 检查 OpenRouter
print("\n【1】OpenRouter 模型检查")
print("-" * 80)
if openrouter_key:
    try:
        response = requests.get(
            'https://openrouter.ai/api/v1/models',
            headers={'Authorization': f'Bearer {openrouter_key}'},
            timeout=10
        )
        if response.status_code == 200:
            models = response.json()['data']
            
            # 搜索 inpainting/edit 相关模型
            inpaint_models = [
                m for m in models 
                if any(keyword in m['id'].lower() for keyword in ['inpaint', 'edit', 'img2img', 'image-to-image'])
            ]
            
            if inpaint_models:
                print(f"✅ 找到 {len(inpaint_models)} 个图像编辑相关模型：")
                for m in inpaint_models[:10]:
                    print(f"  - {m['id']}")
                    if 'description' in m:
                        print(f"    {m['description'][:100]}")
            else:
                print("❌ OpenRouter 不支持 Inpainting/Edit 模型")
                print("   (搜索关键词: inpaint, edit, img2img, image-to-image)")
        else:
            print(f"❌ API 请求失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 检查失败: {e}")
else:
    print("⚠️  未找到 OPENROUTER_API_KEY")

# 2. OpenAI 官方 API 能力说明
print("\n【2】OpenAI 官方 API (推荐)")
print("-" * 80)
print("✅ 支持 DALL-E 2 Edit (图像编辑/Inpainting)")
print("   API: https://api.openai.com/v1/images/edits")
print("   功能:")
print("     - 上传原图 (image: PNG, <4MB)")
print("     - 上传Mask (mask: PNG, 黑色=保留, 透明=编辑)")
print("     - 文本提示词 (prompt: 描述编辑内容)")
print("     - 返回编辑后的图像")
print("\n   优势:")
print("     ✅ 效果最好 (官方优化)")
print("     ✅ 精确区域编辑")
print("     ✅ 自动保持原图风格")
print("\n   劣势:")
print("     ⚠️  需要单独的 OPENAI_API_KEY (不能用 OpenRouter)")
print("     ⚠️  仅支持 DALL-E 2 (不支持 DALL-E 3)")

# 3. Stability AI (Stable Diffusion)
print("\n【3】Stability AI (Stable Diffusion Inpainting)")
print("-" * 80)
print("✅ 支持 SD Inpainting 模型")
print("   API: https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/image-to-image/masking")
print("   功能:")
print("     - 类似 DALL-E Edit")
print("     - 多个模型版本可选")
print("\n   优势:")
print("     ✅ 开源生态")
print("     ✅ 可自建 (ComfyUI/Automatic1111)")
print("\n   劣势:")
print("     ⚠️  需要 Stability AI API Key")
print("     ⚠️  自建需要 GPU 服务器")

# 4. 推荐方案
print("\n【4】推荐技术方案")
print("-" * 80)
print("🎯 方案：OpenAI 官方 API (DALL-E 2 Edit)")
print("\n   实施步骤:")
print("     1. 用户在 .env 中添加 OPENAI_API_KEY")
print("     2. 系统检测：有OPENAI_API_KEY → 启用编辑模式")
print("     3. 前端提供 Canvas 绘制 Mask")
print("     4. 后端调用 openai.Image.create_edit()")
print("\n   降级策略:")
print("     - 无 OPENAI_API_KEY → 隐藏编辑模式，仅保留生成模式")
print("     - API 失败 → 回退到 Vision + 生成 (方案C)")

print("\n" + "=" * 80)
print("✅ 调研完成")
print("=" * 80)
