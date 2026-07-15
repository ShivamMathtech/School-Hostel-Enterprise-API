from datetime import date, timedelta


def test_complete_school_hostel_lifecycle(client, auth_headers):
    grade_response = client.post(
        "/api/v1/academics/grades",
        headers=auth_headers,
        json={"name": "9", "section": "B", "academic_year": "2026-27"},
    )
    assert grade_response.status_code == 201, grade_response.text
    grade_id = grade_response.json()["id"]

    student_response = client.post(
        "/api/v1/students",
        headers=auth_headers,
        json={
            "admission_no": "ADM-TEST-001",
            "first_name": "Riya",
            "last_name": "Singh",
            "date_of_birth": "2012-03-12",
            "gender": "female",
            "grade_id": grade_id,
            "guardian_name": "Anita Singh",
            "guardian_phone": "+91-9000000011",
            "guardian_email": "anita@example.com",
        },
    )
    assert student_response.status_code == 201, student_response.text
    student_id = student_response.json()["id"]

    attendance_response = client.post(
        "/api/v1/attendance/bulk",
        headers=auth_headers,
        json={
            "records": [
                {
                    "student_id": student_id,
                    "attendance_date": str(date.today()),
                    "status": "present",
                    "remarks": "On time",
                }
            ]
        },
    )
    assert attendance_response.status_code == 200, attendance_response.text

    building_response = client.post(
        "/api/v1/hostel/buildings",
        headers=auth_headers,
        json={"name": "Girls Hostel Test", "gender_type": "female", "address": "South Campus"},
    )
    assert building_response.status_code == 201, building_response.text
    building_id = building_response.json()["id"]

    room_response = client.post(
        "/api/v1/hostel/rooms",
        headers=auth_headers,
        json={
            "building_id": building_id,
            "room_no": "201",
            "floor": 2,
            "capacity": 2,
            "monthly_fee": "5000.00",
        },
    )
    assert room_response.status_code == 201, room_response.text
    room_id = room_response.json()["id"]

    beds_response = client.get(f"/api/v1/hostel/beds?room_id={room_id}", headers=auth_headers)
    assert beds_response.status_code == 200
    assert len(beds_response.json()) == 2
    bed_id = beds_response.json()[0]["id"]

    allocation_response = client.post(
        "/api/v1/hostel/allocations",
        headers=auth_headers,
        json={
            "student_id": student_id,
            "bed_id": bed_id,
            "start_date": str(date.today()),
            "deposit_amount": "10000.00",
        },
    )
    assert allocation_response.status_code == 201, allocation_response.text
    allocation_id = allocation_response.json()["id"]

    invoice_response = client.post(
        "/api/v1/fees/invoices",
        headers=auth_headers,
        json={
            "student_id": student_id,
            "fee_type": "Hostel Fee",
            "billing_period": "July 2026",
            "amount": "5000.00",
            "due_date": str(date.today() + timedelta(days=7)),
        },
    )
    assert invoice_response.status_code == 201, invoice_response.text
    invoice_id = invoice_response.json()["id"]

    payment_response = client.post(
        f"/api/v1/fees/invoices/{invoice_id}/payments",
        headers=auth_headers,
        json={"amount": "5000.00", "payment_method": "upi", "transaction_ref": "UPI-TEST-001"},
    )
    assert payment_response.status_code == 201, payment_response.text

    plan_response = client.post(
        "/api/v1/mess/plans",
        headers=auth_headers,
        json={
            "name": "Test Full Meal Plan",
            "monthly_fee": "3000.00",
            "meal_schedule": {"breakfast": "08:00", "dinner": "20:00"},
        },
    )
    assert plan_response.status_code == 201, plan_response.text
    plan_id = plan_response.json()["id"]

    subscription_response = client.post(
        "/api/v1/mess/subscriptions",
        headers=auth_headers,
        json={"student_id": student_id, "plan_id": plan_id, "start_date": str(date.today())},
    )
    assert subscription_response.status_code == 201, subscription_response.text

    visitor_response = client.post(
        "/api/v1/operations/visitors/check-in",
        headers=auth_headers,
        json={
            "student_id": student_id,
            "visitor_name": "Anita Singh",
            "relation": "Mother",
            "phone": "+91-9000000011",
            "purpose": "Weekend visit",
        },
    )
    assert visitor_response.status_code == 201, visitor_response.text
    visitor_id = visitor_response.json()["id"]
    assert client.post(f"/api/v1/operations/visitors/{visitor_id}/check-out", headers=auth_headers).status_code == 200

    leave_response = client.post(
        "/api/v1/operations/leave-requests",
        headers=auth_headers,
        json={
            "student_id": student_id,
            "from_date": str(date.today() + timedelta(days=1)),
            "to_date": str(date.today() + timedelta(days=3)),
            "reason": "Family function",
        },
    )
    assert leave_response.status_code == 201, leave_response.text
    leave_id = leave_response.json()["id"]
    decision = client.patch(
        f"/api/v1/operations/leave-requests/{leave_id}/decision",
        headers=auth_headers,
        json={"status": "approved", "review_notes": "Guardian verified"},
    )
    assert decision.status_code == 200, decision.text

    complaint_response = client.post(
        "/api/v1/operations/complaints",
        headers=auth_headers,
        json={
            "student_id": student_id,
            "category": "maintenance",
            "description": "Ceiling fan requires service",
            "priority": "high",
        },
    )
    assert complaint_response.status_code == 201, complaint_response.text
    complaint_id = complaint_response.json()["id"]
    update_response = client.patch(
        f"/api/v1/operations/complaints/{complaint_id}",
        headers=auth_headers,
        json={"status": "resolved", "resolution": "Fan capacitor replaced"},
    )
    assert update_response.status_code == 200, update_response.text

    dashboard_response = client.get("/api/v1/admin/dashboard", headers=auth_headers)
    assert dashboard_response.status_code == 200, dashboard_response.text
    dashboard = dashboard_response.json()
    assert dashboard["total_students"] == 1
    assert dashboard["occupied_beds"] == 1
    assert float(dashboard["pending_fee_amount"]) == 0

    checkout_response = client.post(
        f"/api/v1/hostel/allocations/{allocation_id}/checkout",
        headers=auth_headers,
        json={"end_date": str(date.today() + timedelta(days=30)), "checkout_notes": "Room inspected"},
    )
    assert checkout_response.status_code == 200, checkout_response.text


def test_duplicate_transaction_reference_is_rejected(client, auth_headers):
    grade_id = client.post(
        "/api/v1/academics/grades",
        headers=auth_headers,
        json={"name": "8", "section": "A", "academic_year": "2026-27"},
    ).json()["id"]
    student_id = client.post(
        "/api/v1/students",
        headers=auth_headers,
        json={
            "admission_no": "ADM-TEST-002",
            "first_name": "Kabir",
            "last_name": "Kumar",
            "date_of_birth": "2013-01-01",
            "gender": "male",
            "grade_id": grade_id,
            "guardian_name": "Mohan Kumar",
            "guardian_phone": "+91-9000000022",
        },
    ).json()["id"]
    invoice_ids = []
    for number in range(2):
        response = client.post(
            "/api/v1/fees/invoices",
            headers=auth_headers,
            json={
                "student_id": student_id,
                "fee_type": f"Fee {number}",
                "billing_period": "July 2026",
                "amount": "1000.00",
                "due_date": str(date.today() + timedelta(days=5)),
            },
        )
        invoice_ids.append(response.json()["id"])
    first = client.post(
        f"/api/v1/fees/invoices/{invoice_ids[0]}/payments",
        headers=auth_headers,
        json={"amount": "1000.00", "payment_method": "cash", "transaction_ref": "DUP-REF"},
    )
    assert first.status_code == 201
    second = client.post(
        f"/api/v1/fees/invoices/{invoice_ids[1]}/payments",
        headers=auth_headers,
        json={"amount": "1000.00", "payment_method": "cash", "transaction_ref": "DUP-REF"},
    )
    assert second.status_code == 409
