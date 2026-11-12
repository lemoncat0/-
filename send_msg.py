import requests
from datetime import datetime
import os

WX_APPID = os.getenv("WX_APPID")
WX_APPSECRET = os.getenv("WX_APPSECRET")
OPENID = os.getenv("OPENID")
TEMPLATE_ID = os.getenv("TEMPLATE_ID")

QWEATHER_KEY = os.getenv("QWEATHER_KEY")
# 滑县真实location_id，来自你刚刚的接口查询结果
LOCATION_ID = "101180203"
TARGET_CITY = "滑县"
TIANAPI_KEY = os.getenv("TIANAPI_KEY")
LOVE_START_DATE = os.getenv("LOVE_START_DATE")
TIAN_TYPE = os.getenv("TIAN_TYPE", "saylove")


def get_wx_access_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WX_APPID}&secret={WX_APPSECRET}"
    res = requests.get(url).json()
    if "access_token" not in res:
        raise Exception(f"微信token获取失败：{res}")
    return res["access_token"]


def get_weather(loc_id, key):
    url = f"https://devapi.qweather.com/v7/weather/now?location={loc_id}&key={key}"
    resp = requests.get(url).json()
    if resp["code"] != "200":
        return {"text": "未知天气", "temp": "--", "tip": "天气查询失败"}
    now = resp["now"]
    weather_text = now["text"]
    temp = now["temp"]
    t = int(temp)
    if t < 5:
        tip = "天气很冷，记得多穿厚衣服，注意保暖。"
    elif t < 15:
        tip = "气温偏低，出门带上外套。"
    elif t < 25:
        tip = "温度很舒服，适合出门走走。"
    elif t < 32:
        tip = "有点热，注意补水防晒。"
    else:
        tip = "高温天气，尽量少在外面久待。"
    return {"text": weather_text, "temp": temp, "tip": tip}


def get_tian_content(api_key, tian_type):
    say_text = ""
    news_text = ""
    if tian_type == "saylove":
        r = requests.get(f"https://apis.tianapi.com/saylove/index?key={api_key}").json()
        if r["code"] == 200:
            say_text = r["result"]["content"]
    elif tian_type == "zaoxin":
        r = requests.get(f"https://apis.tianapi.com/zaoxin/index?key={api_key}").json()
        if r["code"] == 200:
            say_text = r["result"]["content"]
    # 每日简报
    r_bul = requests.get(f"https://apis.tianapi.com/bulletin/index?key={api_key}").json()
    if r_bul["code"] == 200 and len(r_bul["result"]["list"]) > 0:
        first = r_bul["result"]["list"][0]
        news_text = f"{first['title']}：{first['digest'][:45]}..."
    return say_text, news_text


def calc_love_days(start_date):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    now = datetime.now()
    delta = now - start
    return f"{delta.days}天"


def send_template_msg():
    token = get_wx_access_token()
    weather = get_weather(LOCATION_ID, QWEATHER_KEY)
    say_text, news_text = get_tian_content(TIANAPI_KEY, TIAN_TYPE)
    love_day_str = calc_love_days(LOVE_START_DATE)

    data = {
        "touser": OPENID,
        "template_id": TEMPLATE_ID,
        "data": {
            "date": {"value": datetime.now().strftime("%Y-%m-%d")},
            "city": {"value": TARGET_CITY},
            "weather": {"value": weather["text"]},
            "temp": {"value": weather["temp"] + " ℃"},
            "tip": {"value": weather["tip"]},
            "love_day": {"value": love_day_str},
            "say": {"value": say_text},
            "news": {"value": news_text}
        }
    }
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    res = requests.post(url, json=data).json()
    print("微信返回结果：", res)
    if res["errcode"] != 0:
        raise Exception(f"推送失败 {res}")


if __name__ == "__main__":
    send_template_msg()
