"""Canonical browse specifications and facets. Unknown specifications stay absent.

Normalize once on the server from structured fields and explicit retailer specs;
never infer a missing feature from price, marketing tier or absence of a keyword.
"""
import re
from functools import lru_cache
from collections import Counter
from product_metadata import gpu_search_metadata, parse_ram_metadata, capacity_mb_from_text, gpu_series_key

BRANDS = {
 'ASUS':r'asus|에이수스|아수스', 'MSI':r'\bmsi\b', 'GIGABYTE':r'gigabyte|기가바이트',
 'ASRock':r'asrock|애즈락', 'BIOSTAR':r'biostar|바이오스타', 'Samsung':r'samsung|삼성',
 'SK hynix':r'sk\s*하이닉스|sk\s*hynix', 'Micron':r'micron|crucial|마이크론',
 'G.SKILL':r'g[.]?skill|지스킬', 'CORSAIR':r'corsair|커세어', 'TeamGroup':r'teamgroup|팀그룹',
 'ESSENCORE':r'essen core|essencore|klevv|클레브', 'Kingston':r'kingston|킹스톤',
 'Western Digital':r'western digital|\bwd\b|웨스턴디지털', 'Seagate':r'seagate|씨게이트',
 'Toshiba':r'toshiba|도시바', 'Synology':r'synology|시놀로지',
 'Micronics':r'micronics|마이크로닉스', 'Seasonic':r'seasonic|시소닉',
 'FSP':r'\bfsp\b', 'SuperFlower':r'super\s*flower|슈퍼플라워',
 'SAPPHIRE':r'sapphire|사파이어', 'PowerColor':r'powercolor|파워컬러', 'XFX':r'\bxfx\b',
 'Transcend':r'transcend|트랜센드', 'KIOXIA':r'kioxia|키오시아', 'SanDisk':r'sandisk|샌디스크', 'ABKO':r'abko|앱코', 'LIAN LI':r'lian[- ]?li|리안리', 'BIWIN':r'biwin', 'ZOTAC':r'zotac|조텍', 'PALIT':r'palit|팰릿', 'Lexar':r'lexar|렉사',
}
FIELDS = {
 'cpu': [('platform','CPU 제조사'),('cpu_family','제품군'),('generation','세대'),('socket','CPU 소켓'),('memory_type','지원 메모리'),('cores','코어 수'),('threads','스레드 수')],
 'mb': [('manufacturer','제조사'),('platform','CPU 플랫폼'),('socket','CPU 소켓'),('chipset','칩셋'),('memory_type','메모리 규격'),('form_factor','보드 크기'),('pcie_x16','그래픽카드 슬롯')],
 'ram': [('manufacturer','제조사'),('usage','사용 대상'),('memory_type','메모리 규격'),('capacity_gb','총 용량'),('kit','메모리 구성'),('speed','동작 속도'),('cl','CAS 지연'),('voltage','전압'),('color','색상'),('led','LED / RGB')],
 'gpu': [('gpu_vendor','GPU 칩 제조사'),('series','GPU 시리즈'),('chipset','GPU 칩셋'),('manufacturer','그래픽카드 브랜드'),('vram_gb','VRAM')],
 'storage': [('manufacturer','제조사'),('form_factor','크기 / 형태'),('interface','인터페이스'),('protocol','프로토콜'),('capacity_gb','용량'),('nand','NAND 유형'),('nand_structure','NAND 구조'),('dram','DRAM 캐시'),('read_range','순차 읽기 · MB/s'),('write_range','순차 쓰기 · MB/s')],
 'psu': [('manufacturer','제조사'),('form_factor','파워 규격'),('watt_range','정격 출력'),('rating','80 PLUS 인증'),('modular','케이블 연결'),('atx_version','ATX 버전'),('connector','GPU 전원 단자')],
 'hdd': [('manufacturer','제조사'),('usage','사용 용도'),('form_factor','크기'),('capacity_gb','용량'),('interface','인터페이스'),('rpm','회전수'),('cache_mb','캐시')],
}
LABELS = {'Intel':'Intel CPU용','AMD':'AMD CPU용','Desktop':'데스크톱','Laptop':'노트북','Server':'서버','NAS':'NAS','Surveillance':'감시·녹화','Enterprise':'기업용', 'Full':'풀모듈러','Semi':'세미모듈러','Fixed':'고정 케이블','yes':'포함','no':'없음','White':'화이트','Black':'블랙','Silver':'실버','Red':'레드', '2.5-inch':'2.5인치','3.5-inch':'3.5인치','AIC':'PCIe 카드'}
SPEED_RANGES = [(1,599,'600 미만'),(600,2999,'600–2,999'),(3000,6999,'3,000–6,999'),(7000,9999,'7,000–9,999'),(10000,999999,'10,000 이상')]
WATT_RANGES = [(1,499,'500W 미만'),(500,599,'500–599W'),(600,699,'600–699W'),(700,799,'700–799W'),(800,899,'800–899W'),(900,999,'900–999W'),(1000,1299,'1000–1299W'),(1300,99999,'1300W 이상')]

def first(pattern, text, group=1):
    m = re.search(pattern, str(text or ''), re.I)
    return m.group(group) if m else ''

def number(v):
    try: return float(str(v).replace(',',''))
    except (ValueError, TypeError): return 0

def bucket(value, ranges):
    return next((label for lo,hi,label in ranges if lo <= number(value) <= hi),'')

def normalize_specs(item, kind):
    # Cached by immutable source fields, not mutable prices/images.
    keys = ('product_name','name','spec_text','manufacturer','brand','socket','cpu_socket','ram_type','type','cores','threads','gb','speed','vram','chipset','gpu_model','model','series','capacity','rpm','watt','rating','efficiency','modular','form_factor','read_speed','write_speed','color','led','rgb','atx_version','memory_type','voltage','cl')
    return dict(_normalize(kind, tuple((k,str(item[k])) for k in keys if item.get(k) not in (None,''))))

@lru_cache(maxsize=24000)
def _normalize(kind, source):
    p = dict(source); name = p.get('product_name') or p.get('name',''); spec = p.get('spec_text','')
    text = name + ' / ' + spec; d = {}
    # Retail product name is SKU-specific; detailed spec can describe grouped variants.
    brand_text = (p.get('manufacturer') or '') + ' ' + name
    d['manufacturer'] = next((b for b,pat in BRANDS.items() if re.search(pat, brand_text,re.I)), '')
    if not d['manufacturer']:
        candidate = (p.get('manufacturer') or p.get('brand') or '').strip('[] ')
        # Legacy imports sometimes put a chipset or CPU platform in `brand`.
        d['manufacturer'] = candidate if candidate not in ('-', 'AMD','Intel','NVIDIA') and not re.fullmatch(r'[ABHXZ]\d{3}[EM]?',candidate,re.I) else ''
    socket = first(r'(LGA[ -]*\d{3,4}|AM[345]\+?|sTR5|sTRX4|TR4|FM[12]\+?)(?![a-z0-9])',spec) or first(r'소켓\s*(\d{3,4})',spec)
    socket = socket or p.get('socket') or p.get('cpu_socket') or first(r'\b(LGA[ -]*\d{3,4}|AM[345]\+?|sTR5|sTRX4|TR4)(?![a-z0-9])',name)
    if socket:
        socket = re.sub(r'[ -]','',socket).upper(); socket = 'LGA'+socket if socket.isdigit() else socket
        if re.fullmatch(r'LGA\d{3,4}|AM[345]\+?|STR5|STRX4|TR4|FM[12]\+?',socket): d['socket']=socket
    memory = re.findall(r'\bDDR\s*([345])\b', spec,re.I) or re.findall(r'\bDDR\s*([345])\b', name,re.I)
    if not memory: memory = re.findall(r'DDR\s*([345])',p.get('memory_type') or p.get('ram_type') or p.get('type',''),re.I)
    if memory: d['memory_type'] = tuple(dict.fromkeys('DDR'+m for m in memory))
    if kind in ('cpu','mb'):
        d['platform'] = 'AMD' if re.match(r'AM|STR|TR|FM',d.get('socket','')) else 'Intel' if d.get('socket','').startswith('LGA') else 'AMD' if re.search(r'\bAMD\b|라이젠|ryzen',text,re.I) else 'Intel' if re.search(r'intel|인텔',text,re.I) else ''
    if kind == 'cpu':
        family = first(r'(?:core|코어)\s*(ultra|울트라)',name)
        tier = first(r'\bi([3579])(?=\b|-?\d{4,5})',name) or first(r'코어\s*i([3579])',name)
        ryzen = first(r'(?:ryzen|라이젠)\s*([3579])',name)
        d['cpu_family'] = 'Core Ultra' if family else 'Core i'+tier if tier else 'Ryzen '+ryzen if ryzen else ''
        intel_gen = first(r'(1[0-9])세대',text) or first(r'\bi[3579][- ]*(1[0-9])\d{3}',name)
        ryzen_gen = first(r'(?:ryzen|라이젠)\s*[3579][^/]*?\b([35789])\d{3}[a-z0-9]*\b',name)
        d['generation'] = 'Intel '+intel_gen if intel_gen else 'Ryzen '+ryzen_gen+'000' if ryzen_gen else ''
        for field,ko,en in [('cores','코어','cores?'),('threads','스레드','threads?')]:
            d[field] = first(r'(\d+)\s*(?:'+ko+'|'+en+r')\b',text) or p.get(field,'')
    elif kind == 'mb':
        d['chipset'] = p.get('chipset') or first(r'\b((?:Z|B|H|X|A|TRX|WRX)\d{3}E?)(?=[M\s/(-]|$)',text)
        d['form_factor'] = board_form(p.get('form_factor','')+' / '+text)
        # A storage PCIe generation must never be mistaken for an x16 slot.
        d['pcie_x16'] = first(r'PCIe\s*([345])\.0\s*[x×]16',text)
        if d['pcie_x16']: d['pcie_x16'] = f"PCIe {d['pcie_x16']}.0 x16"
    elif kind == 'gpu':
        g = gpu_search_metadata(p)
        d.update(gpu_vendor=g.get('vendor',''),series=g.get('series',''),chipset=g.get('chipset',''),vram_gb=p.get('vram') or first(r'(\d+)\s*GB',name))
        if g.get('manufacturer'): d['manufacturer'] = next((b for b in BRANDS if b.lower()==g['manufacturer']),g['manufacturer'].upper())
    elif kind == 'ram':
        parsed = parse_ram_metadata(name)
        d['capacity_gb'] = parsed.get('gb') or p.get('gb') or single_capacity(spec)
        kit = re.search(r'(\d+)\s*GB\s*[x×*]\s*(\d+)',text,re.I)
        if kit:
            size,count=map(int,kit.groups()); d['capacity_gb']=size*count; d['kit']=f'{size}GB × {count}'
        else:
            count = first(r'램개수\s*[:：]?\s*(\d+)\s*개',spec) or first(r'\b(\d+)\s*개',spec)
            if count and number(d.get('capacity_gb')) and number(d['capacity_gb']) % int(count)==0:
                d['kit']=f'{int(number(d["capacity_gb"])/int(count))}GB × {count}'
        d['speed'] = parsed.get('speed') or first(r'(\d{4,5})\s*(?:MHz|MT/s)',text) or p.get('speed','')
        d['cl'] = first(r'\bCL\s*(\d{2,3})\b',text) or p.get('cl','')
        d['voltage'] = first(r'\b(1\.\d{1,2})\s*V\b',text) or p.get('voltage','')
        d['usage'] = 'Server' if re.search(r'서버용|server|ECC|RDIMM',text,re.I) else 'Laptop' if re.search(r'노트북|laptop|SO[- ]?DIMM',text,re.I) else 'Desktop' if re.search(r'데스크탑|데스크톱|PC용|desktop|UDIMM',text,re.I) else ''
        d['color'] = next((c for c,pat in [('White','white|화이트'),('Black','black|블랙'),('Silver','silver|실버'),('Red','red|레드')] if re.search(pat,name+' '+p.get('color','')+' '+first(r'색상\s*:\s*([^/]+)',spec),re.I)), '')
        d['led'] = 'no' if re.search(r'(?:LED|RGB)\s*[:：]?\s*(?:없음|미지원|미포함)|non[- ]?rgb',text,re.I) or p.get('led','').lower()=='false' else 'yes' if re.search(r'\b(?:ARGB|RGB|LED)\b',text,re.I) or p.get('led','').lower()=='true' else ''
    elif kind in ('storage','hdd'):
        d['capacity_gb'] = capacity_mb_from_text(name) or p.get('capacity') or single_capacity(spec)
        d['form_factor'] = first(r'\b(2\.5|3\.5)\s*(?:인치|inch|형|["”])',text)
        if d['form_factor']: d['form_factor'] += '-inch'
        d['interface'] = 'SAS' if re.search(r'\bSAS\b',text,re.I) else 'SATA III' if re.search(r'\bSATA\s*(?:3|III|6)',text,re.I) else ''
        if kind == 'storage':
            if re.search(r'M\.?2\b',text,re.I):
                size=first(r'\b(2230|2242|2260|2280|22110)\b',text); d['form_factor']='M.2'+(' '+size if size else '')
            elif re.search(r'\bAIC|HHHL\b',text,re.I): d['form_factor']='AIC'
            lanes = first(r'PCI[- ]?e\s*(?:Gen)?\s*([345])(?:\.0)?\s*[x×]\s*4',text)
            if lanes: d['interface']=f'PCIe {lanes}.0 x4'
            protocol=first(r'NVMe\s*([12]\.\d)',text)
            d['protocol']=('NVMe '+protocol) if protocol else 'NVMe' if re.search(r'NVMe',text,re.I) else ''
            d['nand']=first(r'\b(TLC|QLC|MLC|SLC)\b',text).upper()
            d['nand_structure']=first(r'\b([23]D)\s*(?:NAND|낸드)',text).upper()
            d['dram']='no' if re.search(r'DRAM\s*(?:미탑재|없음|리스|less)|DRAM[- ]?less',text,re.I) else 'yes' if re.search(r'DRAM\s*(?:탑재|캐시\s*있음)|DDR[34]\s*캐시',text,re.I) else ''
            for key,term in [('read','읽기|read'),('write','쓰기|write')]:
                match = re.search(r'(?:'+term+r')\s*(?:속도)?\s*[:：]?\s*(?:최대)?\s*([\d,.]+)\s*(GB/s|MB/s|M)(?=\b|/|\s|$)',text,re.I)
                speed=number(p.get(key+'_speed')) or (number(match[1])*(1000 if match[2].lower()=='gb/s' else 1) if match else 0)
                d[key+'_speed']=speed; d[key+'_range']=bucket(speed,SPEED_RANGES)
        else:
            d['usage']=next((v for v,pat in [('NAS',r'\bNAS(?:용|\b)'),('Surveillance','감시|녹화|surveillance'),('Enterprise','기업용|enterprise'),('Laptop','노트북|laptop'),('Desktop','데스크탑|데스크톱|PC용|desktop')] if re.search(pat,text,re.I)),'')
            d['rpm']=first(r'([\d,]{4,6})\s*RPM',text).replace(',','') or p.get('rpm','')
            d['cache_mb']=first(r'(\d+)\s*MB\s*(?:캐시|cache)',text) or first(r'(?:캐시|cache)\s*[:：]?\s*(\d+)\s*MB',text)
    elif kind == 'psu':
        watts=first(r'\b(\d{3,4})\s*W\b',name) or first(r'정격\s*출력\s*[:：]?\s*(\d{3,4})\s*W',spec) or p.get('watt','')
        d['watt']=watts; d['watt_range']=bucket(watts,WATT_RANGES)
        cert=first(r'80\s*(?:PLUS|\+)\s*([^/]+)',spec) or first(r'80\s*(?:PLUS|\+)\s*([^/]+)',name) or p.get('rating','')
        d['rating']=next((v for v,pat in [('Titanium','titanium|티타늄'),('Platinum','platinum|플래티넘|플래티늄'),('Gold','gold|골드'),('Silver','silver|실버'),('Bronze','bronze|브론즈'),('Standard','standard|스탠다드|스탠더드|white')] if re.search(pat,cert,re.I)),'')
        d['modular']='Semi' if re.search(r'semi|세미',text,re.I) else 'Fixed' if re.search(r'non[- ]?modular|고정|일체형',text,re.I) else 'Full' if re.search(r'full[- ]?modular|풀\s*모듈러',text,re.I) else p.get('modular','')
        d['atx_version']=first(r'ATX\s*(3\.[01]|2\.\d+)',text) or p.get('atx_version','')
        d['form_factor']='Server' if '서버용' in text else 'SFX-L' if re.search(r'SFX[- ]?L',text,re.I) else first(r'\b(SFX|TFX|ATX)\b',text).upper()
        d['connector']=tuple(v for v,pat in [('12V-2x6',r'12V[- ]?2[x×]6'),('12VHPWR',r'12VHPWR')] if re.search(pat,text,re.I))
    return tuple((k, str(int(v)) if isinstance(v,(int,float)) and float(v).is_integer() else v) for k,v in d.items() if v not in ('',None,(),0))

def single_capacity(spec):
    # Multiple capacities in a grouped description are ambiguous.
    values=set(re.findall(r'\b(\d+(?:\.\d+)?)\s*(GB|TB)\b',spec,re.I))
    if len(values) != 1: return None
    n,unit=next(iter(values))
    return int(float(n)*(1000 if unit.upper()=='TB' else 1))

def board_form(text):
    return next((v for v,pat in [('E-ATX',r'\bE[- ]?ATX\b'),('M-ATX',r'\b(?:M[- ]?ATX|micro[- ]?ATX)\b'),('Mini-ITX',r'\b(?:mini|M)[- ]?ITX\b'),('ATX',r'\bATX\b')] if re.search(pat,text,re.I)),'')

def clean_filters(kind, filters):
    allowed={k for k,_ in FIELDS.get(kind,[])}
    result = {k:sorted(set(str(v)[:80] for v in (values if isinstance(values,list) else str(values).split(',')) if str(v)))[:20]
              for k,values in (filters or {}).items() if k in allowed and values}
    if 'series' in result: result['series']=[gpu_series_key(v) or v for v in result['series']]
    if 'chipset' in result and kind=='gpu': result['chipset']=[gpu_search_metadata({'chipset':v}).get('chipset',v) for v in result['chipset']]
    return result

def matches_specs(specs, filters):
    for key, values in filters.items():
        actual=specs.get(key,())
        actual=actual if isinstance(actual,(tuple,list)) else [actual]
        if key=='protocol' and 'NVMe' in values and any(str(v).startswith('NVMe') for v in actual): continue
        if not set(map(str,actual)).intersection(values): return False
    return True

def enrich(item, kind):
    return {**item, 'specs':normalize_specs(item,kind)}

def option_label(key, value):
    if key in ('capacity_gb','vram_gb'):
        n=number(value); return f'{n/1000:g}TB' if n>=1000 else f'{n:g}GB'
    if key=='generation' and str(value).startswith('Intel '): return str(value)+'세대'
    if key=='platform': return LABELS.get(value,str(value))
    if key in ('manufacturer','gpu_vendor'): return str(value)
    if key=='speed': return f'{value}MT/s'
    if key=='cl': return 'CL'+str(value)
    if key=='voltage': return str(value)+'V'
    if key=='rpm': return str(value)+' RPM'
    if key=='cache_mb': return str(value)+'MB'
    if key=='cores': return str(value)+'코어'
    if key=='threads': return str(value)+'스레드'
    return LABELS.get(value,str(value))

def facets(kind, rows, selected=None):
    selected=selected or {}; normalized=[r.get('specs') or normalize_specs(r,kind) for r in rows]
    result=[]
    priority=['AM5','LGA1851','LGA1700','AM4','DDR5','DDR4','Intel','AMD','B850','B650','B760','B860','Z890','X870','32','16','64','2000','1000']
    for key,label in FIELDS.get(kind,[]):
        candidates=normalized
        if kind=='mb' and key=='chipset':
            dependencies={k:v for k,v in selected.items() if k in ('socket','platform')}
            candidates=[s for s in normalized if matches_specs(s,dependencies)]
        counts=Counter()
        for s in candidates:
            values=s.get(key,()); values=values if isinstance(values,(tuple,list)) else [values]
            counts.update(str(v) for v in set(values) if v not in ('',None))
        for v in selected.get(key,[]): counts.setdefault(v,0)
        if not counts: continue
        preferred = {
            'cpu_family':['Core Ultra','Core i5','Core i7','Core i9','Ryzen 5','Ryzen 7','Ryzen 9'],
            'generation':['Intel 14','Intel 13','Intel 12','Ryzen 9000','Ryzen 8000','Ryzen 7000','Ryzen 5000'],
            'cores':['6','8','12','14','16','24'], 'threads':['12','16','20','24','28','32'],
            'speed':['6000','5600','6400','7200','3600','3200'],
            'manufacturer':['ASUS','MSI','GIGABYTE','ASRock','Samsung','SK hynix','Micron','Seagate','Western Digital'],
        }.get(key, priority)
        order=sorted(counts, key=lambda v:(preferred.index(v) if v in preferred else 100, -counts[v],v))
        result.append({'key':key,'label':label,'options':[[v,option_label(key,v)] for v in order], 'counts':dict(counts)})
    return result
