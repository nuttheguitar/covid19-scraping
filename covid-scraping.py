## Writer :  https://github.com/UncleEngineer/covid19/blob/master/covid19uncle/covid19.py

from urllib.request import urlopen as req
from bs4 import BeautifulSoup as soup
import pandas as pd
import schedule
import gspread
import gspread_dataframe
from oauth2client.service_account import ServiceAccountCredentials
import json
import time
import os 
import boto3
from botocore.exceptions import NoCredentialsError
import send_message

ACCESS_KEY = os.environ.get('access_key')
SECRET_KEY = os.environ.get('secret_key')
bucket_name = 'tmn-covid-19'

def upload_to_aws(local_file, bucket, s3_file):
    s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                      aws_secret_access_key=SECRET_KEY)

    try:
        s3.upload_file(local_file, bucket, s3_file)
        print("Upload Successful")
        return True
    except FileNotFoundError:
        print("The file was not found")
        return False
    except NoCredentialsError:
        print("Credentials not available")
        return False

def ThaiCovid19():
    url = 'https://ddc.moph.go.th/viralpneumonia/'

    webopen = req(url)
    page_html = webopen.read()
    webopen.close()

    data = soup(page_html, 'html.parser')

    alldata = []

    result = {}

    table = data.findAll('div', {'class':'popup_blog'})
    #print(table[0])
    for i, tb in enumerate(table):


        if i == 1:
            rw = tb.findAll('tr')
            for i in range(len(rw)):
                cl1 = [r.text for r in rw[i].findAll('td')]
                alldata.append(cl1)


        if i == 0:
            rw = tb.findAll('tr')
            for i in range(len(rw)):
                cl1 = [r.text for r in rw[i].findAll('td')]
                alldata.append(cl1)
            #print('-------')

    #print(alldata)
    # for i,d in enumerate(alldata):
    # 	print(i,d,'\n\n')

    result['lasted_updated'] = f'{alldata[0][0]} {alldata[12][0]}' # เวลาอัพเดตล่าสุด
    datetime_eng = result['lasted_updated']
    datetime_eng = datetime_eng.split(' ')

    if datetime_eng[2].startswith('มก'):
        datetime_eng[2] = '01'
    
    elif datetime_eng[2].startswith('กุม'):
        datetime_eng[2] = '02'

    elif datetime_eng[2].startswith('มี'):
        datetime_eng[2] = '03'
    
    elif datetime_eng[2].startswith('เมษ'):
        datetime_eng[2] = '04'

    elif datetime_eng[2].startswith('พฤษ'):
        datetime_eng[2] = '05'
    
    elif datetime_eng[2].startswith('มิถุ'):
        datetime_eng[2] = '06'
    
    elif datetime_eng[2].startswith('กรก'):
        datetime_eng[2] = '07'

    elif datetime_eng[2].startswith('สิงหา'):
        datetime_eng[2] = '08'
    
    elif datetime_eng[2].startswith('กันยา'):
        datetime_eng[2] = '09'
    
    elif datetime_eng[2].startswith('ตุลา'):
        datetime_eng[2] = '10'
    
    elif datetime_eng[2].startswith('พฤศ'):
        datetime_eng[2] = '11'
    
    elif datetime_eng[2].startswith('ธัน'):
        datetime_eng[2] = '12'

    result['lasted_updated'] = str(int(datetime_eng[3])-543)+'-'+datetime_eng[2]+'-'+datetime_eng[1]+' '+datetime_eng[5].replace('.', ':')
    result['total'] = int(alldata[3][0].replace(',', '')) # ผู้ป่วยสะสม
    result['new_cases'] = int(alldata[3][1].replace(',', '')) # ผู้ป่วยรายใหม่
    result['serious_critical'] = int(alldata[5][0].replace(',', '')) # ผู้ป่วยรุนแรง
    result['total_deaths'] = int(alldata[5][1].replace(',', '')) # ผู้ป่วยเสียชีวิต
    result['recoverd'] = int(alldata[5][2].replace(',', '')) # ผู้ป่วยกลับบ้านแล้ว
    result['total_active_cases'] = int(alldata[8][0].replace(',', '')) # ผู้ป่วยเฝ้าระวังสะสม
    result['new_active_cases'] = int(alldata[8][1].replace(',', '')) # ผู้ป่วยเฝ้าระวังรายใหม่
    result['recovering'] = int(int(result['total']) - (int(result['recoverd']) + int(result['total_deaths']))) # ผู้ป่วยกำลังรักษา
    result['in_hospital'] = int(alldata[11][0].replace(',', '')) # รักษาพยาบาลอยู่รพ
    result['back_home'] = int(alldata[11][1].replace(',', '')) # รักษาพยาบาลกลับบ้าน
    result['inspect_cases'] = int(alldata[11][2].replace(',', '')) # รักษาพยาบาลสังเกตอาการ

    for d in alldata[14:]:
        if d[0].startswith('สนาม'):
            d[0] = 'airport'
        elif d[0].startswith('ท่า'):
            d[0] = 'port'
        elif d[0].startswith('ด่าน'):
            d[0] = 'border'
        elif d[0].startswith('สตม'):
            d[0] = 'immigration_bureau_jaeng_wattana'

        result['total_traveler_from_'+d[0]] = int(d[1].replace(',', ''))

    result['Reference'] = url

    return result

def main():
    thai = ThaiCovid19()
    df = pd.DataFrame(thai, index=[0])

    scope = ['https://www.googleapis.com/auth/spreadsheets'] #ให้ทำการ auth scope เข้า sheet ครับ
    credentials = ServiceAccountCredentials.from_json_keyfile_name("./eighth-opus-237810-c056aa9b0bca.json", scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_url('https://docs.google.com/spreadsheets/d/1gkFP_xeW_Rsb348vthtWfytIOoC-mc9AgdPss6rwaAw/edit?usp=sharing')
    wks = sheet.get_worksheet(0) #wks = worksheet
    df2 = gspread_dataframe.get_as_dataframe(wks)
    df2 = df2.iloc[:, :17]
    
    if df.iloc[0, 0] != df2.iloc[0, 0]:
        print('New Data Updated')
        df2 = df.append(df2, ignore_index=True, sort=False)
        gspread_dataframe.set_with_dataframe(wks, df2)
        
        df_json = df.to_json('./covid19.json', orient='records')
        print('File Saved In Local')

        uploaded = upload_to_aws('./covid19.json', bucket_name, 'covid19.json')
        if uploaded:
            print('File Uploaded to S3 Success')
            send_message.send(message="Covid19 : File Uploaded to S3 Success" , spaces= 'spaces/AAAARA65rqo',thread = None)
        else:
            print('File Upload to S3 Failed')
            send_message.send(message="Covid19 : File Upload to S3 Failed" , spaces= 'spaces/AAAARA65rqo',thread = None)
    else:
        print('No Data Update')
        send_message.send(message="Covid19 : No Data Update" , spaces= 'spaces/AAAARA65rqo',thread = None)
        pass

if __name__ == '__main__':
    try:
        main()
    
    except:
        print('Something went wrong')
        send_message.send(message="Something Went Wrong in Covid19.py" , spaces= 'spaces/AAAARA65rqo',thread = None)