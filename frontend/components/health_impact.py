from __future__ import annotations


def cigarettes_equivalent(pm25_ugm3: float) -> float:
    # Berkeley Earth approximation: daily PM2.5 exposure equivalent in cigarettes.
    return max(0.0, float(pm25_ugm3) / 22.0)


def safe_outdoor_hours(aqi: float) -> dict[str, float]:
    aqi = float(aqi)

    if aqi <= 50:  # WHO 2021: very low risk exposure band
        return {"healthy_adult": 8.0, "child": 6.0, "elderly": 6.0, "asthmatic": 4.0}
    if aqi <= 100:  # WHO 2021: mild-to-moderate risk exposure band
        return {"healthy_adult": 5.0, "child": 3.0, "elderly": 3.0, "asthmatic": 1.5}
    if aqi <= 200:  # WHO 2021: elevated risk exposure band
        return {"healthy_adult": 2.5, "child": 1.0, "elderly": 1.0, "asthmatic": 0.5}
    if aqi <= 300:  # WHO 2021: high risk exposure band
        return {"healthy_adult": 1.0, "child": 0.5, "elderly": 0.5, "asthmatic": 0.25}
    # WHO 2021: extreme risk exposure band
    return {"healthy_adult": 0.5, "child": 0.25, "elderly": 0.25, "asthmatic": 0.0}


def get_mask_recommendation(aqi: float) -> str:
    aqi = float(aqi)
    if aqi <= 100:
        return "No mask needed"
    if aqi <= 200:
        return "N95 recommended"
    if aqi <= 300:
        return "N95 mandatory"
    return "Stay indoors even with N95"


def get_activity_advisory(aqi: float) -> dict[str, str]:
    aqi = float(aqi)

    if aqi <= 50:
        return {
            "exercise": "Outdoor exercise is generally safe.",
            "commute": "Normal commute is acceptable.",
            "children_outdoor": "Children can play outdoors with normal breaks.",
            "elderly_outdoor": "Light outdoor walks are safe.",
        }
    if aqi <= 100:
        return {
            "exercise": "Moderate outdoor exercise only; avoid roadside workouts.",
            "commute": "Prefer low-traffic routes and shorter commute windows.",
            "children_outdoor": "Limit continuous outdoor play and monitor symptoms.",
            "elderly_outdoor": "Short, low-intensity walks advised.",
        }
    if aqi <= 200:
        return {
            "exercise": "Shift workouts indoors when possible.",
            "commute": "Use mask during commute and avoid peak congestion.",
            "children_outdoor": "Outdoor activity should be brief and supervised.",
            "elderly_outdoor": "Prefer indoor activity; go out only if necessary.",
        }
    if aqi <= 300:
        return {
            "exercise": "Avoid strenuous outdoor exercise.",
            "commute": "Only essential commute with strict mask use.",
            "children_outdoor": "Keep children indoors.",
            "elderly_outdoor": "Avoid outdoor exposure as much as possible.",
        }

    return {
        "exercise": "Avoid all outdoor exercise.",
        "commute": "Avoid non-essential travel and remain indoors.",
        "children_outdoor": "Children should stay indoors completely.",
        "elderly_outdoor": "Elderly should remain indoors and avoid exposure.",
    }
