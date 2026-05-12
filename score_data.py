class ScoreData:
    """Class to store the important score data from each match in lists."""

    def __init__(self):
        self.hub_score: dict[str, list[int]] = {
            "autoCount": [],
            "transitionCount": [],
            "shift1Count": [],
            "shift2Count": [],
            "shift3Count": [],
            "shift4Count": [],
            "endgameCount": [],
            "teleopCount": [],
            "totalCount": [],
            "uncounted": []
        }

        self.score_breakdown: dict[str, list[int]] = {
            "autoTowerPoints": [],
            "endGameTowerPoints": [],
            "totalTowerPoints": [],
            "foulPoints": [],
            "totalAutoPoints": [],
            "totalTeleopPoints": [],
            "totalPoints": [],
            "rp": []
        }