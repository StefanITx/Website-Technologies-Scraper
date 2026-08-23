from dataclasses import dataclass


@dataclass
class Evidence:
    source:str
    contains:str
    confidence:float


@dataclass
class MatchResult:
    technology:str
    category:str
    evidence:list[Evidence]
    final_confidence:float

@dataclass
class FetchHttpResult:
    domain_name:str
    status_code:int | None = None
    status:str | None = None
    hasResponse:bool | None = None
    response_text:str | None = None
    headers:dict | None = None
    cookies:dict | None = None
    final_url:str | None = None

@dataclass
class DnsResult:
    domain_name: str
    name_servers: list[str]
    mail_exchange_servers: list[str]
    txt_records: list[str]
    canonical_name: list[str]
    start_of_authority:list[str]
