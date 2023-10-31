import base64
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import requests, json
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5


def encrpt(password, public_key):
    rsa = RSA.importKey(public_key)
    cipher = PKCS1_v1_5.new(rsa)
    return base64.b64encode(cipher.encrypt(password.encode())).decode()

def syncData(xingzhe_username, xingzhe_password, igp_username, igp_password):
    headers = {
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        "Accept-Encoding" : "gzip, deflate",
    }

    # login igpsport account
    url = "https://my.igpsport.com/Auth/Login"
    data = {
        'username': username, 
        'password': password, 
    }
    session = requests.session()
    res     = session.post(url, data, headers=headers)

    # get igpsport list
    url = "https://my.igpsport.com/Activity/ActivityList"
    res     = session.get(url)
    result  = json.loads(res.text, strict=False)

    activities   = result["item"]

    # login xingzhe account
    url     = "https://www.imxingzhe.com/user/login"
    res     = session.get(url, headers=headers) # need flush cookie
    cookie  = session.cookies.get_dict()
    rd      = cookie['rd']

    safe_password           = password + ';' + rd
    encrypter_public_key    = "-----BEGIN PUBLIC KEY-----\nMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDmuQkBbijudDAJgfffDeeIButq\nWHZvUwcRuvWdg89393FSdz3IJUHc0rgI/S3WuU8N0VePJLmVAZtCOK4qe4FY/eKm\nWpJmn7JfXB4HTMWjPVoyRZmSYjW4L8GrWmh51Qj7DwpTADadF3aq04o+s1b8LXJa\n8r6+TIqqL5WUHtRqmQIDAQAB\n-----END PUBLIC KEY-----\n"
    safe_password           = encrpt(safe_password, encrypter_public_key)
    
    url     = "https://www.imxingzhe.com/api/v4/account/login"
    data    = {
        'account': username, 
        'password': safe_password, 
        "source": "web"
    }
    res     = session.post(url, json.dumps(data), headers=headers)

    # get user info 
    url     = "https://www.imxingzhe.com/api/v4/account/get_user_info/"
    res     = session.get(url, headers=headers)
    result  = json.loads(res.text, strict=False)
    userId  = result["userid"]

    # get current month data
    url     = "https://www.imxingzhe.com/api/v4/user_month_info/?user_id="+str(userId)
    res     = session.get(url, headers=headers)
    result  = json.loads(res.text, strict=False)
    data  = result["data"]["wo_info"]

    sync_data = []
    # get not upload activity
    for activity in activities:
        timezone  = ZoneInfo('Asia/Shanghai') # to Shanghai timezero in Gtihub Action env
        dt        = datetime.strptime(activity["StartTime"], "%Y-%m-%d %H:%M:%S")
        dt2       = datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, tzinfo=timezone)
        s_time    = dt2.timestamp()
        mk_time   = int(s_time) * 1000
        need_sync = True

        for item in data:
            if item["start_time"] == mk_time:
                need_sync = False
                break
        if need_sync:
            sync_data.append(activity)

    if len(sync_data) == 0:

        print("nothing data need sync")

    else:

        #down file
        upload_url = "https://www.imxingzhe.com/api/v4/upload_fits"
        for sync_item in sync_data:
            rid     = sync_item["RideId"]
            rid     = str(rid)

            print("sync rid:" + rid)

            fit_url = "https://my.igpsport.com/fit/activity?type=0&rideid="+rid
            res     = session.get(fit_url)
            result = session.post(upload_url, files={
                "title": (None, 'IGPSPORT-'+sync_item["StartTime"], None),
                "device": (None, 3, None), #IGPS
                "sport": (None, 3, None), #骑行
                "upload_file_name": (sync_item["StartTime"]+'.fit', res.content, 'application/octet-stream')
            })


activity = syncData(os.getenv("XINGZHE_USERNAME"), os.getenv("XINGZHE_PASSWORD"), os.getenv("IGP_USERNAME"), os.getenv("IGP_PASSWORD"))
