"""
LLM Navigator Backend - Vercel Serverless
FastAPI + Supabase REST API (httpx)
"""

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import httpx

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

app = FastAPI(
    title="LLM Navigator API",
    description="LLM 模型选型 + 金融数据 API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================
# Supabase REST 客户端
# ========================

def sb_headers() -> Dict[str, str]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("请在环境变量中设置 SUPABASE_URL 和 SUPABASE_KEY")
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


async def sb_get(table: str, params: Optional[Dict[str, str]] = None) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = sb_headers()
    headers.pop("Prefer", None)
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers, params=params or {})
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()


async def sb_insert(table: str, data) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=sb_headers(), json=data)
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json() if r.text else []


async def sb_update(table: str, data, params: Dict[str, str]) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    async with httpx.AsyncClient() as client:
        r = await client.patch(url, headers=sb_headers(), json=data, params=params)
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json() if r.text else []


async def sb_delete(table: str, params: Dict[str, str]) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    h = sb_headers()
    h.pop("Prefer", None)
    async with httpx.AsyncClient() as client:
        r = await client.delete(url, headers=h, params=params)
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json() if r.text else []


# ========================
# Pydantic Models
# ========================

class ModelCreate(BaseModel):
    id: str
    name: str
    vendor: str
    vendor_color: str = "gray"
    score: int
    price_per_m: float
    context: str
    params: str = ""
    region: str = "海外"
    tags: List[str] = []
    strength_reasoning: int = 0
    strength_coding: int = 0
    strength_knowledge: int = 0
    strength_math: int = 0
    strength_multilingual: int = 0
    strength_multimodal: int = 0
    data_source: str = ""
    release_date: str = ""


class RatingCreate(BaseModel):
    model_id: str
    user_name: Optional[str] = None
    score: int
    comment: Optional[str] = None


class FinanceRecord(BaseModel):
    code: str
    name: str = ""
    date: str
    nav: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[float] = None


# ========================
# /api/models
# ========================

@app.get("/api/models", tags=["models"])
async def list_models(
    region: Optional[str] = Query(None),
    vendor: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None),
):
    params = {"order": "score.desc"}
    if region:
        params["region"] = f"eq.{region}"
    if vendor:
        params["vendor"] = f"eq.{vendor}"
    if min_score is not None:
        params["score"] = f"gte.{min_score}"

    data = await sb_get("models", params)
    return {"data": data, "count": len(data)}


@app.get("/api/models/{model_id}", tags=["models"])
async def get_model(model_id: str):
    params = {"id": f"eq.{model_id}"}
    data = await sb_get("models", params)
    if not data:
        raise HTTPException(status_code=404, detail="Model not found")
    return data[0]


@app.post("/api/models", tags=["models"])
async def create_model(m: ModelCreate):
    data = await sb_insert("models", m.model_dump())
    return {"msg": "ok", "data": data}


@app.put("/api/models/{model_id}", tags=["models"])
async def update_model(model_id: str, m: ModelCreate):
    params = {"id": f"eq.{model_id}"}
    data = await sb_update("models", m.model_dump(), params)
    return {"msg": "ok", "data": data}


@app.delete("/api/models/{model_id}", tags=["models"])
async def delete_model(model_id: str):
    params = {"id": f"eq.{model_id}"}
    await sb_delete("models", params)
    return {"msg": "deleted"}


# ========================
# /api/ratings
# ========================

@app.get("/api/ratings", tags=["ratings"])
async def list_ratings(model_id: Optional[str] = Query(None)):
    params = {"order": "created_at.desc"}
    if model_id:
        params["model_id"] = f"eq.{model_id}"
    data = await sb_get("ratings", params)
    return {"data": data, "count": len(data)}


@app.post("/api/ratings", tags=["ratings"])
async def create_rating(r: RatingCreate):
    data = await sb_insert("ratings", r.model_dump(exclude_none=True))
    return {"msg": "ok", "data": data}


# ========================
# /api/finance
# ========================

@app.get("/api/finance", tags=["finance"])
async def list_finance(
    code: Optional[str] = Query(None),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
):
    params = {"order": "date.desc", "limit": "200"}
    if code:
        params["code"] = f"eq.{code}"
    if start:
        params["date"] = f"gte.{start}"
    if end:
        params["date"] = f"lte.{end}"

    data = await sb_get("finance_daily", params)
    return {"data": data, "count": len(data)}


@app.post("/api/finance", tags=["finance"])
async def upsert_finance(record: FinanceRecord):
    url = f"{SUPABASE_URL}/rest/v1/finance_daily"
    h = sb_headers()
    h["Prefer"] = "resolution=merge-duplicates"
    params = {"on_conflict": "code,date"}
    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=h, json=record.model_dump(exclude_none=True), params=params)
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return {"msg": "ok", "data": r.json() if r.text else []}


# ========================
# /api/analyze
# ========================

@app.post("/api/analyze", tags=["analyze"])
async def analyze_task(request: Request):
    models = await sb_get("models")
    body = await request.json()
    weights = body.get("weights") or {}
    prefer_region = body.get("prefer_region", "auto")

    def calc_score(m: dict):
        w = weights
        match = (
            (m.get("strength_reasoning", 0) or 0) * w.get("reasoning", 0) / 100 +
            (m.get("strength_coding", 0) or 0)    * w.get("coding", 0)    / 100 +
            (m.get("strength_knowledge", 0) or 0) * w.get("knowledge", 0) / 100 +
            (m.get("strength_math", 0) or 0)      * w.get("math", 0)      / 100 +
            (m.get("strength_multilingual", 0) or 0) * w.get("multilingual", 0) / 100 +
            (m.get("strength_multimodal", 0) or 0) * w.get("multimodal", 0) / 100
        )
        price = m.get("price_per_m", 10) or 10
        median_price = 5.5
        if price <= 0:
            price = 1
        price_score = max(0, 100 - (price / median_price) * 50)

        region_boost = 0
        if prefer_region == "国产" and m.get("region") == "国产":
            region_boost = 10
        elif prefer_region == "海外" and m.get("region") == "海外":
            region_boost = 3

        final = match * 0.7 + price_score * 0.3 + region_boost
        return round(final, 2)

    scored = [(m, calc_score(m)) for m in models]
    scored.sort(key=lambda x: x[1], reverse=True)

    result = []
    for m, score in scored[:10]:
        result.append({
            "id": m["id"],
            "name": m["name"],
            "vendor": m["vendor"],
            "region": m.get("region", ""),
            "score": m.get("score", 0),
            "price_per_m": m.get("price_per_m", 0),
            "match_score": score,
            "reason": _gen_reason(m, weights, prefer_region),
        })
    return {"data": result}


def _gen_reason(m: dict, weights: dict, prefer_region: str) -> str:
    s_reasoning = m.get("strength_reasoning") or 0
    s_coding = m.get("strength_coding") or 0
    tags = []
    if s_coding >= 88 and weights.get("coding", 0) >= 20:
        tags.append("编程能力强")
    if s_reasoning >= 90 and weights.get("reasoning", 0) >= 20:
        tags.append("推理能力突出")
    if (m.get("price_per_m") or 99) <= 5:
        tags.append("性价比高")
    if m.get("region") == "国产" and prefer_region in ("auto", "国产"):
        tags.append("国产模型/数据合规")
    if not tags:
        tags.append("综合能力均衡")
    return " · ".join(tags)


# ========================
# Health check
# ========================

@app.get("/api/health", tags=["health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}
