from datetime import datetime, date
from werkzeug.security import check_password_hash, generate_password_hash

from . import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    location = db.Column(db.String(120), nullable=True)


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), unique=True, nullable=False)
    level = db.Column(db.String(50), nullable=True)


class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(50))
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(50), default="active")

    department_id = db.Column(db.Integer, db.ForeignKey("department.id"))
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"))
    manager_id = db.Column(db.Integer, db.ForeignKey("employee.id"))

    department = db.relationship("Department", backref="employees")
    role = db.relationship("Role", backref="employees")
    manager = db.relationship("Employee", remote_side=[id])

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class TimeOffRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(50), nullable=False, default="pto")
    status = db.Column(db.String(50), nullable=False, default="pending")
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship("Employee", backref="time_off_requests")


class PayrollEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    pay_date = db.Column(db.Date, nullable=False)
    gross_pay = db.Column(db.Numeric(10, 2), nullable=False)
    taxes = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    bonus = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    status = db.Column(db.String(50), nullable=False, default="scheduled")
    notes = db.Column(db.Text, nullable=True)

    employee = db.relationship("Employee", backref="payroll_entries")

    @property
    def net_pay(self):
        return float(self.gross_pay or 0) - float(self.taxes or 0) + float(self.bonus or 0)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default="planned")
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)


class ProjectAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    role = db.Column(db.String(120), nullable=True)
    allocation = db.Column(db.Integer, nullable=True)  # percentage

    project = db.relationship("Project", backref="assignments")
    employee = db.relationship("Employee", backref="assignments")


class AttendanceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    work_date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.Time, nullable=True)
    check_out = db.Column(db.Time, nullable=True)
    status = db.Column(db.String(40), nullable=False, default="present")
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship("Employee", backref="attendance_logs")

    @property
    def hours(self):
        if not self.check_in or not self.check_out:
            return None
        delta = datetime.combine(date.today(), self.check_out) - datetime.combine(date.today(), self.check_in)
        return round(delta.total_seconds() / 3600, 2)


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChannelMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(80), nullable=False, default="general")
    message = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PerformanceReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    reviewer = db.Column(db.String(120), nullable=True)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    rating = db.Column(db.String(20), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    goals = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(40), nullable=False, default="draft")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship("Employee", backref="performance_reviews")


class OnboardingTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(40), nullable=False, default="open")
    due_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship("Employee", backref="onboarding_tasks")


class BenefitEnrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    benefit_type = db.Column(db.String(120), nullable=False)
    provider = db.Column(db.String(120), nullable=True)
    coverage = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(40), nullable=False, default="active")
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)

    employee = db.relationship("Employee", backref="benefit_enrollments")


class Recognition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    from_person = db.Column(db.String(120), nullable=True)
    badge = db.Column(db.String(80), nullable=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship("Employee", backref="recognitions")
