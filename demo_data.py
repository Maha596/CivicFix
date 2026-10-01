"""
CivicFix - Automated Demo Data Seeder
Populates initial sample admin, citizens, realistic civic infrastructure reports,
resolution evidence, and notifications for instant academic project evaluation.
"""

import os
from werkzeug.security import generate_password_hash
from database.db import init_db, execute_query
from config import Config

def create_sample_images():
    """Generates lightweight SVG/PNG placeholder images for reports and resolutions."""
    rep_dir = os.path.join(Config.UPLOAD_FOLDER, 'reports')
    res_dir = os.path.join(Config.UPLOAD_FOLDER, 'resolutions')
    os.makedirs(rep_dir, exist_ok=True)
    os.makedirs(res_dir, exist_ok=True)

    samples = {
        'pothole_sample.svg': ('#334155', '#ef4444', 'POTHOLE ON MAIN ROAD', 'Deep asphalt depression, 45cm diameter'),
        'streetlight_sample.svg': ('#1e293b', '#eab308', 'DAMAGED STREETLIGHT', 'Pole lamp non-functional, exposed wire conduit'),
        'garbage_sample.svg': ('#1c1917', '#f97316', 'SOLID WASTE ACCUMULATION', 'Uncollected municipal garbage bins overflowing'),
        'waterleak_sample.svg': ('#082f49', '#0284c7', 'WATER SUPPLY LEAKAGE', 'High-pressure municipal pipeline rupture'),
        'fallentree_sample.svg': ('#064e3b', '#22c55e', 'FALLEN TREE OBSTRUCTION', 'Tree branch collapsed over arterial road'),
        'pothole_dup_sample.svg': ('#334155', '#ef4444', 'POTHOLE NEAR INTERSECTION', 'Adjacent road crater reported by pedestrian')
    }

    for fname, (bg, fg, title, subtitle) in samples.items():
        path = os.path.join(rep_dir, fname)
        if not os.path.exists(path):
            svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
                <rect width="600" height="400" fill="{bg}"/>
                <circle cx="300" cy="180" r="70" fill="{fg}" fill-opacity="0.2" stroke="{fg}" stroke-width="4"/>
                <text x="300" y="185" font-family="Arial, sans-serif" font-size="28" font-weight="bold" fill="{fg}" text-anchor="middle">CIVIC INCIDENT</text>
                <text x="300" y="270" font-family="Arial, sans-serif" font-size="22" font-weight="bold" fill="#ffffff" text-anchor="middle">{title}</text>
                <text x="300" y="305" font-family="Arial, sans-serif" font-size="14" fill="#94a3b8" text-anchor="middle">{subtitle}</text>
            </svg>"""
            with open(path, 'w', encoding='utf-8') as f:
                f.write(svg_content)

    # Resolution evidence image
    res_path = os.path.join(res_dir, 'garbage_resolved_sample.svg')
    if not os.path.exists(res_path):
        res_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
            <rect width="600" height="400" fill="#064e3b"/>
            <circle cx="300" cy="180" r="70" fill="#22c55e" fill-opacity="0.3" stroke="#22c55e" stroke-width="5"/>
            <text x="300" y="190" font-family="Arial, sans-serif" font-size="34" font-weight="bold" fill="#22c55e" text-anchor="middle">&#10003; RESOLVED</text>
            <text x="300" y="270" font-family="Arial, sans-serif" font-size="22" font-weight="bold" fill="#ffffff" text-anchor="middle">SITE CLEARED & SANITIZED</text>
            <text x="300" y="305" font-family="Arial, sans-serif" font-size="14" fill="#a7f3d0" text-anchor="middle">Municipal Sanitation Department - Resolution Evidence</text>
        </svg>"""
        with open(res_path, 'w', encoding='utf-8') as f:
            f.write(res_svg)

def seed():
    print("[Seed] Initializing database schema...")
    init_db()
    create_sample_images()

    # 1. Seed Users
    pwd_hash = generate_password_hash("Admin@123")
    citizen_hash = generate_password_hash("Citizen@123")

    admin = execute_query("SELECT id FROM users WHERE email = 'admin@civicfix.gov'", fetch_one=True)
    if not admin:
        admin_id = execute_query(
            "INSERT INTO users (name, email, phone, password, role) VALUES (?, ?, ?, ?, 'admin')",
            ('Chief Civic Administrator', 'admin@civicfix.gov', '+91 9876500000', pwd_hash),
            commit=True
        )
        print("[Seed] Created Administrator: admin@civicfix.gov / Admin@123")
    else:
        admin_id = admin['id']

    citizen = execute_query("SELECT id FROM users WHERE email = 'citizen@example.com'", fetch_one=True)
    if not citizen:
        citizen_id = execute_query(
            "INSERT INTO users (name, email, phone, password, role) VALUES (?, ?, ?, ?, 'citizen')",
            ('Mahavarshini', 'citizen@example.com', '+91 9876543210', citizen_hash),
            commit=True
        )
        print("[Seed] Created Citizen: citizen@example.com / Citizen@123")
    else:
        citizen_id = citizen['id']
        execute_query("UPDATE users SET name = 'Mahavarshini' WHERE email = 'citizen@example.com'", commit=True)

    # 2. Seed Departments
    dept_map = {}
    for dname in Config.DEPARTMENTS:
        row = execute_query("SELECT id FROM departments WHERE name = ?", (dname,), fetch_one=True)
        if not row:
            did = execute_query("INSERT INTO departments (name, description) VALUES (?, ?)",
                                (dname, f"Municipal department responsible for {dname.lower()}."), commit=True)
            dept_map[dname] = did
        else:
            dept_map[dname] = row['id']

    # 3. Seed Sample Reports if empty
    rep_count = execute_query("SELECT COUNT(*) as c FROM reports", fetch_one=True)['c']
    if rep_count == 0:
        print("[Seed] Populating sample civic complaints...")
        sample_reports = [
            {
                'complaint_id': 'CIV-2026-00001',
                'user_id': citizen_id,
                'category': 'Pothole',
                'description': 'Severe pothole approximately 2 feet wide on Cross Cut Road, causing severe traffic bottlenecks and hazard for two-wheelers.',
                'image_path': 'reports/pothole_sample.svg',
                'latitude': 11.0176,
                'longitude': 76.9673,
                'address': 'Cross Cut Road, Gandhipuram, Coimbatore',
                'landmark': 'Near Gandhipuram Central Bus Stand Signal',
                'severity': 'HIGH',
                'priority': 'HIGH',
                'priority_score': 62.0,
                'priority_reason': 'Category weight: 25pts | Severity (HIGH): 22pts | Safety: 15pts (main arterial road)',
                'ai_prediction': 'Pothole',
                'ai_confidence': 93.4,
                'status': 'IN_PROGRESS',
                'department_id': dept_map.get('Road Maintenance'),
                'is_duplicate': 0,
                'duplicate_of': None
            },
            {
                'complaint_id': 'CIV-2026-00002',
                'user_id': citizen_id,
                'category': 'Broken Streetlight',
                'description': 'Streetlight pole #18 on D.B. Road completely dark for the past 3 nights. Near school crossing with exposed junction box wires.',
                'image_path': 'reports/streetlight_sample.svg',
                'latitude': 11.0105,
                'longitude': 76.9463,
                'address': 'Diwan Bahadur (D.B.) Road, R.S. Puram, Coimbatore',
                'landmark': 'Opposite Corporation Girls High School',
                'severity': 'CRITICAL',
                'priority': 'CRITICAL',
                'priority_score': 82.0,
                'priority_reason': 'Category: 22pts | Severity (CRITICAL): 30pts | Safety: 15pts (school zone, exposed wire) | Aging: 15pts',
                'ai_prediction': 'Broken Streetlight',
                'ai_confidence': 91.8,
                'status': 'REPORTED',
                'department_id': dept_map.get('Electrical'),
                'is_duplicate': 0,
                'duplicate_of': None
            },
            {
                'complaint_id': 'CIV-2026-00003',
                'user_id': citizen_id,
                'category': 'Garbage',
                'description': 'Municipal community dumpsters overflowing near Ukkadam bus terminal causing foul odor and health hazard for pedestrians.',
                'image_path': 'reports/garbage_sample.svg',
                'latitude': 10.9902,
                'longitude': 76.9614,
                'address': 'Bypass Road, Ukkadam, Coimbatore',
                'landmark': 'Near Ukkadam Lake & Bus Terminus',
                'severity': 'MEDIUM',
                'priority': 'MEDIUM',
                'priority_score': 42.0,
                'priority_reason': 'Category: 14pts | Severity (MEDIUM): 14pts | Density: 14pts',
                'ai_prediction': 'Garbage',
                'ai_confidence': 94.2,
                'status': 'RESOLVED',
                'department_id': dept_map.get('Sanitation'),
                'is_duplicate': 0,
                'duplicate_of': None
            },
            {
                'complaint_id': 'CIV-2026-00004',
                'user_id': citizen_id,
                'category': 'Water Leakage',
                'description': 'Underground drinking water distribution pipeline cracked along Avinashi Road, potable water flooding the roadway.',
                'image_path': 'reports/waterleak_sample.svg',
                'latitude': 11.0267,
                'longitude': 77.0028,
                'address': 'Avinashi Road, Peelamedu, Coimbatore',
                'landmark': 'Near PSG College of Technology Main Gate',
                'severity': 'HIGH',
                'priority': 'HIGH',
                'priority_score': 68.0,
                'priority_reason': 'Category: 18pts | Severity (HIGH): 22pts | Safety: 15pts (highway arterial corridor)',
                'ai_prediction': 'Water Leakage',
                'ai_confidence': 89.6,
                'status': 'VERIFIED',
                'department_id': dept_map.get('Water Supply'),
                'is_duplicate': 0,
                'duplicate_of': None
            },
            {
                'complaint_id': 'CIV-2026-00005',
                'user_id': citizen_id,
                'category': 'Fallen Tree',
                'description': 'Heavy storm caused large tree branch to collapse across NSR Road, completely blocking vehicular movement.',
                'image_path': 'reports/fallentree_sample.svg',
                'latitude': 11.0289,
                'longitude': 76.9421,
                'address': 'NSR Road, Saibaba Colony, Coimbatore',
                'landmark': 'Near Ganga Hospital / Saibaba Temple Junction',
                'severity': 'CRITICAL',
                'priority': 'CRITICAL',
                'priority_score': 86.0,
                'priority_reason': 'Category: 26pts | Severity (CRITICAL): 30pts | Safety: 15pts (blocked thoroughfare)',
                'ai_prediction': 'Fallen Tree',
                'ai_confidence': 95.1,
                'status': 'ASSIGNED',
                'department_id': dept_map.get('Horticulture / Parks'),
                'is_duplicate': 0,
                'duplicate_of': None
            },
            {
                'complaint_id': 'CIV-2026-00006',
                'user_id': citizen_id,
                'category': 'Pothole',
                'description': 'Second crater on Cross Cut Road adjacent to Gandhipuram flyover ramp, causing wheel rim damage.',
                'image_path': 'reports/pothole_dup_sample.svg',
                'latitude': 11.0180,
                'longitude': 76.9677, # ~50 meters from CIV-2026-00001
                'address': 'Cross Cut Road, Gandhipuram, Coimbatore',
                'landmark': 'Near Cross Cut Road Signal Ramp',
                'severity': 'HIGH',
                'priority': 'HIGH',
                'priority_score': 68.0,
                'priority_reason': 'Category: 25pts | Severity: 22pts | Density: 20pts (Cluster of 2 reports within 50m)',
                'ai_prediction': 'Pothole',
                'ai_confidence': 92.0,
                'status': 'REPORTED',
                'department_id': dept_map.get('Road Maintenance'),
                'is_duplicate': 1,
                'duplicate_of': 'CIV-2026-00001'
            }
        ]

        for rep in sample_reports:
            insert_q = """
                INSERT INTO reports (
                    complaint_id, user_id, category, description, image_path,
                    latitude, longitude, address, landmark, severity,
                    priority, priority_score, priority_reason, ai_prediction, ai_confidence,
                    status, department_id, is_duplicate, duplicate_of
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            rid = execute_query(
                insert_q,
                (
                    rep['complaint_id'], rep['user_id'], rep['category'], rep['description'], rep['image_path'],
                    rep['latitude'], rep['longitude'], rep['address'], rep['landmark'], rep['severity'],
                    rep['priority'], rep['priority_score'], rep['priority_reason'], rep['ai_prediction'], rep['ai_confidence'],
                    rep['status'], rep['department_id'], rep['is_duplicate'], rep['duplicate_of']
                ),
                commit=True
            )

            # Record updates
            execute_query(
                "INSERT INTO report_updates (report_id, status, remark, updated_by) VALUES (?, 'REPORTED', 'Complaint lodged by citizen.', ?)",
                (rid, citizen_id), commit=True
            )
            if rep['status'] in ('VERIFIED', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED'):
                execute_query(
                    "INSERT INTO report_updates (report_id, status, remark, updated_by) VALUES (?, 'VERIFIED', 'Issue verified by municipal inspection squad.', ?)",
                    (rid, admin_id), commit=True
                )
            if rep['status'] in ('ASSIGNED', 'IN_PROGRESS', 'RESOLVED'):
                execute_query(
                    "INSERT INTO report_updates (report_id, status, remark, updated_by) VALUES (?, 'ASSIGNED', 'Work order issued to field team.', ?)",
                    (rid, admin_id), commit=True
                )
            if rep['status'] in ('IN_PROGRESS', 'RESOLVED'):
                execute_query(
                    "INSERT INTO report_updates (report_id, status, remark, updated_by) VALUES (?, 'IN_PROGRESS', 'Field crew dispatched on-site for remediation.', ?)",
                    (rid, admin_id), commit=True
                )

            # For CIV-2026-00003, record resolution evidence
            if rep['complaint_id'] == 'CIV-2026-00003':
                execute_query(
                    """
                    INSERT INTO resolutions (report_id, resolution_image, resolution_note, resolved_by)
                    VALUES (?, 'resolutions/garbage_resolved_sample.svg', 'Sanitation crew cleared accumulated solid waste, sanitized with bleaching powder, and deployed 2 additional heavy-duty bins.', ?)
                    """,
                    (rid, admin_id), commit=True
                )
                execute_query(
                    "INSERT INTO report_updates (report_id, status, remark, updated_by) VALUES (?, 'RESOLVED', 'Solid waste completely removed and sanitized.', ?)",
                    (rid, admin_id), commit=True
                )

        # Record duplicate link between 6 and 1
        r1 = execute_query("SELECT id FROM reports WHERE complaint_id = 'CIV-2026-00001'", fetch_one=True)
        r3 = execute_query("SELECT id FROM reports WHERE complaint_id = 'CIV-2026-00003'", fetch_one=True)
        r6 = execute_query("SELECT id FROM reports WHERE complaint_id = 'CIV-2026-00006'", fetch_one=True)
        if r1 and r6:
            execute_query(
                "INSERT INTO duplicate_links (report_id, possible_duplicate_id, distance_meters, similarity_score) VALUES (?, ?, 45.2, 92.5)",
                (r6['id'], r1['id']), commit=True
            )

        # Seed sample notifications
        if r1:
            execute_query(
                "INSERT INTO notifications (user_id, report_id, title, message) VALUES (?, ?, 'Status Update', 'Your complaint CIV-2026-00001 has been moved to IN_PROGRESS.')",
                (citizen_id, r1['id']), commit=True
            )
        if r3:
            execute_query(
                "INSERT INTO notifications (user_id, report_id, title, message) VALUES (?, ?, 'Issue Resolved', 'Your complaint CIV-2026-00003 has been marked as RESOLVED. Please verify and confirm.')",
                (citizen_id, r3['id']), commit=True
            )

        print("[Seed] Successfully seeded 6 sample civic complaints, updates, and evidence.")

if __name__ == '__main__':
    seed()
