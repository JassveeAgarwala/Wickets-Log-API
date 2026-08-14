from typing import Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


app = FastAPI(
    title="Khel AI Wicket Log API",
    version="1.0.0",
    description=(
        "Returns wicket events from an innings in delivery order, "
        "including dismissed player, wicket type, bowler, fielder, "
        "and notes. Integration-ready: accepts events via POST."
    )
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


# --- Request Models ---

class WicketEvent(BaseModel):
    dismissed_player: str
    wicket_type: str
    fielder: Optional[str] = None
    notes: Optional[str] = None


class BallEvent(BaseModel):
    event_id: str
    innings_id: str
    over_number: int = Field(..., ge=0)
    ball_number: int = Field(..., ge=1)
    batter: str
    bowler: str
    batter_runs: int = Field(default=0, ge=0)
    extras: Dict[str, int] = Field(default_factory=dict)
    wicket: Optional[WicketEvent] = None


class WicketLogRequest(BaseModel):
    innings_id: str
    events: List[BallEvent]


# --- Response Models ---

class WicketLogItem(BaseModel):
    event_id: str
    over_ball: str
    over_number: int
    ball_number: int
    dismissed_player: str
    wicket_type: str
    bowler: str
    fielder: Optional[str] = None
    notes: Optional[str] = None


class WicketLogResponse(BaseModel):
    innings_id: str
    total_wickets: int
    wickets: List[WicketLogItem]


# --- Service Layer (no internal data) ---

class WicketLogService:
    """
    Extracts and orders wicket events from raw deliveries.
    """

    def create_wicket_log(
        self,
        innings_id: str,
        events: List[BallEvent]
    ) -> WicketLogResponse:

        # Sort events to ensure delivery order
        ordered_events = sorted(
            events,
            key=lambda event: (
                event.over_number,
                event.ball_number
            )
        )

        wickets = []

        for event in ordered_events:
            if event.wicket is None:
                continue

            wicket = event.wicket

            wickets.append(
                WicketLogItem(
                    event_id=event.event_id,
                    over_ball=(
                        f"{event.over_number}.{event.ball_number}"
                    ),
                    over_number=event.over_number,
                    ball_number=event.ball_number,
                    dismissed_player=wicket.dismissed_player,
                    wicket_type=wicket.wicket_type,
                    bowler=event.bowler,
                    fielder=wicket.fielder,
                    notes=wicket.notes
                )
            )

        return WicketLogResponse(
            innings_id=innings_id,
            total_wickets=len(wickets),
            wickets=wickets
        )


wicket_service = WicketLogService()


# --- Routes ---

@app.get("/")
def home():
    return {
        "message": "Khel AI Wicket Log API is live",
        "endpoint": "POST /wickets",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post(
    "/wickets",
    response_model=WicketLogResponse,
    summary="Get wicket log from raw events",
    description=(
        "Accepts innings_id and list of ball events, "
        "returns ordered wicket log for the innings. "
        "Integration-ready for Khel AI MVP."
    )
)
def get_wicket_log(payload: WicketLogRequest):
    return wicket_service.create_wicket_log(
        innings_id=payload.innings_id,
        events=payload.events
    )
