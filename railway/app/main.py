import asyncio
import hmac
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .fetcher import fetch_contest_page
from .models import ReconRequest, ReconResponse
from .research import OpenAIContestAnalyst
from .scoring import score_assessment
from .settings import Settings, get_settings


app = FastAPI(
    title="Eye of Loki Intelligence Service",
    version="2.0.0",
    docs_url=None,
    redoc_url=None,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def require_secret(
    authorization: str | None = Header(default=None),
    runtime: Settings = Depends(get_settings),
) -> None:
    if not runtime.EYE_OF_LOKI_SHARED_SECRET:
        raise HTTPException(
            status_code=503,
            detail="EYE_OF_LOKI_SHARED_SECRET is not configured",
        )
    expected = f"Bearer {runtime.EYE_OF_LOKI_SHARED_SECRET}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid recon credentials")


@app.get("/health")
async def health(runtime: Settings = Depends(get_settings)) -> dict[str, object]:
    return {
        "ok": True,
        "service": "eye-of-loki-intelligence",
        "version": "2.0.0",
        "model": runtime.OPENAI_MODEL,
        "openai_configured": bool(runtime.OPENAI_API_KEY),
        "auth_configured": bool(runtime.EYE_OF_LOKI_SHARED_SECRET),
    }


@app.post(
    "/v1/recon",
    response_model=ReconResponse,
    dependencies=[Depends(require_secret)],
)
async def recon(
    request: ReconRequest,
    runtime: Settings = Depends(get_settings),
) -> ReconResponse:
    if len(request.contests) > runtime.MAX_CONTESTS_PER_RECON:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {runtime.MAX_CONTESTS_PER_RECON} contests per run",
        )
    if not runtime.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is missing")

    pages = await asyncio.gather(
        *[
            fetch_contest_page(contest, runtime)
            for contest in request.contests
        ]
    )
    analyst = OpenAIContestAnalyst(runtime)
    try:
        assessments = await analyst.analyze(
            request.contests,
            pages,
            request.profile,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI analysis failed: {type(exc).__name__}: {exc}",
        ) from exc

    analyzed_at = datetime.now(timezone.utc).isoformat()
    analyses = [score_assessment(assessment) for assessment in assessments]
    return ReconResponse(
        analyses=analyses,
        model=runtime.OPENAI_MODEL,
        analyzed_at=analyzed_at,
    )
