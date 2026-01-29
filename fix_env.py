# 创建干净的.env文件
with open(".env.example", "r", encoding="utf-8") as f:
    content = f.read()

with open(".env", "w", encoding="utf-8") as f:
    f.write(content)
    f.write("\n# v7.214引擎控制\n")
    f.write("ENABLE_STRUCTURED_ANALYSIS_V7214=false\n")

print("干净的.env文件已创建，包含v7.214引擎禁用配置")
