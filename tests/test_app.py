"""
Unit test suite for ACEest Fitness & Gym Flask Application.
Utilizes pytest and Flask test client to validate functionality, edge cases, and API integrity.
"""

import pytest
from app import app, reset_state


@pytest.fixture(autouse=True)
def run_before_and_after_tests():
    """Ensure in-memory state is clean before each test runs."""
    reset_state()
    yield
    reset_state()


@pytest.fixture
def client():
    """Flask test client fixture."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# =====================================================================
# UI & Template Route Tests
# =====================================================================

def test_index_route(client):
    """Test landing page loads with HTTP 200 and gym branding."""
    res = client.get('/')
    assert res.status_code == 200
    assert b"ACEest Fitness" in res.data
    assert b"Tiered Membership Plans" in res.data


def test_members_route(client):
    """Test members management page loads."""
    res = client.get('/members')
    assert res.status_code == 200
    assert b"Member Management" in res.data


def test_classes_route(client):
    """Test studio classes page loads."""
    res = client.get('/classes')
    assert res.status_code == 200
    assert b"Studio Class Schedules" in res.data


def test_calculator_route(client):
    """Test health metrics calculator page loads."""
    res = client.get('/calculator')
    assert (
        b"Health Metrics &amp; Metabolic Assessment" in res.data
        or b"Health Metrics & Metabolic Assessment" in res.data
    )


# =====================================================================
# Healthcheck & Diagnostic Tests
# =====================================================================

def test_healthcheck_endpoint(client):
    """Verify healthcheck endpoint returns healthy status for container probes."""
    res = client.get('/health')
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['status'] == 'healthy'
    assert json_data['service'] == 'aceest-fitness-gym'
    assert 'timestamp' in json_data


# =====================================================================
# Membership Plans API Tests
# =====================================================================

def test_get_plans_api(client):
    """Verify membership tiers retrieval."""
    res = client.get('/api/plans')
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['success'] is True
    assert len(json_data['data']) >= 3
    plan_ids = [p['id'] for p in json_data['data']]
    assert 'starter' in plan_ids
    assert 'pro' in plan_ids
    assert 'elite' in plan_ids


# =====================================================================
# Stats API Tests
# =====================================================================

def test_get_stats_api(client):
    """Verify aggregated statistics calculation."""
    res = client.get('/api/stats')
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['success'] is True
    stats = json_data['data']
    assert stats['total_members'] == 3
    assert stats['active_members'] == 3
    assert stats['total_classes'] == 4
    assert stats['occupancy_rate'] > 0


# =====================================================================
# Members Management API Tests
# =====================================================================

def test_get_members_list(client):
    """Verify list of all registered gym members."""
    res = client.get('/api/members')
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['success'] is True
    assert json_data['count'] == 3
    assert len(json_data['data']) == 3


def test_create_member_success(client):
    """Verify successful member creation with valid payload."""
    payload = {
        "name": "Bruce Wayne",
        "email": "bruce.wayne@aceest.fit",
        "age": 32,
        "plan": "elite"
    }
    res = client.post('/api/members', json=payload)
    assert res.status_code == 201
    json_data = res.get_json()
    assert json_data['success'] is True
    assert json_data['data']['name'] == "Bruce Wayne"
    assert json_data['data']['email'] == "bruce.wayne@aceest.fit"
    assert json_data['data']['id'] == 4

    # Verify count increased
    verify_res = client.get('/api/members')
    assert verify_res.get_json()['count'] == 4


def test_create_member_missing_fields(client):
    """Validation test: rejection when required fields are missing."""
    res = client.post('/api/members', json={"name": "Incomplete User"})
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data['success'] is False
    assert "required" in json_data['error']


def test_create_member_invalid_email(client):
    """Validation test: rejection of malformed email addresses."""
    payload = {
        "name": "Invalid Email User",
        "email": "not-an-email",
        "age": 25,
        "plan": "starter"
    }
    res = client.post('/api/members', json=payload)
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data['success'] is False
    assert "Invalid email format" in json_data['error']


def test_create_member_invalid_age(client):
    """Validation test: rejection of out-of-bounds age values."""
    payload = {
        "name": "Underage Kid",
        "email": "kid@aceest.fit",
        "age": 10,
        "plan": "starter"
    }
    res = client.post('/api/members', json=payload)
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data['success'] is False
    assert "Member age must be between 14 and 100" in json_data['error']


def test_create_member_duplicate_email(client):
    """Validation test: rejection of duplicate member emails."""
    payload = {
        "name": "Duplicate Person",
        "email": "alex.mercer@aceest.fit",  # Already present in initial seeds
        "age": 30,
        "plan": "pro"
    }
    res = client.post('/api/members', json=payload)
    assert res.status_code == 409
    json_data = res.get_json()
    assert json_data['success'] is False
    assert "already exists" in json_data['error']


def test_delete_member_success(client):
    """Verify deletion of an existing member."""
    res = client.delete('/api/members/1')
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['success'] is True
    assert json_data['data']['id'] == 1

    # Verify count decremented
    verify_res = client.get('/api/members')
    assert verify_res.get_json()['count'] == 2


def test_delete_member_not_found(client):
    """Verify 404 response when attempting to delete non-existent member."""
    res = client.delete('/api/members/999')
    assert res.status_code == 404
    json_data = res.get_json()
    assert json_data['success'] is False
    assert "not found" in json_data['error']


# =====================================================================
# Studio Class Scheduling API Tests
# =====================================================================

def test_get_classes(client):
    """Verify studio classes list retrieval."""
    res = client.get('/api/classes')
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['success'] is True
    assert json_data['count'] == 4


def test_book_class_success(client):
    """Verify booking a spot in a class with available capacity."""
    res = client.post('/api/classes/book', json={"class_id": "c1"})
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['success'] is True
    # Initial booked spots for c1 is 14; should now be 15
    assert json_data['data']['booked'] == 15


def test_book_class_not_found(client):
    """Verify booking non-existent class returns 404."""
    res = client.post('/api/classes/book', json={"class_id": "unknown_id"})
    assert res.status_code == 404
    assert res.get_json()['success'] is False


def test_book_class_fully_booked(client):
    """Verify booking a fully booked class returns 400 error."""
    # c4 has capacity 18 and booked 18 initially
    res = client.post('/api/classes/book', json={"class_id": "c4"})
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data['success'] is False
    assert "fully booked" in json_data['error']


# =====================================================================
# BMI and Health Metrics Calculator API Tests
# =====================================================================

def test_bmi_calculator_normal_weight(client):
    """Verify BMI and caloric estimation for normal weight."""
    payload = {"weight_kg": 70, "height_cm": 175, "age": 25}
    res = client.post('/api/calculator/bmi', json=payload)
    assert res.status_code == 200
    data = res.get_json()['data']
    assert data['bmi'] == 22.86
    assert data['category'] == "Normal weight"
    assert data['estimated_bmr_kcal'] > 0


def test_bmi_calculator_underweight(client):
    """Verify BMI categorization for underweight status."""
    payload = {"weight_kg": 45, "height_cm": 170}
    res = client.post('/api/calculator/bmi', json=payload)
    assert res.status_code == 200
    data = res.get_json()['data']
    assert data['bmi'] < 18.5
    assert data['category'] == "Underweight"


def test_bmi_calculator_overweight(client):
    """Verify BMI categorization for overweight status."""
    payload = {"weight_kg": 85, "height_cm": 175}
    res = client.post('/api/calculator/bmi', json=payload)
    assert res.status_code == 200
    data = res.get_json()['data']
    assert 25.0 <= data['bmi'] <= 29.9
    assert data['category'] == "Overweight"


def test_bmi_calculator_invalid_inputs(client):
    """Verify zero or negative inputs are rejected."""
    res = client.post('/api/calculator/bmi', json={"weight_kg": -10, "height_cm": 170})
    assert res.status_code == 400
    assert res.get_json()['success'] is False

    res_zero = client.post('/api/calculator/bmi', json={"weight_kg": 70, "height_cm": 0})
    assert res_zero.status_code == 400
    assert res_zero.get_json()['success'] is False


def test_bmi_calculator_non_numeric(client):
    """Verify non-numeric values are rejected."""
    res = client.post('/api/calculator/bmi', json={"weight_kg": "abc", "height_cm": "xyz"})
    assert res.status_code == 400
    assert res.get_json()['success'] is False
