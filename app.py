"""
JD Gap Analyzer - 简历与JD深度差距分析工具
基于 SpeedyJob 改进方案 MVP
作者：liuzh | vibe coding with AI
"""

import streamlit as st
import json
import re
from openai import OpenAI

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(
    page_title="JD Gap Analyzer · 简历差距诊断",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 样式 ─────────────────────────────────────────────────
st.markdown("""
<style>
  .main { background: #f7f8fc; }
  .stTextArea textarea {
    font-size: 14px !important;
    min-height: 220px !important;
  }
  .card {
    background: white;
    border-radius: 12px;
    padding: 20px 24px;
    margin: 10px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
  }
  .hit   { border-left: 4px solid #22c55e; }
  .gap   { border-left: 4px solid #ef4444; }
  .weak  { border-left: 4px solid #f59e0b; }
  .tag-hit  { background:#dcfce7; color:#16a34a; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
  .tag-gap  { background:#fee2e2; color:#dc2626; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
  .tag-weak { background:#fef9c3; color:#b45309; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
  .score-circle {
    font-size: 56px;
    font-weight: 800;
    text-align: center;
    padding: 20px 0 8px;
  }
  .rewrite-box {
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    border-radius: 8px;
    padding: 12px 16px;
    margin-top: 8px;
    font-size: 13px;
    color: #0c4a6e;
  }
  h1 { font-size: 26px !important; }
</style>
""", unsafe_allow_html=True)

# ── 标题 ─────────────────────────────────────────────────
st.markdown("## 🔍 JD Gap Analyzer")
st.markdown("**逐条拆解 JD 要求 · 精准定位简历短板 · 给出可直接使用的改写建议**")
st.divider()

# ── 侧边栏：API Key ───────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 配置")
    api_key = st.text_input("DeepSeek API Key", type="password",
                             help="从 platform.deepseek.com 获取，本地运行不会上传")
    model_choice = st.selectbox("模型", ["deepseek-chat", "deepseek-reasoner"])
    st.caption("💡 API Key 仅在本次会话中使用，不会被存储")

# ── 主输入区 ──────────────────────────────────────────────
col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("### 📄 粘贴你的简历")
    resume_text = st.text_area(
        label="简历内容（纯文本即可）",
        height=320,
        placeholder="将简历内容粘贴到这里...\n\n示例：\n工作经验\n- 2023-2025 某公司 后端工程师\n  负责用户服务模块开发，使用 Python/FastAPI...\n\n技能\nPython, React, MySQL, Docker...",
        label_visibility="collapsed"
    )

with col2:
    st.markdown("### 📋 粘贴目标 JD")
    jd_text = st.text_area(
        label="职位描述（JD）",
        height=320,
        placeholder="将 JD 粘贴到这里...\n\n示例：\n任职要求\n1. 熟悉 React/Vue 前端框架\n2. 有 Node.js 后端开发经验\n3. 了解 Docker 容器化部署\n4. 有 AI 应用开发经验者优先",
        label_visibility="collapsed"
    )

# ── 示例数据 ──────────────────────────────────────────────
with st.expander("📖 点击加载示例数据（快速体验）"):
    if st.button("加载示例", use_container_width=True):
        st.session_state["demo_resume"] = """工作经验
2023.06 - 至今 | 某科技公司 | Python后端工程师
• 负责用户中心、订单系统的 API 开发，使用 FastAPI + PostgreSQL
• 设计并实现了基于 Redis 的缓存层，接口响应时间降低 40%
• 参与微服务拆分，将单体应用拆解为 5 个独立服务
• 编写单元测试，覆盖率达到 85%

2022.07 - 2023.05 | 某创业公司 | 全栈实习生  
• 使用 Vue3 开发后台管理系统前端
• 协助搭建 CI/CD 流水线（GitHub Actions + Docker）

技能
编程语言：Python（熟练）、JavaScript（熟悉）
框架：FastAPI, Vue3, React（了解）
数据库：PostgreSQL, MySQL, Redis
工具：Docker, Git, Linux
英语：CET-6（阅读无障碍）"""

        st.session_state["demo_jd"] = """岗位要求（AI应用开发工程师）
1. 熟悉 Python，有扎实的工程开发能力
2. 熟练使用 LangChain 或类似 LLM 框架进行 AI 应用开发
3. 有 RAG（检索增强生成）系统的设计与实现经验
4. 了解主流大语言模型 API（OpenAI、DeepSeek等）的调用方式
5. 有前后端全栈开发能力，能独立完成产品原型
6. 具备良好的英文文档阅读能力
7. 有 AI 项目上线经验者优先"""

        st.rerun()

# 加载示例数据
if "demo_resume" in st.session_state:
    resume_text = st.session_state.pop("demo_resume")
if "demo_jd" in st.session_state:
    jd_text = st.session_state.pop("demo_jd")

st.divider()

# ── 分析按钮 ──────────────────────────────────────────────
analyze_btn = st.button(
    "🚀 开始深度分析", 
    type="primary", 
    use_container_width=True,
    disabled=not (resume_text and jd_text and api_key)
)

if not api_key:
    st.info("👈 请在左侧侧边栏输入 DeepSeek API Key 后开始分析")

# ── AI 分析核心逻辑 ────────────────────────────────────────
SYSTEM_PROMPT = """你是一位资深的职业顾问和简历优化专家。
你的任务是对求职者的简历和目标职位JD进行深度对比分析。

分析维度：
1. 逐条拆解JD中每一项要求
2. 判断简历是否有效覆盖该要求（三个等级：hit/weak/gap）
   - hit：简历中有明确的相关内容，覆盖良好
   - weak：简历中有相关内容但不够突出或描述不够有力
   - gap：简历中完全缺失该要求相关内容
3. 对每条要求给出针对性的改写建议（如果是weak或gap，给出可直接添加到简历的具体文字建议）

输出要求：严格按照JSON格式输出，不要有任何额外文字。

JSON格式如下：
{
  "overall_score": 75,
  "summary": "总体评价（2-3句话）",
  "hit_count": 3,
  "weak_count": 2,
  "gap_count": 2,
  "items": [
    {
      "jd_requirement": "JD原文要求",
      "status": "hit|weak|gap",
      "resume_evidence": "简历中的对应内容摘要（如有）",
      "suggestion": "改写建议或加分动作（hit时可为空字符串）"
    }
  ],
  "quick_wins": ["最优先要补充的3个行动建议"],
  "strengths": ["简历相对该JD的3个优势亮点"]
}"""

def run_analysis(resume: str, jd: str, api_key: str, model: str) -> dict:
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    user_msg = f"""请分析以下简历与JD的匹配情况：

===== 简历内容 =====
{resume}

===== 目标JD =====
{jd}

请严格按JSON格式输出分析结果。"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.3,
        max_tokens=3000,
    )
    
    raw = response.choices[0].message.content.strip()
    # 提取 JSON（防止模型输出多余文字）
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())
    return json.loads(raw)


def score_color(score: int) -> str:
    if score >= 80: return "#22c55e"
    if score >= 60: return "#f59e0b"
    return "#ef4444"


def status_tag(status: str) -> str:
    if status == "hit":
        return '<span class="tag-hit">✅ 覆盖</span>'
    elif status == "weak":
        return '<span class="tag-weak">⚠️ 较弱</span>'
    else:
        return '<span class="tag-gap">❌ 缺失</span>'


# ── 执行分析 & 渲染结果 ────────────────────────────────────
if analyze_btn:
    with st.spinner("🤖 AI 正在逐条分析 JD 要求，请稍候..."):
        try:
            result = run_analysis(resume_text, jd_text, api_key, model_choice)
        except Exception as e:
            st.error(f"分析失败：{e}")
            st.stop()

    st.success("✅ 分析完成！")
    st.divider()

    # ── 顶部总览 ──────────────────────────────────────────
    st.markdown("## 📊 总览")
    
    c1, c2, c3, c4 = st.columns(4)
    score = result.get("overall_score", 0)
    color = score_color(score)
    
    with c1:
        st.markdown(f"""
        <div class="card" style="text-align:center">
          <div style="font-size:13px;color:#888;margin-bottom:4px">综合匹配度</div>
          <div class="score-circle" style="color:{color}">{score}</div>
          <div style="font-size:12px;color:#888">/ 100</div>
        </div>""", unsafe_allow_html=True)
    
    with c2:
        st.markdown(f"""
        <div class="card" style="text-align:center">
          <div style="font-size:13px;color:#888;margin-bottom:4px">已覆盖</div>
          <div style="font-size:48px;font-weight:800;color:#22c55e;padding:20px 0 8px">
            {result.get('hit_count', 0)}
          </div>
          <div style="font-size:12px;color:#888">条 JD 要求</div>
        </div>""", unsafe_allow_html=True)
    
    with c3:
        st.markdown(f"""
        <div class="card" style="text-align:center">
          <div style="font-size:13px;color:#888;margin-bottom:4px">覆盖较弱</div>
          <div style="font-size:48px;font-weight:800;color:#f59e0b;padding:20px 0 8px">
            {result.get('weak_count', 0)}
          </div>
          <div style="font-size:12px;color:#888">条 JD 要求</div>
        </div>""", unsafe_allow_html=True)
    
    with c4:
        st.markdown(f"""
        <div class="card" style="text-align:center">
          <div style="font-size:13px;color:#888;margin-bottom:4px">完全缺失</div>
          <div style="font-size:48px;font-weight:800;color:#ef4444;padding:20px 0 8px">
            {result.get('gap_count', 0)}
          </div>
          <div style="font-size:12px;color:#888">条 JD 要求</div>
        </div>""", unsafe_allow_html=True)

    # 总结
    st.markdown(f"""
    <div class="card">
      <strong>📝 AI 总评</strong><br><br>
      {result.get('summary', '')}
    </div>""", unsafe_allow_html=True)

    st.divider()

    # ── 逐条分析 ──────────────────────────────────────────
    st.markdown("## 🔬 逐条 JD 要求分析")

    items = result.get("items", [])
    for i, item in enumerate(items, 1):
        status = item.get("status", "gap")
        card_class = {"hit": "hit", "weak": "weak", "gap": "gap"}.get(status, "gap")
        
        evidence_html = ""
        if item.get("resume_evidence"):
            evidence_html = f"""
            <div style="font-size:13px;color:#555;margin-top:8px">
              📌 <strong>简历依据：</strong>{item['resume_evidence']}
            </div>"""
        
        suggestion_html = ""
        if item.get("suggestion") and status != "hit":
            suggestion_html = f"""
            <div class="rewrite-box">
              💡 <strong>改写建议：</strong><br>{item['suggestion']}
            </div>"""
        
        st.markdown(f"""
        <div class="card {card_class}">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:4px">
            <span style="color:#888;font-size:13px">#{i}</span>
            {status_tag(status)}
            <span style="font-weight:600;font-size:15px">{item.get('jd_requirement', '')}</span>
          </div>
          {evidence_html}
          {suggestion_html}
        </div>""", unsafe_allow_html=True)

    st.divider()

    # ── 亮点 & 行动清单 ───────────────────────────────────
    col_a, col_b = st.columns(2, gap="large")

    with col_a:
        st.markdown("### 💪 你的优势亮点")
        strengths = result.get("strengths", [])
        for s in strengths:
            st.markdown(f"""
            <div class="card hit" style="padding:12px 16px;margin:6px 0">
              ✅ {s}
            </div>""", unsafe_allow_html=True)

    with col_b:
        st.markdown("### ⚡ 优先行动清单")
        quick_wins = result.get("quick_wins", [])
        for j, qw in enumerate(quick_wins, 1):
            st.markdown(f"""
            <div class="card gap" style="padding:12px 16px;margin:6px 0">
              <strong>#{j}</strong> {qw}
            </div>""", unsafe_allow_html=True)

    st.divider()
    st.caption("🤖 由 DeepSeek AI 驱动 · JD Gap Analyzer MVP · 基于 SpeedyJob 改进方案")
