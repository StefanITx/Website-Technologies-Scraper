import requests
from config.static import HEADERS, TIMEOUT
from config.models import FetchResult

def http_fetch(domain, headers=HEADERS, timeout=TIMEOUT):
    https_url = f"https://{domain}"
    http_url = f"http://{domain}"
    last_failure_status = "Unreachable"

    for attempt_url in (https_url, http_url):
        try:
            response = requests.get(attempt_url, headers=headers, timeout=timeout)
        except requests.exceptions.Timeout:
            last_failure_status = "Connection Timeout"
            if attempt_url == http_url:
                return FetchResult(domain_name=domain, hasResponse=False, status="Connection Timeout")
            continue
        except requests.exceptions.SSLError:
            last_failure_status = "SSL Error"
            if attempt_url == http_url:
                return FetchResult(domain_name=domain, hasResponse=False, status="SSL Error")
            continue
        except requests.exceptions.ConnectionError:
            last_failure_status = "Connection Error"
            if attempt_url == http_url:
                return FetchResult(domain_name=domain, hasResponse=False, status="Connection Error")
            continue
        except requests.exceptions.TooManyRedirects:
            return FetchResult(domain_name=domain, hasResponse=False, status="Too Many Redirects")
        except requests.exceptions.RequestException as e:
            return FetchResult(domain_name=domain, hasResponse=False, status=f"Request Exception: {str(e)}")

        status = "Success" if response.ok else "Failed"
        normalized_headers={key.lower():value for key,value in response.headers.items()}
        return FetchResult(
            domain_name=domain,
            status_code=response.status_code,
            status=status,
            hasResponse=True,
            response_text=response.text,
            headers=normalized_headers,
            cookies=dict(response.cookies),
            final_url=response.url,
        )
    return FetchResult(domain_name=domain, hasResponse=False, status=last_failure_status)