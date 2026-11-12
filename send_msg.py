import requests
import random
from datetime import datetime
import os

WX_APPID = os.getenv("WX_APPID")
WX_APPSECRET = os.getenv("WX_APPSECRET")
OPENID = os.getenv("OPENID")
TEMPLATE_ID = os.getenv("TEMPLATE_ID")

QWEATHER_KEY = os.getenv("QWEATHER_KEY")
TARGET_CITY = os.getenv("TARGET_CITY", "滑县")
TIANAPI_KEY = os.getenv("TIANAPI_KEY")
LOVE_START_DATE = os.getenv("LOVE_START_DATE")

# 可选类型：saylove=土味情话 | zaoxin=早安心语 | bulletin=每日简报
# 如果你想要心语+简报一起推送，代码里已经做好
TIAN_TYPE = os.getenv("TIAN_TYPE", "saylove")


def get_wx_access_token():
    url = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}".format(WX_APPID, WX_APPSECRET)
    res = requests.get(url).json()
    if "access_token" not in res:
        raise Exception(f"获取微信token失败：{res}")
    return res["access_token"]


def get_location_id(city_name, qkey):
    url = f"https://geoapi.qweather.com/v2/city/lookup?location={city_name}&key={qkey}"
    resp = requests.get(url).json()
    if resp["code"] == "200" and len(resp["location"]) > 0:
        return resp["location"][0]["id"], resp["location"][0]["name"]
    return None, city_name


def get_weather(location_id, qkey):
    url = f"https://devapi.qweather.com/v7/weather/now?location={location_id}&key={qkey}"
    resp = requests.get(url).json()
    if resp["code"] != "200":
        return {"text": "未知天气", "temp": "--", "tip": "今天也要好好照顾自己，不要太累啦"}
    now = resp["now"]
    weather_text = now["text"]
    temp = now["temp"]
    t = int(temp)
    if t < 8:
        tip = "外面很冷，记得穿厚外套，戴好围巾，别冻着啦"
    elif 8 <= t < 16:
        tip = "气温偏凉，随身带一件外套，降温了及时穿上"
    elif 16 <= t < 24:
        tip = "温度刚刚好，是舒服的一天，愿你事事顺心"
    elif 24 <= t < 30:
        tip = "天气暖暖的，记得多喝点温水"
    else:
        tip = "天气很热，做好防晒，不要中暑啦"
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
    # 每日简报固定带上一条热点
    r_bul = requests.get(f"https://apis.tianapi.com/bulletin/index?key={api_key}").json()
    if r_bul["code"] == 200 and len(r_bul["result"]["list"]) > 0:
        first = r_bul["result"]["list"][0]
        news_text = f"{first['title']}：{first['digest'][:45]}..."
    return say_text, news_text


def calc_love_days(start_date):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    now = datetime.now()
    delta = now - start
    return f"我们已经在一起 {delta.days} 天啦"


def send_template_msg():
    token = get_wx_access_token()
    loc_id, real_city = get_location_id(TARGET_CITY, QWEATHER_KEY)
    if loc_id is None:
        weather = {"text": "查询失败", "temp": "--", "tip": "城市查询出错啦，记得照顾好自己"}
    else:
        weather = get_weather(loc_id, QWEATHER_KEY)

    say_text, news_text = get_tian_content(TIANAPI_KEY, TIAN_TYPE)
    love_day_str = calc_love_days(LOVE_START_DATE)

    post_data = {
        "touser": OPENID,
        "template_id": TEMPLATE_ID,
        "data": {
            "date": {"value": datetime.now().strftime("%Y-%m-%d")},
            "city": {"value": real_city},
            "weather": {"value": weather["text"]},
            "temp": {"value": weather["temp"] + " ℃"},
            "tip": {"value": weather["tip"]},
            "love_day": {"value": love_day_str},
            "say": {"value": say_text},
            "news": {"value": news_text}
        }
    }
    url = "https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={}".format(token)
    result = requests.post(url, json=post_data).json()
    print("推送返回结果：", result)
    return result


if __name__ == "__main__":
    send_template_msg()
