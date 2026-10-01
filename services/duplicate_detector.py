"""
CivicFix - Duplicate Issue Detection Service
Detects spatial and categorical proximity between reported complaints.
Flags potential duplicates without deleting data, preserving citizen reports
while notifying administrators of clustering.
"""

from database.db import execute_query
from services.priority import haversine_distance

def detect_duplicates(category, latitude, longitude, current_report_id=None, radius_meters=150):
    """
    Checks if an existing unresolved report of the same category is within radius_meters.
    Returns:
        dict with 'is_duplicate': bool, 'matches': list of matched reports
    """
    if latitude is None or longitude is None:
        return {'is_duplicate': False, 'matches': []}

    try:
        lat = float(latitude)
        lon = float(longitude)
    except (ValueError, TypeError):
        return {'is_duplicate': False, 'matches': []}

    query = """
        SELECT id, complaint_id, category, description, latitude, longitude, created_at, status
        FROM reports
        WHERE status NOT IN ('RESOLVED', 'REJECTED')
    """
    params = ()
    if current_report_id:
        query += " AND id != ?"
        params = (current_report_id,)

    existing_reports = execute_query(query, params, fetch_all=True) or []

    matches = []
    for r in existing_reports:
        r_lat = r.get('latitude')
        r_lon = r.get('longitude')
        if r_lat is not None and r_lon is not None:
            dist = haversine_distance(lat, lon, float(r_lat), float(r_lon))
            if dist <= radius_meters:
                # Category similarity
                is_same_cat = (r.get('category', '').lower() == category.lower())
                
                # Distance score (1.0 at 0m down to 0.5 at radius_meters)
                dist_score = max(0.5, 1.0 - (dist / (radius_meters * 2.0)))
                
                cat_weight = 0.5 if is_same_cat else 0.2
                total_sim = round((dist_score * 0.5 + cat_weight) * 100, 1)

                if is_same_cat or total_sim >= 65:
                    matches.append({
                        'report_id': r['id'],
                        'complaint_id': r['complaint_id'],
                        'category': r['category'],
                        'distance_meters': round(dist, 1),
                        'similarity_score': min(98.0, total_sim),
                        'status': r['status'],
                        'created_at': r['created_at']
                    })

    # Sort by closest distance
    matches.sort(key=lambda x: x['distance_meters'])

    return {
        'is_duplicate': len(matches) > 0,
        'matches': matches
    }

def record_duplicate_links(report_id, matches):
    """Inserts potential duplicate relationships into duplicate_links table."""
    for m in matches:
        check_q = "SELECT id FROM duplicate_links WHERE report_id = ? AND possible_duplicate_id = ?"
        exists = execute_query(check_q, (report_id, m['report_id']), fetch_one=True)
        if not exists:
            insert_q = """
                INSERT INTO duplicate_links (report_id, possible_duplicate_id, distance_meters, similarity_score)
                VALUES (?, ?, ?, ?)
            """
            execute_query(insert_q, (report_id, m['report_id'], m['distance_meters'], m['similarity_score']), commit=True)
