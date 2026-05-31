"""
LLM Navigator Backend - Vercel Serverless
纯 ASGI 应用，兼容 Vercel Python Runtime
"""
import os
import json
import httpx
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Vercel 入口点
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional

app = FastAPI(title="LLM Navigator API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def sb_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


# ========================
# Supabase REST 客户端
# ========================

async def sb_get(table: str, params: dict = None) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=sb_headers(), params=params or {})
        if r.status_code >= 400:
            return []
        return r.json()

async def sb_insert(table: str, data) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    h = sb_headers()
    h["Prefer"] = "return=representation"
    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=h, json=data)
        return r.json() if r.text else []


# ========================
# API 路由
# ========================

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/models")
async def list_models():
    data = await sb_get("models", {"order": "score.desc"})
    return {"data": data, "count": len(data)}


@app.get("/api/ratings")
async def list_ratings():
    data = await sb_get("ratings", {"order": "created_at.desc"})
    return {"data": data, "count": len(data)}


@app.get("/api/finance")
async def list_finance():
    data = await sb_get("finance_daily", {"order": "date.desc", "limit": "200"})
    return {"data": data, "count": len(data)}


@app.post("/api/analyze")
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
        tags = []
        s_coding = m.get("strength_coding") or 0
        s_reasoning = m.get("strength_reasoning") or 0
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

        result.append({
            "id": m["id"],
            "name": m["name"],
            "vendor": m["vendor"],
            "region": m.get("region", ""),
            "score": m.get("score", 0),
            "price_per_m": m.get("price_per_m", 0),
            "match_score": score,
            "reason": " · ".join(tags),
        })
    return {"data": result}


@app.post("/api/ratings")
async def create_rating(request: Request):
    body = await request.json()
    data = await sb_insert("ratings", body)
    return {"msg": "ok", "data": data}
