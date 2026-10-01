# CivicFix – Intelligent Public Infrastructure Issue Reporting & Resolution System

**3rd-Year B.Tech Artificial Intelligence and Data Science Mini-Project**

---

## 1. Project Title
**CivicFix: Intelligent Public Infrastructure Issue Reporting, Prioritization, and Resolution Platform**

---

## 2. Problem Statement
Urban public infrastructure in modern municipalities regularly experiences degradation, including road craters (potholes), non-operational streetlighting, overflowing garbage dumpsters, ruptured water mains, choked storm drainage conduits, and fallen trees. Currently, citizens face numerous challenges:
- Absence of a unified, transparent digital reporting channel.
- Ambiguity in identifying the appropriate municipal department responsible for remediation.
- Inability to objectively assess and rank issue urgency, leading to safety hazards being ignored.
- Pervasive duplicate reports overwhelming administrative staff at identical locations.
- Lack of verifiable resolution evidence, resulting in premature or unverified complaint closure.

---

## 3. Proposed Solution
**CivicFix** is an AI-augmented full-stack web platform designed to bridge the operational gap between citizens and municipal authorities. By coupling **Computer Vision AI** for automated issue classification with an **Intelligent Multi-Criteria Priority Engine** and **Geospatial GIS Mapping**, CivicFix streamlines the entire complaint lifecycle from initial citizen capture to on-site resolution evidence verification.

---

## 4. Key Objectives
1. **Empower Citizens**: Provide a responsive portal for snapping photos, tagging GPS coordinates, and tracking civic issues.
2. **AI-Driven Issue Categorization**: Apply computer vision feature extraction to diagnose civic defect categories with calibrated confidence scores.
3. **Dynamic Priority Calculation**: Compute explainable urgency scores considering inherent category risk, citizen severity, neighborhood report density, and public safety flags.
4. **Geospatial Proximity Deduplication**: Use the Haversine metric to link concurrent reports submitted in the same vicinity without data deletion.
5. **Municipal Accountability**: Provide administrators with real-time operations dashboards and require resolution photographic proof before closing complaints.
6. **Citizen Verification Loop**: Enable citizens to inspect uploaded resolution proof and confirm repair or reopen the ticket.

---

## 5. System Features

### Citizen Capabilities
* **Secure Registration & Authentication**: Role-based access with hashed password security.
* **Photograph & AI Diagnosis**: Drag-and-drop or camera capture with live classification.
* **Interactive Map Pinpoint**: Geolocation detection via browser GPS or interactive Leaflet map pin placement.
* **Complaint Tracking**: Lifecycle timeline (Reported → Verified → Assigned → In Progress → Resolved).
* **Duplicate Awareness**: Clear alerts when a report matches a nearby open complaint.
* **Resolution Verification**: Citizen confirmation actions (`✓ Issue Resolved` or `✗ Issue Still Exists` to reopen).
* **In-App Notification Center**: Real-time alerts on status transitions and department dispatches.
* **Public Civic Map**: View all nearby open civic issues filtered by priority badges.

### Administrator / Authority Console
* **Executive Dashboard**: Key KPIs (Total, Unverified, In Progress, Resolved, Critical Hazard alerts).
* **Visual Analytics (Chart.js)**:
  - Chart 1: Issues by Category (Doughnut)
  - Chart 2: Lifecycle Status Breakdown (Bar)
  - Chart 3: Daily Influx Trend (Line)
  - Chart 4: Priority Distribution (Pie)
* **Master Triage Table**: Advanced multi-attribute search and filtering (Status, Category, Priority, Department).
* **Modal Operations**:
  - One-click complaint verification.
  - Department routing and field dispatch.
  - Priority adjustment with audit logging.
  - Resolution evidence upload (after photograph + remediation note).
* **Department & Category Management**: Dynamic roster configuration.

---

## 6. Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | HTML5, CSS3 (Custom Design System), Vanilla JavaScript |
| **Icons & Fonts** | FontAwesome 6, Google Fonts (Outfit & Inter) |
| **Mapping & GIS** | OpenStreetMap (OSM) Tiles, Leaflet.js |
| **Data Visualization** | Chart.js 4.4 |
| **Backend Framework** | Python 3.11, Flask 3.x, Jinja2 |
| **Authentication & Security** | Werkzeug Security (`generate_password_hash`, `check_password_hash`), Session cookies |
| **AI / Computer Vision** | Pillow, NumPy, Scikit-Learn |
| **Database** | Relational Database (SQLite default for zero-config portability, MySQL fully compatible via PyMySQL) |

---

## 7. System Architecture

```text
[ Citizen Web Client ]          [ Admin Operations Console ]
        |                                   |
        +-----------------+-----------------+
                          |
                   [ Flask Server ]
                          |
       +------------------+------------------+
       |                  |                  |
[ AI Classifier ]   [ Priority Engine ] [ Duplicate Detector ]
(Computer Vision)   (Multi-Factor Score)  (Haversine Distance)
       |                  |                  |
       +------------------+------------------+
                          |
              [ Relational Database ]
         (users, reports, updates, evidence)
```

---

## 8. Database Schema Design

The relational database comprises 7 structured tables:
1. `users`: Stores user credentials (`id`, `name`, `email`, `phone`, `password`, `role`).
2. `departments`: Municipal operational units (`Road Maintenance`, `Sanitation`, `Electrical`, etc.).
3. `categories`: Civic issue domains mapped to default departments.
4. `reports`: Central complaints table (`complaint_id`, `category`, `description`, `image_path`, `latitude`, `longitude`, `priority`, `priority_score`, `priority_reason`, `ai_prediction`, `ai_confidence`, `status`, `department_id`, `is_duplicate`).
5. `report_updates`: Comprehensive audit trail of every status transition and remark.
6. `notifications`: In-app alerts for status transitions.
7. `resolutions`: Stores completion proof (`resolution_image`, `resolution_note`, `resolved_by`, `resolved_at`).
8. `duplicate_links`: Stores spatial proximity linkages and similarity percentages.

---

## 9. AI & Data Science Component

### Computer Vision Visual Feature Extraction
The AI engine (`services/ai_classifier.py`) extracts multidimensional visual descriptors from civic defect photographs:
- **Asphalt & Concrete Ratio**: Evaluates low-saturation mid-gray pixel densities characteristic of road surfaces.
- **Surface Depression Factor**: Measures localized dark tonal clusters indicative of potholes.
- **Spatial Edge Energy**: Computes discrete first-order gradients measuring surface fracture roughness (distinguishes smooth asphalt from cracked roads).
- **Chromatic Entropy & Clutter**: Detects high-variance color distributions typical of uncollected solid waste dumps.
- **Foliage Index**: Analyzes green spectral dominance for fallen trees and vegetative obstructions.
- **Specular Reflectance**: Evaluates water reflections for pipeline ruptures and drainage overflows.
- **Calibrated Softmax Output**: Returns top-3 predicted classes with calibrated confidence scores (e.g., 91.8%).

### Mathematical Formulation of Intelligent Priority
The dynamic priority score $P \in [0, 105]$ is formulated as:
$$P = W_{\text{category}} + W_{\text{severity}} + S_{\text{density}} + S_{\text{safety}} + S_{\text{aging}}$$

* $W_{\text{category}} \in [10, 26]$: Inherent hazard weight (Broken streetlight at night = 22, Pothole = 25, Fallen tree = 26).
* $W_{\text{severity}} \in [6, 30]$: Citizen-selected severity (Low = 6, Medium = 14, High = 22, Critical = 30).
* $S_{\text{density}} \in [0, 20]$: Number of concurrent active complaints within 300m radius via Haversine distance.
* $S_{\text{safety}} \in [0, 15]$: NLP keyword presence (e.g., *school*, *hospital*, *highway*, *danger*, *live wire*).
* $S_{\text{aging}} \in [0, 10]$: Auto-escalation score based on ticket age.

**Priority Thresholds:**
- $P \ge 75 \implies \mathbf{CRITICAL}$ (Red Badge)
- $P \ge 50 \implies \mathbf{HIGH}$ (Orange Badge)
- $P \ge 30 \implies \mathbf{MEDIUM}$ (Yellow Badge)
- $P < 30 \implies \mathbf{LOW}$ (Green Badge)

---

## 10. Installation & Setup Instructions

### Prerequisites
- Python 3.10+ or Python 3.11 installed.

### Step 1: Clone or Navigate to Directory
```bash
cd "Mini project 2"
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Populate Demo Seed Data
Run the automated seeder to initialize tables and load demo complaints, departments, and credentials:
```bash
python demo_data.py
```

### Step 4: Run the Application
```bash
python app.py
```
Open your browser at: `http://127.0.0.1:5000`

---

## 11. Sample Credentials

| Role | Email | Password | Access Portal |
|---|---|---|---|
| **Citizen** | `citizen@example.com` | `Citizen@123` | `/login` |
| **Administrator** | `admin@civicfix.gov` | `Admin@123` | `/admin/login` |

*(Quick "Auto-Fill" buttons are provided on both login pages for effortless demonstration).*

---

## 12. Standard Demo Workflow (Final Presentation)

1. **Step 1: Citizen Login**: Login with `citizen@example.com`.
2. **Step 2: File Complaint**: Click `+ Report New Issue`.
3. **Step 3: Upload Image**: Select a pothole photo. Watch the AI Computer Vision engine diagnose `Pothole` with ~93% confidence and auto-select the category.
4. **Step 4: Geotag**: Click `Detect My Current Location` or click on the Leaflet map to set coordinates.
5. **Step 5: Dynamic Priority**: Submit the report. Notice the system generates complaint ID `CIV-2026-00007` and computes priority `HIGH`.
6. **Step 6: Authority Login**: Sign out and sign in as `admin@civicfix.gov`.
7. **Step 7: Dashboard Analytics**: View updated charts (Category, Status, Time Influx, Priority).
8. **Step 8: Triage**: In `Manage Issues`, click **Verify** on the new ticket, then click **Assign** to route to `Road Maintenance`.
9. **Step 9: Resolution Evidence**: Click **Resolve**, upload the completion photo (After) and write remediation notes.
10. **Step 10: Citizen Confirmation**: Log back in as citizen, view side-by-side Before/After evidence, and click `✓ Issue Resolved`.

---

## 13. Future Enhancements
- Integration of Deep Learning Convolutional Neural Networks (YOLOv8 / ResNet50) for fine-grained bounding-box damage localization.
- Automated SMS / WhatsApp status notification webhooks via municipal gateways.
- Multi-lingual voice-to-text complaint logging for rural citizens.
- IoT sensor integration into municipal streetlights and drainage channels for automated fault reporting.

---

## 14. Project Credits
**CivicFix Academic Project Team**
* Department of Artificial Intelligence and Data Science
* 3rd-Year B.Tech Mini-Project 2026
