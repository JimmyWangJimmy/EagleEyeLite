#!/bin/bash
# 快速设置脚本 - 新用户首次使用

echo "========================================="
echo "EagleEye Lite - 快速设置"
echo "========================================="

# 第一步：克隆仓库
echo ""
echo "📁 第一步：克隆仓库..."
git clone https://github.com/JimmyWangJimmy/EagleEyeLite.git
cd EagleEyeLite

# 第二步：创建虚拟环境
echo ""
echo "🐍 第二步：创建虚拟环境..."
python -m venv venv

# 第三步：激活虚拟环境
echo ""
echo "✨ 第三步：激活虚拟环境..."
# Windows
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    # Mac/Linux
    source venv/bin/activate
fi

# 第四步：安装依赖
echo ""
echo "📦 第四步：安装依赖..."
pip install -r requirements.txt

# 第五步：设置API Key
echo ""
echo "🔑 第五步：设置Anthropic API Key..."
echo "   获取地址: https://console.anthropic.com/"
read -p "   请输入你的API Key (sk-ant-...): " API_KEY
export ANTHROPIC_API_KEY="$API_KEY"

# 第六步：构建向量索引
echo ""
echo "🔍 第六步：构建向量索引（这会下载模型，约200MB）..."
python scripts/index_rules.py

# 第七步：测试系统
echo ""
echo "🧪 第七步：测试检索系统..."
python scripts/test_retrieval.py

# 第八步：运行演示
echo ""
echo "🚀 第八步：运行审计演示..."
python scripts/run_audit.py

echo ""
echo "========================================="
echo "✅ 设置完成！"
echo "========================================="
echo ""
echo "下一步："
echo "1. 审计真实PDF文件:"
echo "   python scripts/run_audit.py /path/to/file.pdf"
echo ""
echo "2. 查看文档:"
echo "   - README.md (中文)"
echo "   - README_EN.md (English)"
echo "   - docs/rag_guide.md (RAG详解)"
echo ""
echo "3. 联系我们:"
echo "   GitHub Issues: https://github.com/JimmyWangJimmy/EagleEyeLite/issues"
echo ""
