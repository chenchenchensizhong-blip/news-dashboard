import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from openai import OpenAI
import os

# --- 页面配置 ---
st.set_page_config(page_title="全网热点监控 V3.6 (Llama 3.3)", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    .ai-report {
        background-color: #f0f2f6; 
        padding: 20px; 
        border-radius: 10px; 
        border-left: 5px solid #00b894;
        font-family: 'Microsoft YaHei', sans-serif;
    }
    div[data-testid="stVerticalBlock"] > div {gap: 0.5rem;}
    p {margin-bottom: 0.2rem;}
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 全网热点监控中心 (V3.6 最新模型版)")
st.caption("已升级至 Llama 3.3 70B | 极速响应 | 兼容 DeepSeek/Kimi")

# --- 0. 控制台 & 设置 ---
with st.sidebar:
    st.header("⚙️ 控制台")
    if st.button("🔄 刷新全网数据", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    st.header("🤖 AI 配置 (Groq)")
    
    # 默认地址
    api_base = st.text_input("API Base URL", value="https://api.groq.com/openai/v1")
    
    api_key = st.text_input("API Key", type="password", help="在此填入 Groq 的 gsk_... Key")
    
    # === 关键修改：更新为 Llama 3.3 最新模型 ===
    # 旧的 llama3-70b-8192 已下架
    # 新的推荐模型是: llama-3.3-70b-versatile
    model_name = st.text_input("模型名称", value="llama-3.3-70b-versatile")
    
    st.markdown("---")
    st.header("🌐 网络设置")
    proxy_port = st.text_input("本地代理端口 (VPN)", value="7897")
    
    if proxy_port:
        proxy_url = f"http://127.0.0.1:{proxy_port}"
        PROXIES = {"http": proxy_url, "https": proxy_url}
        st.success(f"爬虫代理: {proxy_port}")
        
        # 强制注入 AI 代理
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url
        st.success(f"AI 代理: {proxy_port} (环境注入)")
    else:
        PROXIES = None
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)
        st.warning("无代理")

def get_html(url, use_proxy=False):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
    }
    try:
        p = PROXIES if use_proxy else None
        response = requests.get(url, headers=headers, proxies=p, timeout=10)
        response.encoding = 'utf-8'
        return response.text if response.status_code == 200 else None
    except: return None

# --- 1. 爬虫模块 ---

@st.cache_data(ttl=3600)
def scrape_baidu():
    url = "https://top.baidu.com/board?tab=realtime"
    html = get_html(url)
    if not html: return pd.DataFrame()
    soup = BeautifulSoup(html, 'lxml')
    data = []
    items = soup.find_all('div', class_='category-wrap_iQLoo')
    for idx, item in enumerate(items[:10]):
        try:
            title = item.find('div', class_='c-single-text-ellipsis').text.strip()
            link = item.find('a')['href']
            heat = item.find('div', class_='hot-index_1Bl1a').text.strip()
            data.append({"排名": idx+1, "标题": title, "链接": link, "热度": heat})
        except: continue
    return pd.DataFrame(data)

@st.cache_data(ttl=3600)
def scrape_weibo():
    api_url = "https://weibo.com/ajax/side/hotSearch"
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://weibo.com/"}
        resp = requests.get(api_url, headers=headers, timeout=5)
        data = resp.json()
        realtime_list = data['data']['realtime']
        result = []
        for idx, item in enumerate(realtime_list[:10]):
            if 'rank' not in item and 'is_ad' in item: continue
            title = item['word']
            link = f"https://s.weibo.com/weibo?q={title}"
            heat = item.get('num', '置顶')
            tag = item.get('label_name', '')
            desc = f"【{tag}】" if tag else ""
            result.append({"排名": idx+1, "标题": title, "链接": link, "热度": str(heat), "简介": desc})
        return pd.DataFrame(result)
    except: return pd.DataFrame()

@st.cache_data(ttl=3600)
def scrape_bilibili():
    api_url = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/v/popular/rank/all"
    }
    try:
        resp = requests.get(api_url, headers=headers, timeout=5)
        json_data = resp.json()
        video_list = json_data['data']['list']
        data = []
        for idx, video in enumerate(video_list[:10]):
            title = video['title']
            author = video['owner']['name']
            play = video['stat']['view']
            play_str = f"{play/10000:.1f}万" if play > 10000 else str(play)
            link = video['short_link_v2']
            data.append({"排名": idx+1, "标题": title, "链接": link, "UP主": author, "播放": play_str})
        return pd.DataFrame(data)
    except: return pd.DataFrame()

@st.cache_data(ttl=3600)
def scrape_overseas(platform):
    url = "https://kworb.net/youtube/trending_overall.html" if platform == "youtube" else "https://getdaytrends.com/"
    html = get_html(url, use_proxy=True)
    if not html: return pd.DataFrame()
    soup = BeautifulSoup(html, 'lxml')
    data = []
    
    if platform == "youtube":
        try:
            rows = soup.find('tbody').find_all('tr')
            for idx, row in enumerate(rows[:10]):
                link_tag = row.find('a')
                if link_tag:
                    title = link_tag.text.strip()
                    raw_href = link_tag['href']
                    link = f"https://www.youtube.com/watch?v={raw_href.split('video/')[1].replace('.html','')}" if "video/" in raw_href else "https://www.youtube.com"+raw_href
                    data.append({"排名": idx+1, "标题": title, "链接": link})
        except: pass
    elif platform == "x":
        try:
            rows = soup.select('table.table tbody tr')
            for idx, row in enumerate(rows[:10]):
                link_tag = row.find('a')
                if link_tag:
                    title = link_tag.text.strip()
                    link = "https://twitter.com/search?q=" + title.replace("#", "%23")
                    heat = row.find('small').text.strip() if row.find('small') else ""
                    data.append({"排名": idx+1, "标题": title, "链接": link, "热度": heat})
        except: pass
    return pd.DataFrame(data)

# --- 2. AI 分析模块 ---

def generate_ai_report(dfs_dict, api_key, api_base, model_name):
    if not api_key:
        st.info("👈 请在左侧输入 API Key 开启 AI 分析")
        return

    prompt_text = "你是一位专业的全网舆情分析师。以下是当前各大平台的热搜前10名数据：\n\n"
    for platform, df in dfs_dict.items():
        if not df.empty:
            titles = df['标题'].tolist()
            prompt_text += f"【{platform}】：{', '.join(titles)}\n"
    
    prompt_text += """
    \n请根据以上数据，用中文生成一份简报（Markdown格式）：
    1. **全网核心焦点**：用一句话总结当前不论国内还是国外，大家最关注的一件事。
    2. **情绪晴雨表**：当前网民整体情绪是焦虑、娱乐、愤怒还是平静？
    3. **差异化洞察**：国内平台与海外平台关注点的最大区别是什么？
    4. **爆款预测**：预测哪一个话题最有可能在接下来几小时内持续发酵？
    """

    try:
        client = OpenAI(api_key=api_key, base_url=api_base)
        
        with st.spinner(f"🚀 正在呼叫 {model_name} 进行光速分析..."):
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "你是一个乐于助人的数据分析助手。"},
                    {"role": "user", "content": prompt_text}
                ],
                temperature=0.7,
            )
            ai_content = completion.choices[0].message.content
            
            st.markdown('<div class="ai-report">', unsafe_allow_html=True)
            st.markdown("### 🚀 AI 全网舆情深度简报")
            st.markdown(ai_content)
            st.markdown('</div>', unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"❌ AI 分析失败: {e}")
        st.warning("提示：如果遇到 'model decommissioned' 错误，请在侧边栏手动将模型名称改为 'llama-3.3-70b-versatile'")

# --- 3. UI 渲染 ---

def render_column(title, emoji, df):
    with st.container():
        st.markdown(f"### {emoji} {title}")
        st.markdown("---")
        if df.empty:
            st.warning("暂无数据")
        else:
            for _, row in df.iterrows():
                st.markdown(f"**{row['排名']}. [{row['标题']}]({row['链接']})**")
                meta = []
                if '热度' in row and row['热度']: meta.append(f"🔥 {row['热度']}")
                if 'UP主' in row: meta.append(f"👤 {row['UP主']}")
                if '简介' in row and row['简介']: meta.append(f"{row['简介']}")
                st.caption(" · ".join(meta))
                st.markdown("---")

# --- 主程序 ---
df_baidu = scrape_baidu()
df_weibo = scrape_weibo()
df_bili = scrape_bilibili()
df_yt = scrape_overseas("youtube") if PROXIES else pd.DataFrame()
df_x = scrape_overseas("x") if PROXIES else pd.DataFrame()

c1, c2, c3 = st.columns(3)
with c1: render_column("百度热搜", "🇨🇳", df_baidu)
with c2: render_column("微博热搜", "🇨🇳", df_weibo)
with c3: render_column("B站热门", "📺", df_bili)

st.markdown("<br>", unsafe_allow_html=True)

c4, c5, c6 = st.columns(3)
with c4:
    if PROXIES: render_column("YouTube", "🟥", df_yt)
    else: st.error("需代理")
with c5:
    if PROXIES: render_column("Twitter (X)", "✖️", df_x)
    else: st.error("需代理")
with c6:
    all_data = {"百度": df_baidu, "微博": df_weibo, "B站": df_bili, "YouTube": df_yt, "Twitter": df_x}
    # 从侧边栏获取配置，并直接调用
    generate_ai_report(all_data, api_key, api_base, model_name)