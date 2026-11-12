import requests
from datetime import datetime
import os

# ====================== 从Secrets读取配置 ======================
WX_APPID = os.getenv("WX_APPID")
WX_APPSECRET = os.getenv("WX_APPSECRET")
OPENID = os.getenv("OPENID")
TEMPLATE_ID = os.getenv("TEMPLATE_ID")
QWEATHER_KEY = os.getenv("QWEATHER_KEY")
TIANAPI_KEY = os.getenv("TIANAPI_KEY")
LOVE_START_DATE = os.getenv("LOVE_START_DATE")
TIAN_TYPE = os.getenv("TIAN_TYPE", "saylove")

# 滑县固定location_id，直接跳过城市搜索，不再用下线的geo接口
LOCATION_ID = "101180203"
TARGET_CITY = "滑县"
# ==================================================================

def get_wx_token():
    print("[1/4] 正在获取微信access_token...")
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WX_APPID}&secret={WX_APPSECRET}"
    try:
        res = requests.get(url, timeout=10).json()
        if "access_token" in res:
            print("✅ 微信token获取成功")
            return res["access_token"]
        print(f"❌ 微信token返回错误: {res}")
        return None
    except Exception as e:
        print(f"❌ 微信token请求失败: {e}")
        return None

def get_weather():
    print("[2/4] 正在查询滑县天气...")
    url = f"https://devapi.qweather.com/v7/weather/now?location={LOCATION_ID}&key={QWEATHER_KEY}"
    try:
        resp = requests.get(url, timeout=10).json()
        if resp.get("code") == "200":
            now = resp["now"]
            t = int(now["temp"])
            if t < 5:
                tip = "天气很冷，多穿厚衣服，注意保暖。"
            elif t < 15:
                tip = "气温偏低，出门带件外套。"
            elif t < 25:
                tip = "温度很舒服，适合出门走走。"
            elif t < 32:
                tip = "有点热，记得多喝水防晒。"
            else:
                tip = "高温天气，尽量少在外面久待。"
            print(f"✅ 天气查询成功: {now['text']} {now['temp']}℃")
            return {"text": now["text"], "temp": now["temp"], "tip": tip}
        print(f"❌ 天气接口返回错误: {resp}")
    except Exception as e:
        print(f"❌ 天气请求失败: {e}")
    return {"text": "未知", "temp": "--", "tip": "今天也要好好照顾自己。"}

def get_tian_content():
    print("[3/4] 正在获取情话和新闻...")
    say_text = ""
    news_text = ""
    # 土味情话 / 早安心语 二选一
    if TIAN_TYPE == "zaoan":
        url = f"https://apis.tianapi.com/zaoan/index?key={TIANAPI_KEY}"
    else:
        url = f"https://apis.tianapi.com/saylove/index?key={TIANAPI_KEY}"
    try:
        r = requests.get(url, timeout=10).json()
        if r.get("code") == 200:
            say_text = r["result"]["content"]
            print("✅ 心语获取成功")
        else:
            print(f"⚠️ 心语接口失败: {r}，用默认文案")
            say_text = "今天也要开开心心呀。"
    except Exception as e:
        print(f"⚠️ 心语请求失败: {e}，用默认文案")
        say_text = "我一直在惦记你。"
    # 每日简报
    try:
        r_bul = requests.get(f"https://apis.tianapi.com/bulletin/index?key={TIANAPI_KEY}", timeout=10).json()
        if r_bul.get("code") == 200 and len(r_bul["result"]["list"]) > 0:
            first = r_bul["result"]["list"][0]
            news_text = f"{first['title']}"
            print("✅ 新闻获取成功")
    except Exception as e:
        print(f"⚠️ 新闻请求失败: {e}")
        news_text = ""
    return say_text, news_text

def send_msg(token, weather, say_text, news_text):
    print("[4/4] 正在发送微信推送...")
    start = datetime.strptime(LOVE_START_DATE, "%Y-%m-%d")
    days = (datetime.now() - start).days
    data = {
        "touser": OPENID,
        "template_id": TEMPLATE_ID,
        "data": {
            "date": {"value": datetime.now().strftime("%Y-%m-%d")},
            "city": {"value": TARGET_CITY},
            "weather": {"value": weather["text"]},
            "temp": {"value": weather["temp"] + " ℃"},
            "tip": {"value": weather["tip"]},
            "love_day": {"value": f"在一起第{days}天"},
            "say": {"value": say_text},
            "news": {"value": news_text if news_text else "暂无新闻"}
        }
    }
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    try:
        res = requests.post(url, json=data, timeout=10).json()
        print(f"✅ 微信推送返回: {res}")
        if res.get("errcode") == 0:
            print("🎉 推送成功！")
        else:
            print(f"❌ 推送失败: {res}")
    except Exception as e:
        print(f"❌ 发送请求失败: {e}")

if __name__ == "__main__":
    print("=== 开始执行每日推送 ===")
    token = get_wx_token()
    if not token:
        exit(1)
    weather = get_weather()
    say_text, news_text = get_tian_content()
    send_msg(token, weather, say_text, news_text)
    print("=== 执行结束 ===")
