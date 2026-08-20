import json

import pandas as pd
from fetch_modules.fetch_httpRequests import http_fetch
from detector import signature_matches
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

final_result=[]

df=pd.read_parquet("domains.snappy.parquet", columns=["root_domain"])
list_of_domains=df["root_domain"].astype(str).tolist()

def append_to_final(domain):
    domain_result=http_fetch(domain)
    result={}
    result["domain_name"]=domain_result.domain_name
    result["status_code"]=domain_result.status_code
    result["status"]=domain_result.status
    result["hasResponse"]=domain_result.hasResponse
    result["final_url"]=domain_result.final_url
    if domain_result.hasResponse is False:
        result["technologies"]=[]
    else:
        matches=signature_matches(domain_result.response_text, domain_result.headers, domain_result.cookies)
        result["technologies"]=matches
    #print(result)
    final_result.append(result)

#for domain in list_of_domains:
#    append_to_final(domain)

with ThreadPoolExecutor(max_workers=10) as executor:
    executor_map=list(executor.map(append_to_final, list_of_domains))  

with open('results.json', 'w', encoding='utf-8') as file:
    json.dump(final_result, file,indent=2)

'''
domain_1=http_fetch(list_of_domains[1])

print(f"Domain: {domain_1.domain_name}")
x=signature_matches(domain_1.response_text, domain_1.headers, domain_1.cookies)
for match in x:
    print(f"Match found: {match}")

'''