# -*- coding: utf-8 -*-
"""
每日暖心推送：天气 + 情话/心语轮换 + 新闻/热搜/健康，生成 H5 聚合页并推送微信卡片。
密钥全部从 GitHub Secrets 读取，代码里不写任何真实密钥。
"""
import os
import html
import requests
from datetime import datetime, timezone, timedelta

# ====================== 从 Secrets 读取配置 ======================
WX_APPID = os.getenv("WX_APPID")
WX_APPSECRET = os.getenv("WX_APPSECRET")
OPENID = os.getenv("OPENID")
TEMPLATE_ID = os.getenv("TEMPLATE_ID")
TIANAPI_KEY = os.getenv("TIANAPI_KEY")
LOVE_START_DATE = os.getenv("LOVE_START_DATE")
# ==================================================================

# 固定配置（滑县坐标）
CITY = "滑县"
LAT, LON = 35.58, 114.55
# GitHub Pages 站点地址（仓库名 -，根目录 index.html）
PAGES_URL = "https://lemoncat0.github.io/-/"

BJ = timezone(timedelta(hours=8))
now = datetime.now(BJ)

# WMO 天气码 → 中文
WMO = {
    0: "晴", 1: "大部晴朗", 2: "多云", 3: "阴",
    45: "雾", 48: "冻雾",
    51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨", 56: "冻毛毛雨", 57: "冻毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨", 66: "冻雨", 67: "冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
    80: "阵雨", 81: "阵雨", 82: "强阵雨", 85: "阵雪", 86: "阵雪",
    95: "雷雨", 96: "雷雨伴冰雹", 99: "雷雨伴冰雹",
}


def fetch_json(url, params=None):
    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json()
    except Exception as e:
        print("请求失败:", url, e)
        return None


def get_weather():
    """Open-Meteo 免费天气，无需 key。"""
    data = fetch_json("https://api.open-meteo.com/v1/forecast", {
        "latitude": LAT, "longitude": LON,
        "current": "temperature_2m,weather_code,apparent_temperature",
        "timezone": "Asia/Shanghai",
    })
    if not data or "current" not in data:
        return {"text": "未知", "temp": "--", "tip": "今天也要好好照顾自己。"}
    c = data["current"]
    code = c.get("weather_code", 0)
    temp = round(c.get("temperature_2m", 0))
    text = WMO.get(code, "未知")
    if temp < 5:
        tip = "天气很冷，多穿厚衣服，注意保暖。"
    elif temp < 15:
        tip = "气温偏低，出门记得带件外套。"
    elif temp < 25:
        tip = "温度很舒服，适合出门走走。"
    elif temp < 32:
        tip = "有点热，注意补水和防晒。"
    else:
        tip = "高温天气，尽量少在外面久待。"
    return {"text": text, "temp": temp, "tip": tip}


def tian(path, num=3, extra=None):
    """调用天行接口，兼容三种结构：result.list / result.newslist / result 为数组；
    单条接口（情话/心语/妙招）result 直接是内容字典，也包成 [dict] 返回。"""
    params = {"key": TIANAPI_KEY, "num": num}
    if extra:
        params.update(extra)
    data = fetch_json(f"https://apis.tianapi.com/{path}/index", params)
    if not data or data.get("code") != 200:
        print(f"  天行 {path} 返回:", data)
        return []
    res = data.get("result")
    if isinstance(res, dict):
        lst = res.get("list") or res.get("newslist")
        if not lst:
            lst = [res]  # 单条接口：result 本身就是内容字典
    elif isinstance(res, list):
        lst = res
    else:
        lst = []
    return lst if isinstance(lst, list) else []


def news_item(x):
    return {
        "title": (x.get("title") or "").strip(),
        "url": (x.get("url") or "").strip(),
        "source": (x.get("source") or "").strip(),
        "desc": (x.get("description") or x.get("digest") or "").strip(),
    }


def esc(s):
    return html.escape(str(s if s is not None else ""))


# ---------------- 1. 轮换：一天土味情话，一天早安心语 ----------------
day_of_year = now.timetuple().tm_yday
if day_of_year % 2 == 0:
    say_label, say_path = "今日情话", "saylove"
else:
    say_label, say_path = "今日心语", "zaoan"

say_items = tian(say_path, 1)
say = (say_items[0].get("content", "") if say_items else "") or "想你，是我每天都会做的小事。"

# ---------------- 2. 各类内容容错拉取 ----------------
social = [news_item(x) for x in tian("social", 3)][:2]
ai = [news_item(x) for x in tian("ai", 3)][:2]
bulletin = [news_item(x) for x in tian("bulletin", 3)][:2]

hot = []
for x in tian("networkhot", 5):
    hot.append({
 "title": (x.get("title") or "").strip(),
 "hot": x.get("hotnum", ""),
 "desc": (x.get("digest") or "").strip(),
 })
hot = hot[:3]

# 健康小妙招：healthskill 需传关键词，内置一组常见养生主题按天轮换
HEALTH_WORDS = ["失眠", "疲劳", "护眼", "上火", "颈椎", "肠胃",
 "减脂", "脱发", "便秘", "感冒", "咳嗽", "口臭"]
health_word = HEALTH_WORDS[day_of_year % len(HEALTH_WORDS)]
health = tian("healthskill", extra={"word": health_word})
health_title = (health[0].get("title", "") if health else "").strip()
health_text = (health[0].get("content", "") if health else "").strip() or "好好吃饭，好好睡觉，少熬夜。"

# ---------------- 3. 在一起天数 ----------------
try:
    start = datetime.strptime(LOVE_START_DATE, "%Y-%m-%d")
    days = (now.replace(tzinfo=None) - start).days
except Exception:
    days = 0
love_day = f"在一起第{days}天"

weather = get_weather()

# 卡片“今日看点”取第一条有标题的新闻
first_news = next((n["title"] for n in (social + ai + bulletin) if n["title"]),
 "今日热点已整理在下方页面")

date_str = now.strftime("%Y-%m-%d")
week_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()]


# ---------------- 4. 生成 H5 聚合页 ----------------
def render_news_block(title, items, with_desc=True):
 if not items:
 return ""
    rows = []
 for n in items:
 if not n["title"]:
 continue
        desc = f'<p class="desc">{esc(n["desc"])}</p>' if (with_desc and n["desc"]) else ""
        source = f'<span class="source">{esc(n["source"])}</span>' if n["source"] else ""
 if n["url"]:
            body = f'<a class="item" href="{esc(n["url"])}" target="_blank" rel="noopener noreferrer">' \
 f'<div class="title">{esc(n["title"])}</div>{desc}{source}</a>'
 else:
            body = f'<div class="item"><div class="title">{esc(n["title"])}</div>{desc}{source}</div>'
        rows.append(body)
 if not rows:
 return ""
 return f'<section class="block"><h3>{esc(title)}</h3>{"".join(rows)}</section>'


def render_hot_block():
 if not hot:
 return ""
    rows = []
 for i, n in enumerate(hot, 1):
 if not n["title"]:
 continue
        hot_label = f'🔥 {esc(n["hot"])}' if n["hot"] else ""
        rows.append(f'<div class="item rank"><span class="no">{i}</span>'
 f'<div><div class="title">{esc(n["title"])}</div>'
 f'<span class="hot">{hot_label}</span></div></div>')
 if not rows:
 return ""
 return f'<section class="block"><h3>全网热搜</h3>{"".join(rows)}</section>'


page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>每日暖心推送 · {esc(date_str)}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; background:#f6f1ee; color:#3a3330; padding-bottom:40px; }}
  .hero {{ background:linear-gradient(135deg,#ff9a9e,#fecfef 60%,#f6d5f7); padding:28px 20px 22px; color:#5a2e3a; }}
  .hero .date {{ font-size:14px; opacity:.85; }}
  .hero .city {{ font-size:22px; font-weight:700; margin-top:6px; }}
  .hero .w {{ display:flex; align-items:baseline; gap:10px; margin-top:10px; }}
  .hero .temp {{ font-size:40px; font-weight:800; }}
  .hero .wt {{ font-size:16px; }}
  .card {{ background:#fff; margin:16px 14px; border-radius:18px; padding:18px 16px; box-shadow:0 4px 14px rgba(180,120,130,.12); }}
  .love {{ text-align:center; }}
  .love .label {{ display:inline-block; background:#ffe3ec; color:#d14d72; font-size:13px; border-radius:20px; padding:3px 12px; }}
  .love .say {{ font-size:17px; line-height:1.7; margin-top:12px; }}
  .days {{ text-align:center; font-size:14px; color:#b07; margin-top:8px; }}
  .block {{ margin-top:4px; }}
  .block h3 {{ font-size:15px; color:#c2557a; margin-bottom:10px; }}
  .item {{ display:block; padding:12px 0; border-bottom:1px solid #f2e9ea; text-decoration:none; color:inherit; }}
  .item:last-child {{ border-bottom:none; }}
  .item .title {{ font-size:15px; line-height:1.55; }}
  .item .desc {{ font-size:13px; color:#8a7f7c; margin-top:5px; line-height:1.6; }}
  .item .source {{ display:inline-block; font-size:12px; color:#b9a8a4; margin-top:6px; }}
  .rank {{ display:flex; gap:10px; }}
  .rank .no {{ width:20px; font-weight:800; color:#e89; }}
  .hot {{ font-size:12px; color:#e2703a; }}
  .health {{ background:#fff7ee; border:1px dashed #f2c98a; }}
  .health .tip {{ font-size:15px; line-height:1.7; color:#8a6a3a; }}
  footer {{ text-align:center; font-size:12px; color:#b9a8a4; margin-top:24px; }}
</style>
</head>
<body>
  <div class="hero">
    <div class="date">{esc(date_str)} · {esc(week_cn)}</div>
    <div class="city">{esc(CITY)}</div>
    <div class="w">
      <div class="temp">{esc(weather["temp"])}℃</div>
      <div class="wt">{esc(weather["text"])}</div>
    </div>
    <div class="desc" style="margin-top:8px;font-size:14px;">{esc(weather["tip"])}</div>
  </div>

  <div class="card love">
    <span class="label">{esc(say_label)}</span>
    <div class="say">{esc(say)}</div>
    <div class="days">💗 {esc(love_day)}</div>
  </div>

 {render_news_block("社会新闻", social)}
 {render_news_block("AI 资讯", ai)}
 {render_news_block("每日简报", bulletin)}
 {render_hot_block()}

  <div class="card health">
    <h3 style="color:#c98a3a;margin-bottom:8px;">💡 健康小妙招{(' · ' + esc(health_title)) if health_title else ''}</h3>
    <div class="tip">{esc(health_text)}</div>
  </div>

  <footer>每天一份小浪漫 · 为你而生</footer>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(page)
print("✅ H5 聚合页已生成 index.html")


# ---------------- 5. 推送微信卡片 ----------------
def get_wx_token():
    url = ("https://api.weixin.qq.com/cgi-bin/token"
 f"?grant_type=client_credential&appid={WX_APPID}&secret={WX_APPSECRET}")
    res = fetch_json(url)
 if not res or "access_token" not in res:
 print("❌ 微信 token 获取失败:", res)
 return None
 return res["access_token"]


def send_card(token):
    data = {
 "touser": OPENID,
 "template_id": TEMPLATE_ID,
 "url": PAGES_URL,
 "data": {
 "date": {"value": date_str},
 "city": {"value": CITY},
 "weather": {"value": weather["text"]},
 "temp": {"value": f'{weather["temp"]} ℃'},
 "tip": {"value": weather["tip"]},
 "love_day": {"value": love_day},
 "say": {"value": say[:60]},
 "news": {"value": first_news[:30]},
 },
 }
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    res = fetch_json(url)
 print("微信返回:", res)
 return res


if __name__ == "__main__":
 print("=== 开始执行每日推送 ===")
    token = get_wx_token()
 if token:
 send_card(token)
 print("=== 执行结束 ===")
