import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
# [修改 1] 引入智谱AI官方SDK
from zhipuai import ZhipuAI 
import os
import random
import datetime
import json
import time

# --- 页面配置 ---
st.set_page_config(page_title="全网热点 V4.4 (智谱版)", page_icon="🔥", layout="wide")

st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    /* AI 报告样式优化，适应竖向排版 */
    .ai-report {
        background-color: #f0f2f6; 
        padding: 15px; 
        border-radius: 10px; 
        border-top: 5px solid #3498db; /* 智谱蓝 */
        font-family: 'Microsoft YaHei', sans-serif;
        font-size: 14px;
    }
    div[data-testid="stVerticalBlock"] > div {gap: 0.5rem;}
    .demo-tag {
        font-size: 12px; color: #ff9f43; background: #fff3cd; 
        padding: 2px 6px; border-radius: 4px; margin-left: 5px;
    }
    a {text-decoration: none;}
    </style>
    """, unsafe_allow_html=True)

st.title("🔥 全网热点监控 (V4.4 智谱适配版)")
st.caption("8大模块聚合 | 4x2 黄金网格 | 智谱 GLM 实时洞察")

# --- 0. 控制台 & 设置 ---
with st.sidebar:
    st.header("⚙️ 控制台")
    if st.button("🔄 刷新全网数据", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    st.header("🤖 智谱 AI 配置")
    # [修改 2] 移除Base URL，仅保留API Key和模型名称
    api_key = st.text_input("智谱 API Key", type="password", help="请前往 bigmodel.cn 获取")
    model_name = st.text_input("模型名称", value="glm-4-flash", help="推荐 glm-4-flash (快) 或 glm-4")
    
    st.markdown("---")
    st.header("🌐 网络设置")
    is_cloud_mode = st.checkbox("我是云端部署 (Cloud Mode)", value=True)
    proxy_port = st.text_input("本地代理端口", value="")
    
    PROXIES = None
    if proxy_port:
        proxy_url = f"http://127.0.0.1:{proxy_port}"
        PROXIES = {"http": proxy_url, "https": proxy_url}
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url
    else:
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)

# --- 通用工具 ---
def get_random_ua():
    return random.choice([
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ])

def get_html(url, use_proxy=False, extra_headers=None):
    headers = {
        "User-Agent": get_random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    if extra_headers: headers.update(extra_headers)
    
    try:
        p = PROXIES if (use_proxy and not is_cloud_mode) else None
        response = requests.get(url, headers=headers, proxies=p, timeout=15)
        response.encoding = 'utf-8'
        return response.text if response.status_code == 200 else None
    except: return None

# --- 1. 模拟数据生成器 ---
def get_mock_data(platform_name):
    mock_db = {
        "百度": ["中国空间站", "GDP目标", "文旅抢人", "国产大模型", "五一车票"],
        "微博": ["微博反爬升级中", "建议稍后刷新", "正在尝试破解", "演示数据A", "演示数据B"],
        "B站": ["何同学新作", "罗翔说刑法", "原神前瞻", "拜年纪", "演示数据"],
        "抖音": ["科目三", "猫咪后空翻", "特种兵旅游", "听劝改造"],
        "小红书": ["年度总结", "显眼包穿搭", "CityWalk", "减脂餐"],
        "YouTube": ["MrBeast", "GTA VI", "SpaceX"],
        "Twitter": ["#Bitcoin", "#AI", "Elon Musk"]
    }
    titles = mock_db.get(platform_name, ["热点话题"])
    data = []
    for i in range(10):
        title = random.choice(titles) if i < len(titles) else f"{platform_name} 热门 {i+1}"
        data.append({
            "排名": i+1, "标题": title, "链接": "#", 
            "热度": f"{random.randint(100,999)}w", 
            "简介": "⚠️ 抓取失败 (Mock)", "is_mock": True
        })
    return pd.DataFrame(data)

# --- 2. 爬虫模块 ---

@st.cache_data(ttl=3600)
def scrape_baidu():
    html = get_html("https://top.baidu.com/board?tab=realtime")
    if not html: return get_mock_data("百度")
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
    return pd.DataFrame(data) if data else get_mock_data("百度")

@st.cache_data(ttl=3600)
def scrape_weibo():
    session = requests.Session()
    session.headers.update({"User-Agent": get_random_ua(), "Referer": "https://weibo.com/"})
    try:
        session.get("https://weibo.com/", timeout=5)
        resp = session.get("https://weibo.com/ajax/side/hotSearch", timeout=5)
        if resp.status_code == 200:
            data = resp.json()['data']['realtime']
            result = []
            for idx, item in enumerate(data[:10]):
                if 'rank' not in item and 'is_ad' in item: continue
                title = item['word']
                desc = f"【{item.get('label_name','')}】" if item.get('label_name') else ""
                result.append({"排名": idx+1, "标题": title, "链接": f"https://s.weibo.com/weibo?q={title}", "热度": str(item.get('num','')), "简介": desc, "is_mock": False})
            if result: return pd.DataFrame(result)
    except: pass

    try:
        headers_mobile = {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"}
        api_url = "https://m.weibo.cn/api/container/getIndex?containerid=106003type%3D25%26t%3D3%26disable_hot%3D1%26is_ext%3D1"
        resp = requests.get(api_url, headers=headers_mobile, timeout=5)
        if resp.status_code == 200:
            cards = resp.json()['data']['cards'][0]['card_group']
            result = []
            for idx, card in enumerate(cards[:10]):
                title = card['desc']
                result.append({"排名": idx+1, "标题": title, "链接": card['scheme'], "热度": str(card.get('desc_extr', '')), "简介": "", "is_mock": False})
            if result: return pd.DataFrame(result)
    except: pass
    return get_mock_data("微博")

@st.cache_data(ttl=3600)
def scrape_bilibili():
    headers = {"User-Agent": get_random_ua(), "Referer": "https://www.bilibili.com/v/popular/rank/all", "Cookie": "b_nut=1712000000;"}
    try:
        resp = requests.get("https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = []
            for idx, v in enumerate(resp.json()['data']['list'][:10]):
                play = v['stat']['view']
                play_s = f"{play/10000:.1f}万" if play > 10000 else str(play)
                data.append({"排名": idx+1, "标题": v['title'], "链接": v['short_link_v2'], "UP主": v['owner']['name'], "播放": play_s, "is_mock": False})
            return pd.DataFrame(data)
    except: pass
    return get_mock_data("B站")

@st.cache_data(ttl=3600)
def scrape_douyin():
    try:
        url = "https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/"
        resp = requests.get(url, headers={"User-Agent": get_random_ua()}, timeout=5)
        data = []
        for idx, item in enumerate(resp.json()['word_list'][:10]):
            title = item.get('word')
            heat = item.get('hot_value')
            data.append({"排名": idx+1, "标题": title, "链接": f"https://www.douyin.com/search/{title}", "热度": f"{heat/10000:.1f}w", "is_mock": False})
        return pd.DataFrame(data)
    except: return get_mock_data("抖音")

@st.cache_data(ttl=3600)
def scrape_xhs():
    return get_mock_data("小红书")

@st.cache_data(ttl=3600)
def scrape_overseas(platform):
    url = "https://kworb.net/youtube/trending_overall.html" if platform == "youtube" else "https://getdaytrends.com/"
    html = get_html(url, use_proxy=True)
    if not html: return get_mock_data("YouTube" if platform=="youtube" else "Twitter")
    
    soup = BeautifulSoup(html, 'lxml')
    data = []
    try:
        if platform == "youtube":
            for idx, row in enumerate(soup.find('tbody').find_all('tr')[:10]):
                link_tag = row.find('a')
                href = link_tag['href']
                link = f"https://www.youtube.com/watch?v={href.split('video/')[1].replace('.html','')}" if "video/" in href else href
                data.append({"排名": idx+1, "标题": link_tag.text.strip(), "链接": link, "is_mock": False})
        elif platform == "x":
            rows = soup.select('table.table tbody tr')
            for idx, row in enumerate(rows[:10]):
                link_tag = row.find('a')
                if link_tag:
                    title = link_tag.text.strip()
                    link = "https://twitter.com/search?q=" + title.replace("#", "%23")
                    heat = row.find('small').text.strip() if row.find('small') else ""
                    data.append({"排名": idx+1, "标题": title, "链接": link, "热度": heat, "is_mock": False})
    except: pass
    return pd.DataFrame(data) if data else get_mock_data("YouTube" if platform=="youtube" else "Twitter")

# --- 4. AI 分析 (适配智谱版) ---
def generate_ai_report(dfs_dict, api_key, model_name):
    # 显示标题（与其他列对齐）
    st.markdown("### 🧠 智谱 AI 洞察")
    st.markdown("---")
    
    if not api_key:
        st.info("👈 请配置 智谱 API Key")
        return
    
    # 构造 Prompt
    prompt = "你是一位全网舆情专家。以下是各平台实时热搜：\n\n"
    has_data = False
    for plat, df in dfs_dict.items():
        if not df.empty:
            has_data = True
            titles = df['标题'].tolist()
            is_mock = df.iloc[0].get('is_mock', False)
            tag = "(演示数据)" if is_mock else ""
            prompt += f"【{plat}{tag}】：{', '.join(titles)}\n"
    
    if not has_data: return

    prompt += """
    \n请生成一份简练的【舆情简报】（Markdown格式，不要太长）：
    1. **焦点话题**：全网都在看什么？
    2. **平台差异**：抖音/小红书 vs 微博/B站 vs 海外。
    3. **趋势预测**：下一个爆点。
    """
    
    try:
        # [修改 3] 使用 ZhipuAI Client
        client = ZhipuAI(api_key=api_key)
        
        with st.spinner(f"🚀 智谱 AI ({model_name}) 分析中..."):
            completion = client.chat.completions.create(
                model=model_name, 
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            st.markdown('<div class="ai-report">', unsafe_allow_html=True)
            st.markdown(completion.choices[0].message.content)
            st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e: st.error(f"AI 失败: {e}")

# --- 5. UI 渲染 ---
def render_col(title, emoji, df):
    with st.container():
        is_mock = df.iloc[0].get('is_mock', False) if not df.empty else False
        header = f"### {emoji} {title}"
        if is_mock: header += ' <span class="demo-tag">演示</span>'
        st.markdown(header, unsafe_allow_html=True)
        st.markdown("---")
        
        if df.empty: st.caption("暂无数据")
        else:
            for _, row in df.iterrows():
                st.markdown(f"**{row['排名']}. [{row['标题']}]({row['链接']})**")
                meta = []
                if '热度' in row: meta.append(f"🔥 {row['热度']}")
                if 'UP主' in row: meta.append(f"👤 {row['UP主']}")
                st.caption(" · ".join(meta))
                st.markdown("---")

# --- 主程序 ---
run_overseas = True if is_cloud_mode else (PROXIES is not None)

data_map = {
    "百度": scrape_baidu(),
    "微博": scrape_weibo(),
    "B站": scrape_bilibili(),
    "抖音": scrape_douyin(),
    "小红书": scrape_xhs(),
    "YouTube": scrape_overseas("youtube") if run_overseas else pd.DataFrame(),
    "Twitter": scrape_overseas("x") if run_overseas else pd.DataFrame()
}

# === 布局：4 + 4 完美网格 ===

# 第一行：微博 | 抖音 | 百度 | B站
c1, c2, c3, c4 = st.columns(4)
with c1: render_col("微博", "🍉", data_map["微博"])
with c2: render_col("抖音", "🎵", data_map["抖音"])
with c3: render_col("百度", "🇨🇳", data_map["百度"])
with c4: render_col("B站", "📺", data_map["B站"])

st.markdown("<br>", unsafe_allow_html=True)

# 第二行：小红书 | Twitter | YouTube | AI简报
c5, c6, c7, c8 = st.columns(4)
with c5: render_col("小红书", "📕", data_map["小红书"])

with c6:
    if run_overseas: render_col("Twitter", "✖️", data_map["Twitter"])
    else: st.error("需代理")

with c7:
    if run_overseas: render_col("YouTube", "🟥", data_map["YouTube"])
    else: st.error("需代理")

with c8:
    # 第8列专门放 AI 报告
    # [修改 4] 移除 api_base 参数
    generate_ai_report(data_map, api_key, model_name)