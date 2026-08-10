from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


app = FastAPI(
    title="Khel AI Wicket Log API",
    version="1.0.0",
    description=(
        "Returns wicket events from an innings in delivery order, "
        "including dismissed player, wicket type, bowler, fielder, "
        "and notes."
    )
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


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


RAW_BALL_EVENTS: Dict[str, List[BallEvent]] = {
    "innings-001": [
        BallEvent(
            event_id="ball-001",
            innings_id="innings-001",
            over_number=0,
            ball_number=1,
            batter="Rohit Sharma",
            bowler="Mitchell Starc",
            batter_runs=4
        ),
        BallEvent(
            event_id="ball-002",
            innings_id="innings-001",
            over_number=0,
            ball_number=2,
            batter="Rohit Sharma",
            bowler="Mitchell Starc",
            batter_runs=0,
            wicket=WicketEvent(
                dismissed_player="Rohit Sharma",
                wicket_type="caught",
                fielder="David Warner",
                notes="Caught at first slip"
            )
        ),
        BallEvent(
            event_id="ball-003",
            innings_id="innings-001",
            over_number=0,
            ball_number=3,
            batter="Virat Kohli",
            bowler="Mitchell Starc",
            batter_runs=2
        ),
        BallEvent(
            event_id="ball-004",
            innings_id="innings-001",
            over_number=1,
            ball_number=4,
            batter="Virat Kohli",
            bowler="Pat Cummins",
            batter_runs=0,
            wicket=WicketEvent(
                dismissed_player="Virat Kohli",
                wicket_type="lbw",
                notes="Trapped in front of the stumps"
            )
        ),
        BallEvent(
            event_id="ball-005",
            innings_id="innings-001",
            over_number=1,
            ball_number=5,
            batter="KL Rahul",
            bowler="Pat Cummins",
            batter_runs=1
        ),
        BallEvent(
            event_id="ball-006",
            innings_id="innings-001",
            over_number=2,
            ball_number=1,
            batter="KL Rahul",
            bowler="Josh Hazlewood",
            batter_runs=0,
            wicket=WicketEvent(
                dismissed_player="KL Rahul",
                wicket_type="run out",
                fielder="Steve Smith",
                notes="Run out attempting a second run"
            )
        )
    ],

    "innings-no-wickets": [
        BallEvent(
            event_id="ball-101",
            innings_id="innings-no-wickets",
            over_number=0,
            ball_number=1,
            batter="Shubman Gill",
            bowler="Mitchell Starc",
            batter_runs=4
        )
    ],

    "innings-empty": []
}


class BallEventRepository:
    """
    Provides access to raw ball-event data.

    In a production system, this class can later be connected
    to a database or live scoring system.
    """

    def innings_exists(self, innings_id: str) -> bool:
        return innings_id in RAW_BALL_EVENTS

    def get_events(self, innings_id: str) -> List[BallEvent]:
        return RAW_BALL_EVENTS.get(innings_id, [])


class WicketLogService:
    """
    Extracts and orders wicket events from raw deliveries.
    """

    def __init__(self, repository: BallEventRepository):
        self.repository = repository

    def create_wicket_log(
        self,
        innings_id: str
    ) -> Optional[WicketLogResponse]:

        if not self.repository.innings_exists(innings_id):
            return None

        events = self.repository.get_events(innings_id)

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


repository = BallEventRepository()
wicket_service = WicketLogService(repository)


@app.get("/")
def home():
    return {
        "message": "Khel AI Wicket Log API is live",
        "endpoint": "/innings/{innings_id}/wickets",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.get(
    "/innings/{innings_id}/wickets",
    response_model=WicketLogResponse
)
def get_wicket_log(innings_id: str):
    result = wicket_service.create_wicket_log(innings_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Innings not found"
        )

    return result
