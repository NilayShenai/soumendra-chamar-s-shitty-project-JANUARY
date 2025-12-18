from datetime import date, timedelta, datetime

from . import db
from .models import (
    User,
    Department,
    Role,
    Employee,
    TimeOffRequest,
    PayrollEntry,
    Project,
    ProjectAssignment,
    AttendanceLog,
    Announcement,
    ChannelMessage,
    PerformanceReview,
    OnboardingTask,
    BenefitEnrollment,
    Recognition,
)


def seed_data() -> None:
    db.create_all()

    # reset people and related records to match requested roster
    AttendanceLog.query.delete()
    Recognition.query.delete()
    BenefitEnrollment.query.delete()
    OnboardingTask.query.delete()
    PerformanceReview.query.delete()
    ChannelMessage.query.delete()
    Announcement.query.delete()
    ProjectAssignment.query.delete()
    Project.query.delete()
    PayrollEntry.query.delete()
    TimeOffRequest.query.delete()
    Employee.query.delete()

    admin = User.query.filter_by(email="admin@local").first()
    if not admin:
        admin = User(email="admin@local", full_name="Admin User")
        admin.set_password("admin123")
        db.session.add(admin)

    departments = [
        ("Engineering", "Remote"),
        ("People", "NYC"),
        ("Finance", "Chicago"),
    ]
    for name, location in departments:
        if not Department.query.filter_by(name=name).first():
            db.session.add(Department(name=name, location=location))

    roles = [
        ("Software Engineer", "IC3"),
        ("Engineering Manager", "M2"),
        ("HR Partner", "IC2"),
        ("Controller", "M1"),
    ]
    for title, level in roles:
        if not Role.query.filter_by(title=title).first():
            db.session.add(Role(title=title, level=level))

    db.session.flush()

    engineering = Department.query.filter_by(name="Engineering").first()
    people = Department.query.filter_by(name="People").first()
    finance = Department.query.filter_by(name="Finance").first()

    eng_manager = Role.query.filter_by(title="Engineering Manager").first()
    engineer = Role.query.filter_by(title="Software Engineer").first()
    hr_partner = Role.query.filter_by(title="HR Partner").first()
    controller = Role.query.filter_by(title="Controller").first()

    employees = [
        {
            "first_name": "Soumendra",
            "last_name": "",
            "email": "soumendra@january.local",
            "phone": "555-1101",
            "start_date": date.today() - timedelta(days=360),
            "department": engineering,
            "role": eng_manager,
            "status": "active",
        },
        {
            "first_name": "Saksham",
            "last_name": "",
            "email": "saksham@january.local",
            "phone": "555-1102",
            "start_date": date.today() - timedelta(days=290),
            "department": engineering,
            "role": engineer,
            "status": "active",
            "manager": None,
        },
        {
            "first_name": "Srajan",
            "last_name": "",
            "email": "srajan@january.local",
            "phone": "555-1103",
            "start_date": date.today() - timedelta(days=220),
            "department": people,
            "role": hr_partner,
            "status": "active",
        },
        {
            "first_name": "Gautami",
            "last_name": "",
            "email": "gautami@january.local",
            "phone": "555-1104",
            "start_date": date.today() - timedelta(days=440),
            "department": finance,
            "role": controller,
            "status": "active",
        },
        {
            "first_name": "Sravani",
            "last_name": "",
            "email": "sravani@january.local",
            "phone": "555-1105",
            "start_date": date.today() - timedelta(days=180),
            "department": people,
            "role": hr_partner,
            "status": "on-leave",
        },
    ]

    for data in employees:
        if not Employee.query.filter_by(email=data["email"]).first():
            employee = Employee(**data)
            db.session.add(employee)

    db.session.flush()

    soumendra = Employee.query.filter_by(email="soumendra@january.local").first()
    saksham = Employee.query.filter_by(email="saksham@january.local").first()
    sravani = Employee.query.filter_by(email="sravani@january.local").first()

    projects = [
        {
            "name": "Atlas Revamp",
            "description": "Rebuild onboarding to cut time-to-value.",
            "status": "active",
            "start_date": date.today() - timedelta(days=45),
            "end_date": None,
        },
        {
            "name": "Northwind Migration",
            "description": "Finance systems consolidation for Q1 close.",
            "status": "planned",
            "start_date": date.today() + timedelta(days=20),
            "end_date": None,
        },
    ]

    for proj in projects:
        if not Project.query.filter_by(name=proj["name"]).first():
            db.session.add(Project(**proj))

    db.session.flush()

    atlas = Project.query.filter_by(name="Atlas Revamp").first()
    northwind = Project.query.filter_by(name="Northwind Migration").first()

    assignments = [
        {"project": atlas, "employee": soumendra, "role": "Lead", "allocation": 80},
        {"project": atlas, "employee": saksham, "role": "Engineer", "allocation": 70},
        {"project": northwind, "employee": sravani, "role": "Change partner", "allocation": 50},
    ]

    for assign in assignments:
        if assign["project"] and assign["employee"]:
            exists = ProjectAssignment.query.filter_by(
                project_id=assign["project"].id,
                employee_id=assign["employee"].id,
            ).first()
            if not exists:
                db.session.add(ProjectAssignment(**assign))

    requests = [
        {
            "employee": soumendra,
            "start_date": date.today() + timedelta(days=5),
            "end_date": date.today() + timedelta(days=8),
            "category": "pto",
            "status": "pending",
            "note": "Festival travel",
        },
        {
            "employee": saksham,
            "start_date": date.today() + timedelta(days=12),
            "end_date": date.today() + timedelta(days=15),
            "category": "sick",
            "status": "approved",
            "note": "Recovery",
        },
        {
            "employee": sravani,
            "start_date": date.today() + timedelta(days=20),
            "end_date": date.today() + timedelta(days=23),
            "category": "unpaid",
            "status": "pending",
            "note": "Family visit",
        },
    ]

    for req in requests:
        exists = TimeOffRequest.query.filter_by(
            employee_id=req["employee"].id,
            start_date=req["start_date"],
            end_date=req["end_date"],
        ).first()
        if not exists:
            db.session.add(TimeOffRequest(**req))

    payroll_entries = [
        {
            "employee": soumendra,
            "period_start": date.today() - timedelta(days=30),
            "period_end": date.today() - timedelta(days=16),
            "pay_date": date.today() - timedelta(days=10),
            "gross_pay": 9200.00,
            "taxes": 2100.00,
            "bonus": 600.00,
            "status": "paid",
            "notes": "Product milestone bonus",
        },
        {
            "employee": saksham,
            "period_start": date.today() - timedelta(days=30),
            "period_end": date.today() - timedelta(days=16),
            "pay_date": date.today() - timedelta(days=10),
            "gross_pay": 6400.00,
            "taxes": 1500.00,
            "bonus": 350.00,
            "status": "paid",
            "notes": "Sprint completion",
        },
        {
            "employee": sravani,
            "period_start": date.today() - timedelta(days=15),
            "period_end": date.today() - timedelta(days=1),
            "pay_date": date.today() + timedelta(days=4),
            "gross_pay": 5800.00,
            "taxes": 1200.00,
            "bonus": 0.00,
            "status": "scheduled",
            "notes": "Payroll queued",
        },
    ]

    for entry in payroll_entries:
        if entry["employee"]:
            exists = PayrollEntry.query.filter_by(
                employee_id=entry["employee"].id,
                period_start=entry["period_start"],
                period_end=entry["period_end"],
            ).first()
            if not exists:
                db.session.add(PayrollEntry(**entry))

    attendance_logs = [
        {
            "employee": soumendra,
            "work_date": date.today(),
            "check_in": datetime.strptime("09:00", "%H:%M").time(),
            "check_out": datetime.strptime("17:30", "%H:%M").time(),
            "status": "present",
            "notes": "Product review",
        },
        {
            "employee": saksham,
            "work_date": date.today(),
            "check_in": datetime.strptime("09:15", "%H:%M").time(),
            "check_out": datetime.strptime("18:00", "%H:%M").time(),
            "status": "remote",
            "notes": "Remote pairing",
        },
        {
            "employee": sravani,
            "work_date": date.today(),
            "check_in": None,
            "check_out": None,
            "status": "leave",
            "notes": "Visiting family",
        },
    ]

    for log in attendance_logs:
        if log["employee"]:
            exists = AttendanceLog.query.filter_by(
                employee_id=log["employee"].id,
                work_date=log["work_date"],
            ).first()
            if not exists:
                db.session.add(AttendanceLog(**log))

    announcements = [
        {"title": "Welcome to January", "body": "New navigation and attendance tracking are live.", "author": "Ops"},
        {"title": "Benefits window", "body": "Open enrollment closes Friday.", "author": "People"},
    ]
    for ann in announcements:
        if not Announcement.query.filter_by(title=ann["title"]).first():
            db.session.add(Announcement(**ann))

    messages = [
        {"channel": "general", "message": "Great work on Atlas Revamp!", "author": "Soumendra"},
        {"channel": "finance", "message": "Northwind migration kickoff next week.", "author": "Gautami"},
    ]
    for msg in messages:
        db.session.add(ChannelMessage(**msg))

    reviews = [
        {
            "employee": soumendra,
            "reviewer": "CTO",
            "period_start": date.today() - timedelta(days=180),
            "period_end": date.today(),
            "rating": "Exceeds",
            "status": "submitted",
            "summary": "Led Atlas and hit milestones.",
            "goals": "Stabilize onboarding latency.",
        },
        {
            "employee": saksham,
            "reviewer": "Eng Manager",
            "period_start": date.today() - timedelta(days=180),
            "period_end": date.today(),
            "rating": "Meets",
            "status": "in-review",
            "summary": "Strong delivery and pairing.",
            "goals": "Improve incident response.",
        },
    ]
    for r in reviews:
        if r["employee"] and not PerformanceReview.query.filter_by(employee_id=r["employee"].id, period_start=r["period_start"], period_end=r["period_end"]).first():
            db.session.add(PerformanceReview(**r))

    onboarding_tasks = [
        {"employee": saksham, "title": "Laptop setup", "status": "done", "due_date": date.today() - timedelta(days=150), "notes": "Completed"},
        {"employee": sravani, "title": "HR orientation", "status": "open", "due_date": date.today() + timedelta(days=2), "notes": "Schedule with People"},
    ]
    for t in onboarding_tasks:
        if t["employee"]:
            db.session.add(OnboardingTask(**t))

    benefits = [
        {
            "employee": soumendra,
            "benefit_type": "Health",
            "provider": "Acme Health",
            "coverage": "Gold",
            "status": "active",
            "start_date": date.today() - timedelta(days=200),
            "end_date": None,
        },
        {
            "employee": sravani,
            "benefit_type": "Dental",
            "provider": "BrightSmiles",
            "coverage": "Standard",
            "status": "pending",
            "start_date": date.today() + timedelta(days=10),
            "end_date": None,
        },
    ]
    for b in benefits:
        if b["employee"]:
            db.session.add(BenefitEnrollment(**b))

    recognitions = [
        {"employee": saksham, "from_person": "Soumendra", "badge": "Kudos", "message": "Great pairing on Atlas."},
        {"employee": sravani, "from_person": "People Team", "badge": "Gratitude", "message": "Thanks for supporting change management."},
    ]
    for r in recognitions:
        if r["employee"]:
            db.session.add(Recognition(**r))

    db.session.commit()
