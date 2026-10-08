"""
ACEest Fitness & Gym — Core Web Application
Modular Flask application handling membership, class scheduling, health metrics, and system diagnostics.
"""

import re
from datetime import datetime, timezone
from threading import Lock
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Thread-safe in-memory data store
_lock = Lock()

MEMBERSHIP_PLANS = [
    {
        "id": "starter",
        "name": "Starter Zinc",
        "price": 29.99,
        "billing": "monthly",
        "features": ["Access to Gym Floor", "Locker Room Access", "1 Free Fitness Assessment"],
        "badge": "Popular"
    },
    {
        "id": "pro",
        "name": "Pro Performance",
        "price": 59.99,
        "billing": "monthly",
        "features": [
            "All Starter Features",
            "Unlimited Studio Classes",
            "Sauna & Spa Access",
            "Monthly Nutrition Consultation"
        ],
        "badge": "Recommended"
    },
    {
        "id": "elite",
        "name": "Elite Athlete",
        "price": 99.99,
        "billing": "monthly",
        "features": ["All Pro Features", "Dedicated Personal Trainer", "Custom Meal Plans", "24/7 Priority VIP Access"],
        "badge": "VIP"
    }
]

# Initial Seed Data
INITIAL_MEMBERS = [
    {
        "id": 1,
        "name": "Alex Mercer",
        "email": "alex.mercer@aceest.fit",
        "age": 28,
        "plan": "pro",
        "joined_date": "2026-01-15",
        "status": "Active"
    },
    {
        "id": 2,
        "name": "Sarah Connor",
        "email": "sarah.c@aceest.fit",
        "age": 34,
        "plan": "elite",
        "joined_date": "2026-02-01",
        "status": "Active"
    },
    {
        "id": 3,
        "name": "Marcus Vance",
        "email": "marcus.v@aceest.fit",
        "age": 24,
        "plan": "starter",
        "joined_date": "2026-03-10",
        "status": "Active"
    }
]

INITIAL_CLASSES = [
    {
        "id": "c1",
        "title": "High-Intensity Interval Training (HIIT)",
        "instructor": "Coach Dave",
        "time": "07:00 AM - 08:00 AM",
        "capacity": 20,
        "booked": 14,
        "intensity": "High",
        "category": "Cardio"
    },
    {
        "id": "c2",
        "title": "Powerlifting & Hypertrophy",
        "instructor": "Coach Elena",
        "time": "10:00 AM - 11:30 AM",
        "capacity": 15,
        "booked": 12,
        "intensity": "Extreme",
        "category": "Strength"
    },
    {
        "id": "c3",
        "title": "Mobility & Restorative Yoga",
        "instructor": "Coach Maya",
        "time": "05:30 PM - 06:30 PM",
        "capacity": 25,
        "booked": 19,
        "intensity": "Low",
        "category": "Flexibility"
    },
    {
        "id": "c4",
        "title": "CrossFit Functional Conditioning",
        "instructor": "Coach Jax",
        "time": "07:00 PM - 08:00 PM",
        "capacity": 18,
        "booked": 18,
        "intensity": "High",
        "category": "Conditioning"
    }
]

# State
members = [dict(m) for m in INITIAL_MEMBERS]
classes = [dict(c) for c in INITIAL_CLASSES]
next_member_id = 4


def reset_state():
    """Helper to reset state for test isolations."""
    global members, classes, next_member_id
    with _lock:
        members = [dict(m) for m in INITIAL_MEMBERS]
        classes = [dict(c) for c in INITIAL_CLASSES]
        next_member_id = 4


# -------------------------------------------------------------
# Template Routes (shadcn grey/zinc UI)
# -------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html', plans=MEMBERSHIP_PLANS)


@app.route('/members')
def members_page():
    with _lock:
        current_members = list(members)
    return render_template('members.html', members=current_members, plans=MEMBERSHIP_PLANS)


@app.route('/classes')
def classes_page():
    with _lock:
        current_classes = list(classes)
    return render_template('classes.html', classes=current_classes)


@app.route('/calculator')
def calculator_page():
    return render_template('calculator.html')


# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------

@app.route('/health', methods=['GET'])
def healthcheck():
    """Healthcheck endpoint for Docker & CI quality gates."""
    return jsonify({
        "status": "healthy",
        "service": "aceest-fitness-gym",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200


@app.route('/api/plans', methods=['GET'])
def get_plans():
    return jsonify({"success": True, "data": MEMBERSHIP_PLANS}), 200


@app.route('/api/stats', methods=['GET'])
def get_stats():
    with _lock:
        total_members = len(members)
        active_members = sum(1 for m in members if m.get("status") == "Active")
        total_classes = len(classes)
        total_booked_spots = sum(c.get("booked", 0) for c in classes)
        total_capacity = sum(c.get("capacity", 0) for c in classes)

    return jsonify({
        "success": True,
        "data": {
            "total_members": total_members,
            "active_members": active_members,
            "total_classes": total_classes,
            "total_booked_spots": total_booked_spots,
            "total_capacity": total_capacity,
            "occupancy_rate": round((total_booked_spots / total_capacity * 100), 1) if total_capacity else 0
        }
    }), 200


@app.route('/api/members', methods=['GET'])
def get_members():
    with _lock:
        return jsonify({"success": True, "count": len(members), "data": members}), 200


@app.route('/api/members', methods=['POST'])
def create_member():
    global next_member_id
    payload = request.get_json(silent=True) or {}

    name = str(payload.get('name', '')).strip()
    email = str(payload.get('email', '')).strip()
    age = payload.get('age')
    plan = str(payload.get('plan', 'starter')).strip().lower()

    # Validation
    if not name or not email or age is None:
        return jsonify({
            "success": False,
            "error": "Validation failed: 'name', 'email', and 'age' are required fields."
        }), 400

    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(email_regex, email):
        return jsonify({
            "success": False,
            "error": "Validation failed: Invalid email format."
        }), 400

    try:
        age_int = int(age)
        if age_int < 14 or age_int > 100:
            return jsonify({
                "success": False,
                "error": "Validation failed: Member age must be between 14 and 100."
            }), 400
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "error": "Validation failed: Age must be an integer."
        }), 400

    valid_plans = [p['id'] for p in MEMBERSHIP_PLANS]
    if plan not in valid_plans:
        plan = 'starter'

    with _lock:
        # Check duplicate email
        if any(m['email'].lower() == email.lower() for m in members):
            return jsonify({
                "success": False,
                "error": f"Member with email '{email}' already exists."
            }), 409

        new_member = {
            "id": next_member_id,
            "name": name,
            "email": email,
            "age": age_int,
            "plan": plan,
            "joined_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "status": "Active"
        }
        next_member_id += 1
        members.append(new_member)

    return jsonify({
        "success": True,
        "message": "Member registered successfully.",
        "data": new_member
    }), 201


@app.route('/api/members/<int:member_id>', methods=['DELETE'])
def delete_member(member_id):
    with _lock:
        for idx, m in enumerate(members):
            if m['id'] == member_id:
                deleted = members.pop(idx)
                return jsonify({
                    "success": True,
                    "message": f"Member {member_id} removed.",
                    "data": deleted
                }), 200

    return jsonify({
        "success": False,
        "error": f"Member with ID {member_id} not found."
    }), 404


@app.route('/api/classes', methods=['GET'])
def get_classes():
    with _lock:
        return jsonify({"success": True, "count": len(classes), "data": classes}), 200


@app.route('/api/classes/book', methods=['POST'])
def book_class():
    payload = request.get_json(silent=True) or {}
    class_id = str(payload.get('class_id', '')).strip()

    if not class_id:
        return jsonify({"success": False, "error": "Missing 'class_id' parameter."}), 400

    with _lock:
        target = next((c for c in classes if c['id'] == class_id), None)
        if not target:
            return jsonify({"success": False, "error": f"Class '{class_id}' not found."}), 404

        if target['booked'] >= target['capacity']:
            return jsonify({
                "success": False,
                "error": f"Class '{target['title']}' is currently fully booked."
            }), 400

        target['booked'] += 1
        updated = dict(target)

    return jsonify({
        "success": True,
        "message": f"Spot successfully booked for '{updated['title']}'!",
        "data": updated
    }), 200


@app.route('/api/calculator/bmi', methods=['POST'])
def calculate_bmi():
    """
    Calculate Body Mass Index (BMI) and daily caloric maintenance baseline.
    Payload: {"weight_kg": float, "height_cm": float, "age": int, "gender": "male"|"female"}
    """
    payload = request.get_json(silent=True) or {}
    try:
        weight = float(payload.get('weight_kg', 0))
        height_cm = float(payload.get('height_cm', 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Weight and height must be valid numeric values."}), 400

    if weight <= 0 or height_cm <= 0:
        return jsonify({"success": False, "error": "Weight and height must be strictly greater than 0."}), 400

    if height_cm < 50 or height_cm > 280 or weight < 20 or weight > 350:
        return jsonify({"success": False, "error": "Values out of realistic biological human bounds."}), 400

    height_m = height_cm / 100.0
    bmi = round(weight / (height_m ** 2), 2)

    if bmi < 18.5:
        category = "Underweight"
        recommendation = "Focus on nutrient-dense calorie surplus and progressive strength hypertrophy training."
    elif bmi < 24.9:
        category = "Normal weight"
        recommendation = "Optimal baseline. Maintain balanced macronutrient intake and hybrid conditioning."
    elif bmi < 29.9:
        category = "Overweight"
        recommendation = (
            "Incorporate moderate calorie deficit, high protein intake, "
            "and consistent resistance + HIIT training."
        )
    else:
        category = "Obese"
        recommendation = (
            "Consult with ACEest personal coach and medical practitioner "
            "for a structured metabolic reboot plan."
        )

    # Estimated BMR using Mifflin-St Jeor equation (baseline approximation)
    bmr = round(10 * weight + 6.25 * height_cm - 5 * 25 + 5, 0)

    return jsonify({
        "success": True,
        "data": {
            "bmi": bmi,
            "category": category,
            "recommendation": recommendation,
            "estimated_bmr_kcal": bmr
        }
    }), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
