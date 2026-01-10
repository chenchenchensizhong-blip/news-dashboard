import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from openai import OpenAI
import os
import random
import datetime

# --- 页面配置 ---
st.set_page_config(page_title="全网热点 V3.8 (演示版)", page_icon="🛡️", layout="wide")

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
    .demo-tag {
        font-size: 12px; 
        color: #ff9f43; 
        background: #fff3cd; 
        padding: 2px 6px; 
        border-radius: 4px;
        margin-left: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ 全网热点监控 (V3.8 优雅降级版)")
st.caption("检测到云端阻断时自动切换至演示数据 | 保证界面完整性")

# --- 0. 控制台 & 设置 ---
with st.sidebar:
    st.header("⚙️ 控制台")
    if st.button("🔄 刷新全网数据", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    st.header("🤖 AI 配置")
    api_base = st.text_input("API Base URL", value="https://api.groq.com/openai/v1")
    api_key = st.text_input("API Key", type="password")
    model_name = st.text_input("模型名称", value="llama-3.3-70b-versatile")
    
    st.markdown("---")
    st.header("🌐 网络设置")
    is_cloud_mode = st.checkbox("我是云端部署 (Cloud Mode)", value=True)
    proxy_port = st.text_input("本地代理端口 (仅本地需填)", value="")
    
    PROXIES = None
    if proxy_port:
        proxy_url = f"http://127.0.0.1:{proxy_port}"
        PROXIES = {"http": proxy_url, "https": proxy_url}
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url
    else:
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)

def get_html(url, use_proxy=False):
    # 尽可能模拟真实用户
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.baidu.com/",
        "Cookie": "BIDUPSID=12345; PSTM=12345;" # 尝试塞个假 Cookie
    }
    
    try:
        p = PROXIES if (use_proxy and not is_cloud_mode) else None
        response = requests.get(url, headers=headers, proxies=p, timeout=10)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            return response.text
        return None
    except:
        return None

# --- 1. 模拟数据生成器 (关键功能) ---
def get_mock_data(platform_name):
    """当爬虫失败时，生成好看的假数据，防止开天窗"""
    current_time = datetime.datetime.now().strftime("%H:%M")
    
    mock_titles = {
        "百度": [
            f"中国空间站第四批航天员选拔完成 {current_time}", "2024年GDP增长目标发布", "各地文旅开启'抢人'模式",
            "国产大模型技术突破", "新能源汽车销量再创新高", "五一假期火车票开售", 
            "科学家发现新系外行星", "某知名歌手巡回演唱会官宣"
        ],
        "微博": [
            f"这就是中国式浪漫 {current_time}", "建议专家不要建议", "考研成绩", 
            "熊猫花花", "春天的第一杯奶茶", "没想到你是这样的", 
            "可以不结婚但不能不...", "这泼天的富贵轮到我了"
        ],
        "B站": [
            "【何同学】我做了一个...", "耗时300天，还原...", "【罗翔】法律...", 
            "这是我不花钱能看的吗？", "原神：新版本前瞻", "【全程高能】...", 
            "2024拜年纪", "关于我转生变成..."
        ]
    }
    
    titles = mock_titles.get(platform_name, ["演示数据标题1", "演示数据标题2"])
    data = []
    for i in range(8):
        title = random.choice(titles) if i < len(titles) else f"{platform_name}热点话题 {i+1}"
        data.append({
            "排名": i+1,
            "标题": title,
            "链接": "#", # 演示链接
            "热度": f"{random.randint(100, 999)}万",
            "简介": "⚠️ 因云端IP限制，当前显示为演示数据 (Mock Data)",
            "is_mock": True # 标记为假数据
        })
    return pd.DataFrame(data)

# --- 2. 爬虫模块 (带降级逻辑) ---

@st.cache_data(ttl=3600)
def scrape_baidu():
    url = "https://top.baidu.com/board?tab=realtime"
    html = get_html(url)
    if not html: return get_mock_data("百度") # <--- 失败则返回假数据
    
    soup = BeautifulSoup(html, 'lxml')
    data = []
    items = soup.find_all('div', class_='category-wrap_iQLoo')
    for idx, item in enumerate(items[:10]):
        try:
            title = item.find('div', class_='c-single-text-ellipsis').text.strip()
            link = item.find('a')['href']
            heat = item.find('div', class_='hot-index_1Bl1a').text.strip()
            data.append({"排名": idx+1, "标题": title, "链接": link, "热度": heat, "is_mock": False})
        except: continue
        
    if not data: return get_mock_data("百度")
    return pd.DataFrame(data)

@st.cache_data(ttl=3600)
def scrape_weibo():
    api_url = "https://weibo.com/ajax/side/hotSearch"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Referer": "https://weibo.com/",
            "Cookie": "SUB=_2A25;" # 极简 Cookie
        }
        resp = requests.get(api_url, headers=headers, timeout=5)
        if resp.status_code != 200: return get_mock_data("微博")
        
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
            result.append({"排名": idx+1, "标题": title, "链接": link, "热度": str(heat), "简介": desc, "is_mock": False})
        return pd.DataFrame(result)
    except: return get_mock_data("微博")

@st.cache_data(ttl=3600)
def scrape_bilibili():
    # B站 Web 接口
    api_url = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/"
    }
    try:
        resp = requests.get(api_url, headers=headers, timeout=5)
        if resp.status_code != 200: return get_mock_data("B站")
        json_data = resp.json()
        video_list = json_data['data']['list']
        data = []
        for idx, video in enumerate(video_list[:10]):
            title = video['title']
            author = video['owner']['name']
            play = video['stat']['view']
            play_str = f"{play/10000:.1f}万" if play > 10000 else str(play)
            link = video['short_link_v2']
            data.append({"排名": idx+1, "标题": title, "链接": link, "UP主": author, "播放": play_str, "is_mock": False})
        return pd.DataFrame(data)
    except: return get_mock_data("B站")

@st.cache_data(ttl=3600)
def scrape_overseas(platform):
    # 海外平台代码保持不变，因为它们在云端是通的
    url = "https://kworb.net/youtube/trending_overall.html" if platform == "youtube" else "https://getdaytrends.com/"
    html = get_html(url, use_proxy=True)
    if not html: return pd.DataFrame() # 海外失败暂时不 Mock，因为通常能通
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
                    data.append({"排名": idx+1, "标题": title, "链接": link, "is_mock": False})
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
                    data.append({"排名": idx+1, "标题": title, "链接": link, "热度": heat, "is_mock": False})
        except: pass
    return pd.DataFrame(data)

# --- 3. AI 分析模块 ---

def generate_ai_report(dfs_dict, api_key, api_base, model_name):
    if not api_key:
        st.info("👈 请在左侧输入 API Key 开启 AI 分析")
        return

    prompt_text = "你是一位舆情分析师。以下是数据（部分可能为演示数据，请正常分析）：\n\n"
    has_data = False
    for platform, df in dfs_dict.items():
        if not df.empty:
            has_data = True
            titles = df['标题'].tolist()
            # 如果是假数据，稍微提示一下 AI，但让它继续分析
            is_mock = df.iloc[0].get('is_mock', False)
            note = "(演示数据)" if is_mock else ""
            prompt_text += f"【{platform}{note}】：{', '.join(titles)}\n"
    
    if not has_data: return

    prompt_text += """
    \n请生成简报（Markdown）：
    1. **核心焦点**：总结关注点。
    2. **情绪晴雨表**：分析情绪。
    3. **爆款预测**：预测发酵话题。
    """

    try:
        client = OpenAI(api_key=api_key, base_url=api_base)
        with st.spinner(f"🚀 正在呼叫 {model_name} 分析..."):
            completion = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt_text}],
                temperature=0.7,
            )
            st.markdown('<div class="ai-report">', unsafe_allow_html=True)
            st.markdown("### 🚀 AI 舆情简报")
            st.markdown(completion.choices[0].message.content)
            st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"AI 分析失败: {e}")

# --- 4. UI 渲染 ---

def render_column(title, emoji, df):
    with st.container():
        # 检查是否是 Mock 数据
        is_mock = False
        if not df.empty and 'is_mock' in df.columns:
            is_mock = df.iloc[0]['is_mock']
            
        header_html = f"### {emoji} {title}"
        if is_mock:
            header_html += ' <span class="demo-tag">演示数据</span>'
            
        st.markdown(header_html, unsafe_allow_html=True)
        st.markdown("---")
        
        if df.empty:
            st.caption("⚠️ 暂无数据")
        else:
            for _, row in df.iterrows():
                st.markdown(f"**{row['排名']}. [{row['标题']}]({row['链接']})**")
                
                meta = []
                if '热度' in row and row['热度']: meta.append(f"🔥 {row['热度']}")
                if 'UP主' in row: meta.append(f"👤 {row['UP主']}")
                if '简介' in row and row['简介']: meta.append(f"{row['简介']}")
                
                # 如果是 Mock 数据，说明原因
                if is_mock and row['排名'] == 1:
                    st.caption("⚠️ 云端IP被拦截，已自动切换至演示数据以保持界面完整。")
                else:
                    st.caption(" · ".join(meta))
                st.markdown("---")

# --- 主程序 ---
run_overseas = True if is_cloud_mode else (PROXIES is not None)

df_baidu = scrape_baidu()
df_weibo = scrape_weibo()
df_bili = scrape_bilibili()
df_yt = scrape_overseas("youtube") if run_overseas else pd.DataFrame()
df_x = scrape_overseas("x") if run_overseas else pd.DataFrame()

c1, c2, c3 = st.columns(3)
with c1: render_column("百度热搜", "🇨🇳", df_baidu)
with c2: render_column("微博热搜", "🇨🇳", df_weibo)
with c3: render_column("B站热门", "📺", df_bili)

st.markdown("<br>", unsafe_allow_html=True)

c4, c5, c6 = st.columns(3)
with c4:
    if run_overseas: render_column("YouTube", "🟥", df_yt)
    else: st.error("本地需配置代理")
with c5:
    if run_overseas: render_column("Twitter (X)", "✖️", df_x)
    else: st.error("本地需配置代理")
with c6:
    all_data = {"百度": df_baidu, "微博": df_weibo, "B站": df_bili, "YouTube": df_yt, "Twitter": df_x}
    generate_ai_report(all_data, api_key, api_base, model_name)