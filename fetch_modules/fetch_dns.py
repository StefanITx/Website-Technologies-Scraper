from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, field

import dns.resolver
from config.models import DnsResult

resolver = dns.resolver.Resolver()
resolver.timeout = 1      # seconds per individual attempt
resolver.lifetime = 2     # total seconds across all retries before giving up

def fetch_name_servers(domain):
    result = []
    try:
        answers=resolver.resolve(domain, 'NS')
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return result
    except dns.exception.DNSException:
        return result
    for record in answers:
        result.append(str(record))
    return result

def fetch_mail_exchange_servers(domain):
    result = []
    try:
        answers=resolver.resolve(domain, 'MX')
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return result
    except dns.exception.DNSException:
        return result

    for record in answers:
        result.append(str(record.exchange))
    return result

def fetch_txt_records(domain):
    result = []
    try:
        answers=resolver.resolve(domain, 'TXT')
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return result
    except dns.exception.DNSException:
        return result
    for record in answers:
        for text in record.strings:
            result.append(text.decode())
    return result

def fetch_canonical_name(domain):
    result=[]
    try:
        answers=resolver.resolve(domain, 'CNAME')
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return result
    except dns.exception.DNSException:
        return result
    for record in answers:
        result.append(str(record))
    return result

def fetch_start_of_authority(domain):
    result=[]
    try:
        answers = resolver.resolve(domain, 'SOA')
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return result
    except dns.exception.DNSException:
        return result

    for record in answers:
        result.append(str(record.mname))
    return result

def dns_fetch(domain):
    with ThreadPoolExecutor(max_workers=5) as executor:
        name_servers_future = executor.submit(fetch_name_servers, domain)
        mail_exchange_servers_future = executor.submit(fetch_mail_exchange_servers, domain)
        txt_records_future = executor.submit(fetch_txt_records, domain)
        canonical_name_future = executor.submit(fetch_canonical_name, domain)
        start_of_authority_future = executor.submit(fetch_start_of_authority, domain)

        return DnsResult(
            domain,
            name_servers_future.result(),
            mail_exchange_servers_future.result(),
            txt_records_future.result(),
            canonical_name_future.result(),
            start_of_authority_future.result(),
        )

if __name__ == "__main__":
    mock_domain="szentkristofudvarhaz.hu"
    x=asdict(dns_fetch(mock_domain))
    print(x)
    for item in x.items():
        print(item)
