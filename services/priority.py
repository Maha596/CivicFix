"""
CivicFix - Intelligent Priority Calculation Engine
Computes explainable civic complaint priority using multi-criteria weighted scoring:
- Category inherent risk
- Citizen-selected severity
- Geospatial density of nearby unresolved complaints
- Public safety & high-hazard keywords
- Temporal aging of complaint
"""

from database.db import execute_query
import math

CATEGORY_BASE_WEIGHTS = {
    'Broken Streetlight': 22,
    'Pothole': 25,
    'Fallen Tree': 26,
    'Drainage Issue': 22,
    'Water Leakage': 18,
    'Damaged Road': 20,
    'Damaged Public Property': 15,
    'Garbage': 14,
    'Other': 10
}

SEVERITY_WEIGHTS = {
    'CRITICAL': 30,
    'HIGH': 22,
    'MEDIUM': 14,
    'LOW': 6
}

SAFETY_KEYWORDS = [
    'school', 'hospital', 'highway', 'main road', 'junction',
    'traffic', 'accident', 'danger', 'hazard', 'electric',
    'children', 'elderly', 'deep', 'live wire', 'flooding',
    'blocked', 'emergency', 'ambulance'
]

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculates distance between two GPS coordinates in meters."""
    if None in (lat1, lon1, lat2, lon2):
        return 999999
    try:
        R = 6371000  # Radius of earth in meters
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    except Exception:
        return 999999

def count_nearby_active_issues(latitude, longitude, category=None, radius_meters=300):
    """Counts active (unresolved) reports within radius."""
    if not latitude or not longitude:
        return 0
    
    query = "SELECT latitude, longitude, category FROM reports WHERE status NOT IN ('RESOLVED', 'REJECTED')"
    rows = execute_query(query, fetch_all=True) or []
    count = 0
    for r in rows:
        r_lat = r.get('latitude')
        r_lon = r.get('longitude')
        if r_lat and r_lon:
            dist = haversine_distance(latitude, longitude, float(r_lat), float(r_lon))
            if dist <= radius_meters:
                count += 1
    return count

def calculate_priority(category, severity, latitude=None, longitude=None, description="", landmark="", age_days=0):
    """
    Computes priority level and returns an explainable breakdown.
    Levels: LOW, MEDIUM, HIGH, CRITICAL
    """
    # 1. Category Base Weight (max 30)
    cat_score = CATEGORY_BASE_WEIGHTS.get(category, 15)

    # 2. Citizen Severity Weight (max 30)
    sev_upper = str(severity).upper() if severity else 'MEDIUM'
    sev_score = SEVERITY_WEIGHTS.get(sev_upper, 14)

    # 3. Location Density (max 20)
    nearby_count = count_nearby_active_issues(latitude, longitude, category=category, radius_meters=300)
    if nearby_count >= 3:
        density_score = 20
        density_reason = f"High cluster: {nearby_count} active civic reports within 300m"
    elif nearby_count == 2:
        density_score = 14
        density_reason = f"Moderate cluster: {nearby_count} active reports nearby"
    elif nearby_count == 1:
        density_score = 8
        density_reason = "1 existing complaint in vicinity"
    else:
        density_score = 0
        density_reason = "Isolated complaint location"

    # 4. Public Safety Factor (max 15)
    combined_text = f"{description} {landmark}".lower()
    safety_matches = [w for w in SAFETY_KEYWORDS if w in combined_text]
    if safety_matches:
        safety_score = 15
        safety_reason = f"Safety risk indicators detected: {', '.join(safety_matches[:3])}"
    else:
        safety_score = 0
        safety_reason = "No immediate high-risk safety keywords detected"

    # 5. Temporal Aging Factor (max 10)
    if age_days >= 14:
        age_score = 10
        age_reason = "Overdue: Unresolved for 14+ days"
    elif age_days >= 7:
        age_score = 7
        age_reason = "Pending for over 7 days"
    elif age_days >= 3:
        age_score = 3
        age_reason = "Pending for over 3 days"
    else:
        age_score = 0
        age_reason = "Recently reported"

    # Composite Score (0 to 105)
    total_score = cat_score + sev_score + density_score + safety_score + age_score

    # Determine Priority Level
    if total_score >= 75:
        level = 'CRITICAL'
    elif total_score >= 50:
        level = 'HIGH'
    elif total_score >= 30:
        level = 'MEDIUM'
    else:
        level = 'LOW'

    explanation = (
        f"Category weight: {cat_score}pts | "
        f"Severity ({sev_upper}): {sev_score}pts | "
        f"Density: {density_score}pts ({density_reason}) | "
        f"Safety: {safety_score}pts ({safety_reason}) | "
        f"Aging: {age_score}pts"
    )

    return {
        'priority': level,
        'score': total_score,
        'explanation': explanation,
        'breakdown': {
            'category_score': cat_score,
            'severity_score': sev_score,
            'density_score': density_score,
            'density_reason': density_reason,
            'safety_score': safety_score,
            'safety_reason': safety_reason,
            'age_score': age_score,
            'age_reason': age_reason,
            'total_score': total_score
        }
    }
