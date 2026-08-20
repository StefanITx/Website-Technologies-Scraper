from dataclasses import dataclass


@dataclass
class Evidence:
    source:str
    contains:str
    confidence:float


@dataclass
class Match_Result:
    technology:str
    category:str
    evidence:list[Evidence]
    final_confidence:float

@dataclass
class FetchResult:
    domain_name:str
    status_code:int | None = None
    status:str | None = None
    hasResponse:bool | None = None
    response_text:str | None = None
    headers:dict | None = None
    cookies:dict | None = None
    final_url:str | None = None