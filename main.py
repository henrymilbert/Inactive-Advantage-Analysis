from __future__ import print_function
from enum import StrEnum
import re
from statistics import mean, stdev
import tbaapiv3client
from tbaapiv3client.rest import ApiException

from cache import MatchCache

from score_data import ScoreData

# Set a minimum auto hub count for matches to be used.
MIN_AUTO_HUB_COUNT: int | None = None
# Set a minimum total points for matches to be used (looks at the higher of the two alliances'
# total points).
MIN_HIGHER_TOTAL_POINTS: int | None = None
# Set to true to print the standard deviations for each category in the comparison tables.
PRINT_STANDARD_DEVIATIONS: bool = False
# Set to true to print the tables of the total points difference (first inactive - second inactive)
# versus auto hub count and the total points difference versus higher total points in a format that
# can be copied into a spreadsheet or Desmos. (VS Code didn't print it out correctly, so I used
# IDLE to print it instead.)
PRINT_DIFF_VERSUS_POINTS_TABLE: bool = False
# Set to true to print the raw data for total points for the first and second inactive alliances, and
# the difference.
PRINT_TOTAL_POINTS_RAW_DATA: bool = False
# Set the tolerance percentage for how close the auto hub counts must be to be included.
AUTO_HUB_SCORE_TOLERANCE_PERCENT: float = 0.0

configuration = tbaapiv3client.Configuration(
    host="https://www.thebluealliance.com/api/v3",
    api_key={
        'X-TBA-Auth-Key': 'cggK4TyXXKHqyc178BENo4Pr4xn784yToaBispkny00owGKlmTRleE3ohflURWwb'
    }
)


class AllianceColor(StrEnum):
    RED = "red"
    BLUE = "blue"
    NONE = ""


def determine_first_inactive(red_hub_score: dict[str, int], blue_hub_score: dict[str, int]) -> AllianceColor | None:
    # Compare auto hub count
    if red_hub_score.get("autoCount") > blue_hub_score.get("autoCount"):
        return AllianceColor.RED
    if blue_hub_score.get("autoCount") > red_hub_score.get("autoCount"):
        return AllianceColor.BLUE

    # Auto hub count tied: compare shift 1 to find who was randomly selected as inactive first
    if red_hub_score.get("shift1Count") > 0:
        return AllianceColor.BLUE
    if blue_hub_score.get("shift1Count") > 0:
        return AllianceColor.RED

    # No scoring in shift 1: compare shift 2
    if red_hub_score.get("shift2Count") > 0:
        return AllianceColor.RED
    if blue_hub_score.get("shift2Count") > 0:
        return AllianceColor.BLUE

    # No scoring in shift 2: compare shift 3
    if red_hub_score.get("shift3Count") > 0:
        return AllianceColor.BLUE
    if blue_hub_score.get("shift3Count") > 0:
        return AllianceColor.RED

    # No scoring in shift 3: compare shift 4
    if red_hub_score.get("shift4Count") > 0:
        return AllianceColor.RED
    if blue_hub_score.get("shift4Count") > 0:
        return AllianceColor.BLUE

    # Auto hub count tied, no shift scoring. Cannot determine who was inactive first.
    return None


def camel_to_title(text):
    # Inserts space between letter/digit transitions.
    pattern = r'(?<=[a-z])(?=[A-Z])|(?<=[a-zA-Z])(?=[0-9])|(?<=[0-9])(?=[a-zA-Z])'
    spaced_text = re.sub(pattern, ' ', text)
    # Converts to Title Case (capitalizes every word).
    return spaced_text.title()


def print_comparison_tables(first_data: ScoreData, second_data: ScoreData, diff_data: ScoreData):
    """Print formatted comparison tables for means and standard deviations."""

    header = f"{'Category':<22} {'First Inactive':<17} {'Second Inactive':<17} {'Difference':<17}"

    divider_length = len(header)

    # Get all hub score keys.
    hub_keys = list(first_data.hub_score.keys())
    # Get all score breakdown keys.
    breakdown_keys = list(first_data.score_breakdown.keys())

    print("\nMeans:")
    print("-" * divider_length)
    print(header)
    print("-" * divider_length)

    # Print hub score means.
    for key in hub_keys:
        first_mean = mean(first_data.hub_score[key]) if first_data.hub_score[key] else 0
        second_mean = mean(second_data.hub_score[key]) if second_data.hub_score[key] else 0
        diff_mean = mean(diff_data.hub_score[key]) if diff_data.hub_score[key] else 0

        print(f"{"Hub " + camel_to_title(key):<22} {first_mean:<17.4f} {second_mean:<17.4f} {diff_mean:<17.4f}")

    # Print score breakdown means.
    for key in breakdown_keys:
        first_mean = mean(first_data.score_breakdown[key]) if first_data.score_breakdown[key] else 0
        second_mean = mean(second_data.score_breakdown[key]) if second_data.score_breakdown[key] else 0
        diff_mean = mean(diff_data.score_breakdown[key]) if diff_data.score_breakdown[key] else 0

        print(f"{camel_to_title(key):<22} {first_mean:<17.4f} {second_mean:<17.4f} {diff_mean:<17.4f}")

    if PRINT_STANDARD_DEVIATIONS:
        print("\nStandard Deviations:")
        print("-" * divider_length)
        print(header)
        print("-" * divider_length)

        # Print hub score standard deviations.
        for key in hub_keys:
            first_std = stdev(first_data.hub_score[key]) if len(first_data.hub_score[key]) > 1 else 0
            second_std = stdev(second_data.hub_score[key]) if len(second_data.hub_score[key]) > 1 else 0
            diff_std = stdev(diff_data.hub_score[key]) if len(diff_data.hub_score[key]) > 1 else 0

            print(f"{"Hub " + camel_to_title(key):<22} {first_std:<17.4f} {second_std:<17.4f} {diff_std:<17.4f}")

        # Print score breakdown standard deviations.
        for key in breakdown_keys:
            first_std = stdev(first_data.score_breakdown[key]) if len(first_data.score_breakdown[key]) > 1 else 0
            second_std = stdev(second_data.score_breakdown[key]) if len(second_data.score_breakdown[key]) > 1 else 0
            diff_std = stdev(diff_data.score_breakdown[key]) if len(diff_data.score_breakdown[key]) > 1 else 0

            print(f"{camel_to_title(key):<22} {first_std:<17.4f} {second_std:<17.4f} {diff_std:<17.4f}")


if __name__ == "__main__":
    with tbaapiv3client.ApiClient(configuration) as api_client:
        api_instance = tbaapiv3client.EventApi(api_client)
        cache = MatchCache()

        skipped_ties = 0
        skipped_no_inactive_first = 0

        first_inactive_data = ScoreData()
        second_inactive_data = ScoreData()
        diff_first_minus_second_data = ScoreData()

        matches_won_by_inactive_first = 0
        matches_won_by_inactive_second = 0

        total_matches_checked = 0

        points_diff_vs_auto_hub_count_string = ""
        points_diff_vs_higher_total_points_string = ""

        total_points_raw_data_string = ""

        try:
            # Get list of events for the year 2026.
            events: list[tbaapiv3client.Event] = api_instance.get_events_by_year(2026)

            for index, event in enumerate(events):
                print(f"Checking event {index + 1}/{len(events)}")

                # Filter out offseason and preaseason events.
                if event.event_type_string in {"Offseason", "Preseason"}:
                    continue

                # Check if we have cached match data for this event.
                cached_matches = cache.get(event.key)
                if cached_matches is not None:
                    matches_data = cached_matches
                else:
                    # Cache missing, fetch from API once and save locally.
                    print(f"Fetching from API: {event.key}")
                    matches: list[tbaapiv3client.Match] = api_instance.get_event_matches(event.key)

                    # Convert to simple dicts for caching (only what we need)
                    matches_data = [
                        {
                            "key": m.key,
                            "score_breakdown": m.score_breakdown,
                            "winning_alliance": m.winning_alliance
                        }
                        for m in matches
                    ]
                    cache.save(event.key, matches_data)

                for match_data in matches_data:
                    # Get the score breakdown for the match.
                    score_breakdown: dict[str, dict] = match_data["score_breakdown"]

                    # Get the score breakdown for each alliance by color.
                    red_score_breakdown = score_breakdown.get("red")
                    blue_score_breakdown = score_breakdown.get("blue")

                    # Get the hub scoring breakdown for each alliance by color.
                    red_hub_score: dict[str, int] = red_score_breakdown.get("hubScore")
                    blue_hub_score: dict[str, int] = blue_score_breakdown.get("hubScore")

                    # Only look at matches where the auto hub count is the same for both alliances,
                    # and therefore the first inactive shift was randomly assigned. Setting the
                    # AUTO_HUB_SCORE_TOLERANCE_PERCENT to a value greater than 0 will allow matches
                    # where the auto hub counts are close, but not exactly the same, to be included
                    # as well.
                    if abs(red_hub_score.get("autoCount") - blue_hub_score.get("autoCount")) > AUTO_HUB_SCORE_TOLERANCE_PERCENT / 100 * max(red_hub_score.get("autoCount"), blue_hub_score.get("autoCount")):
                        continue

                    # Only look at matches with an auto hub count above the specified threshold (if set).
                    if MIN_AUTO_HUB_COUNT is not None and min(red_hub_score.get("autoCount"), blue_hub_score.get("autoCount")) < MIN_AUTO_HUB_COUNT:
                        continue

                    # Only look at matches with a higher total points above the specified threshold (if set).
                    if MIN_HIGHER_TOTAL_POINTS is not None and max(
                        red_score_breakdown.get("totalPoints"), blue_score_breakdown.get("totalPoints")
                    ) < MIN_HIGHER_TOTAL_POINTS:
                        continue

                    # Determine which alliance was inactive first.
                    first_inactive = determine_first_inactive(red_hub_score, blue_hub_score)

                    # If we can't determine who was inactive first, skip the match. This was likely a
                    # completely invalid match anyway, since there was no scoring in any of the shifts.
                    if first_inactive is None:
                        skipped_no_inactive_first += 1
                        continue

                    # Determine which alliance won the match.
                    winner: AllianceColor = match_data["winning_alliance"]

                    # If there was no winner, skip the match.
                    if winner == AllianceColor.NONE:
                        skipped_ties += 1
                        continue

                    # Get the score breakdown for each alliance by when they were inactive.
                    first_inactive_score_breakdown = score_breakdown.get(first_inactive)
                    second_inactive_score_breakdown = score_breakdown.get(
                        AllianceColor.BLUE if first_inactive == AllianceColor.RED else AllianceColor.RED
                    )

                    # Get the hub scoring breakdown for each alliance by when they were inactive.
                    first_inactive_hub_score: dict[str, int] = first_inactive_score_breakdown.get("hubScore")
                    second_inactive_hub_score: dict[str, int] = second_inactive_score_breakdown.get("hubScore")

                    # Record the data for the first inactive alliance.
                    for key, value in first_inactive_data.hub_score.items():
                        value.append(first_inactive_hub_score.get(key))
                    for key, value in first_inactive_data.score_breakdown.items():
                        value.append(first_inactive_score_breakdown.get(key))

                    # Record the data for the second inactive alliance.
                    for key, value in second_inactive_data.hub_score.items():
                        value.append(second_inactive_hub_score.get(key))
                    for key, value in second_inactive_data.score_breakdown.items():
                        value.append(second_inactive_score_breakdown.get(key))

                    # Record the difference in data between the first and second inactive alliances
                    # (first minus second).
                    for key, value in diff_first_minus_second_data.hub_score.items():
                        value.append(first_inactive_hub_score.get(key) - second_inactive_hub_score.get(key))
                    for key, value in diff_first_minus_second_data.score_breakdown.items():
                        value.append(first_inactive_score_breakdown.get(key) - second_inactive_score_breakdown.get(key))

                    # Print the points difference versus auto hub count and higher total points for
                    # this match in a format that can be copied into a spreadsheet or Desmos (if
                    # enabled).
                    if PRINT_DIFF_VERSUS_POINTS_TABLE:
                        total_points_diff = (
                            first_inactive_score_breakdown.get("totalPoints")
                                - second_inactive_score_breakdown.get("totalPoints")
                        )
                        points_diff_vs_auto_hub_count_string += (
                            f"\n{first_inactive_hub_score.get("autoCount")}\t{total_points_diff}"
                        )
                        points_diff_vs_higher_total_points_string += (
                            f"\n{max(
                                first_inactive_score_breakdown.get("totalPoints"),
                                second_inactive_score_breakdown.get("totalPoints")
                            )}\t{total_points_diff}"
                        )

                    if PRINT_TOTAL_POINTS_RAW_DATA:
                        total_points_raw_data_string += (
                            f"\n{first_inactive_score_breakdown.get("totalPoints")}\t"
                            f"{second_inactive_score_breakdown.get("totalPoints")}\t"
                            f"{
                                first_inactive_score_breakdown.get("totalPoints")
                                    - second_inactive_score_breakdown.get("totalPoints")
                            }"
                        )

                    # Find which alliance (inactive first or inactive second) won the match, and
                    # increase the appropriate count.
                    if winner == first_inactive:
                        matches_won_by_inactive_first += 1
                    else:
                        matches_won_by_inactive_second += 1

                    # Increase the count of total matches checked.
                    total_matches_checked += 1

        except ApiException as e:
            print("Exception when calling EventApi->get_events_by_year: %s\n" % e)
        else:
            print()
            print(f"Matches checked: {total_matches_checked}")
            print(f"First inactive wins: {matches_won_by_inactive_first}")
            print(f"Second inactive wins: {matches_won_by_inactive_second}")
            print(f"Skipped couldn't determine inactive first: {skipped_no_inactive_first}")
            print(f"Skipped non-decisive winners/ties: {skipped_ties}")

            # Print formatted comparison tables
            print_comparison_tables(first_inactive_data, second_inactive_data, diff_first_minus_second_data)

            if PRINT_DIFF_VERSUS_POINTS_TABLE:
                print(f"\nAuto Count\tTotal Points Diff{points_diff_vs_auto_hub_count_string}")
                print(f"\nHigher Total Points\tTotal Points Diff{points_diff_vs_higher_total_points_string}")

            if PRINT_TOTAL_POINTS_RAW_DATA:
                print(
                    f"\nFirst Inactive\tSecond Inactive\tDifference (First - Second)"
                        + total_points_raw_data_string
                )