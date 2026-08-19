import pandas as pd
from fetch_modules.fetch_httpRequests import http_fetch
from detector import signature_matches


df=pd.read_parquet("domains.snappy.parquet", columns=["root_domain"])
list_of_domains=df["root_domain"].astype(str).tolist()

for domain in list_of_domains:
    domain_result=http_fetch(domain)
    print(f"Domain: {domain_result.domain_name}")
    print(f"Status Code: {domain_result.status_code}")
    print(f"Status: {domain_result.status}")
    print(f"Final URL: {domain_result.final_url}")
    print(f"Has Response: {domain_result.hasResponse}")
    if domain_result.hasResponse is False:
        print("Request failed.\n")
        continue
    matches=signature_matches(domain_result.response_text, domain_result.headers)
    if not matches:
        print("No matches found.")
    for match in matches:
        print(f"Match found: {match}")
    print("\n")


'''
domain_1=http_fetch(list_of_domains[1])

print(f"Domain: {domain_1.domain_name}")
x=signature_matches(domain_1.response_text, domain_1.headers)
for match in x:
    print(f"Match found: {match}")

'''