import json

import pandas as pd
from fetch_modules.fetch_httpRequests import http_fetch
from fetch_modules.fetch_dns import dns_fetch
from detector import signature_matches
from concurrent.futures import ThreadPoolExecutor

final_result=[]


df=pd.read_parquet("domains.snappy.parquet", columns=["root_domain"])
list_of_domains=df["root_domain"].astype(str).tolist()

def append_to_final(domain):
    domain_result=http_fetch(domain)
    dns_result=dns_fetch(domain)
    result={}
    result["domain_name"]=domain_result.domain_name
    result["status_code"]=domain_result.status_code
    result["status"]=domain_result.status
    result["hasResponse"]=domain_result.hasResponse
    result["final_url"]=domain_result.final_url
    if domain_result.hasResponse is False:
        result["technologies"]=[]
    else:
        matches=signature_matches(domain_result.response_text, domain_result.headers, domain_result.cookies,dns_result)
        result["technologies"]=matches
    #print(result)
    final_result.append(result)

#for domain in list_of_domains:
#    append_to_final(domain)

with ThreadPoolExecutor(max_workers=10) as executor:
    executor_map=list(executor.map(append_to_final, list_of_domains))  

with open('results.json', 'w', encoding='utf-8') as file:
    technology_name_to_count = {'Comment':'Stats','Number of technologies found': 0,
                                'Listing':'Technology/Number of evidences'}

    for item in final_result:
        technology_entries = item.get("technologies", [])

        for technology_entry in technology_entries:
            technology_name = technology_entry["technology"]

            if technology_name in technology_name_to_count:
                technology_name_to_count[technology_name] += 1
            else:
                technology_name_to_count[technology_name] = 1
        technology_name_to_count['Number of technologies found'] = len(technology_name_to_count)
    print(f'{technology_name_to_count['Number of technologies found']} technologies found! \n')
    for x, y in technology_name_to_count.items():
        print(f'{x}: {y}')
    json.dump(final_result, file,indent=2)
