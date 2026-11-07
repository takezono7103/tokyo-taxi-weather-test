#!/usr/bin/env python3
"""GitHub Actions only. Read secret from env. Publish compact public forecast, never secret."""
import datetime as dt
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen

STATIONS = [
    ('shinagawa','品川',35.6289,139.7388),
    ('hamamatsucho','浜松町',35.6553,139.7571),
    ('shimbashi','新橋',35.6650,139.7597),
    ('shibuya','渋谷',35.6580,139.7016),
    ('shinjuku','新宿',35.6909,139.7003),
    ('tokyo','東京駅',35.6812,139.7671),
    ('haneda','羽田',35.5488,139.7544),
    ('ikebukuro','池袋',35.7295,139.7109),
]
BASE='https://api.openweathermap.org/data/4.0/onecall/timeline/1h'

def normalize_item(row):
    if not isinstance(row,dict) or not isinstance(row.get('dt'),(int,float)):return None
    pop=row.get('pop'); rain=row.get('rain') or {}
    if not isinstance(rain,dict):rain={}
    rainmm=rain.get('1h'); temp=row.get('temp')
    return {'t':int(row['dt']), 'pop':round(float(pop),4) if isinstance(pop,(int,float)) and 0<=pop<=1 else None,
       'rain_mm':round(float(rainmm),2) if isinstance(rainmm,(int,float)) and rainmm>=0 else None,
       'temp_c':round(float(temp),1) if isinstance(temp,(int,float)) else None}

def fetch(lat,lon,key):
    params=urlencode({'lat':lat,'lon':lon,'units':'metric','lang':'ja','appid':key})
    req=Request(BASE+'?'+params,headers={'User-Agent':'TokyoTaxiWeather/1.0'})
    # Never print urllib exceptions (they may contain the secret in URL).
    with urlopen(req,timeout=25) as res:
        content=res.read(500_000)
    body=json.loads(content)
    now=dt.datetime.now(dt.timezone.utc).timestamp()
    rows=[normalize_item(x) for x in body.get('data',[])];rows=[x for x in rows if x and now-3600<=x['t']<=now+8*3600]
    rows.sort(key=lambda x:x['t'])
    if not rows: raise ValueError('No near-term hourly data')
    return rows

def main():
    key=os.environ.get('OPENWEATHER_API_KEY','').strip()
    if not key:raise SystemExit('Missing GitHub secret OPENWEATHER_API_KEY')
    stations=[];errors=[]
    for id,name,lat,lon in STATIONS:
        try:
            rows=fetch(lat,lon,key)
            stations.append({'id':id,'name':name,'lat':lat,'lon':lon,'hourly':rows})
            print(f'{name}: {len(rows)} records')
        except Exception:
            errors.append(name)
            print(f'{name}: API error (details intentionally hidden)')
    # Never replace a good published file with empty/partial data.
    if errors or len(stations)!=len(STATIONS): raise SystemExit('Weather refresh failed; existing published file retained')
    output={'schema':1,'source':'OpenWeather One Call API 4.0 hourly',
      'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
      'stations':stations}
    path=Path('data/weather_latest.json');path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(output,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf8')

if __name__=='__main__':main()
