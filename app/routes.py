import os
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify

from . import db
from .models import (
    Employee,
    Department,
    Role,
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
from .utils import login_required


def _get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None, "Missing GEMINI_API_KEY"
    try:
        from google import genai
    except ImportError as err:
        return None, f"Gemini client not installed: {err}"

    try:
        client = genai.Client(api_key=api_key)
    except Exception as err:
        return None, f"Gemini client init failed: {err}"

    model_id = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    return (client, model_id), None

bp = Blueprint("main", __name__)


@bp.route("/")
@login_required
def dashboard():
    employee_count = Employee.query.count()
    department_count = Department.query.count()
    pending_requests = TimeOffRequest.query.filter_by(status="pending").count()
    recent_requests = TimeOffRequest.query.order_by(TimeOffRequest.created_at.desc()).limit(5).all()
    open_payroll = PayrollEntry.query.filter_by(status="scheduled").count()
    active_projects = Project.query.filter(Project.status != "done").count()
    todays_logs = AttendanceLog.query.filter_by(work_date=date.today()).count()
    return render_template(
        "dashboard.html",
        employee_count=employee_count,
        department_count=department_count,
        pending_requests=pending_requests,
        recent_requests=recent_requests,
        open_payroll=open_payroll,
        active_projects=active_projects,
        todays_logs=todays_logs,
    )


@bp.route("/employees")
@login_required
def employees():
    employees_list = Employee.query.order_by(Employee.last_name.asc()).all()
    roles = Role.query.order_by(Role.title.asc()).all()
    departments = Department.query.order_by(Department.name.asc()).all()
    return render_template(
        "employees/list.html",
        employees=employees_list,
        roles=roles,
        departments=departments,
    )


@bp.route("/employees/new", methods=["GET", "POST"])
@login_required
def new_employee():
    roles = Role.query.order_by(Role.title.asc()).all()
    departments = Department.query.order_by(Department.name.asc()).all()
    managers = Employee.query.order_by(Employee.last_name.asc()).all()

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        start_date_raw = request.form.get("start_date", "")
        department_id = request.form.get("department_id") or None
        role_id = request.form.get("role_id") or None
        manager_id = request.form.get("manager_id") or None

        try:
            start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date()
        except ValueError:
            start_date = None

        if not all([first_name, last_name, email, start_date]):
            flash("First name, last name, email, and start date are required.", "danger")
            return render_template(
                "employees/form.html",
                roles=roles,
                departments=departments,
                managers=managers,
            )

        employee = Employee(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            start_date=start_date,
            department_id=department_id,
            role_id=role_id,
            manager_id=manager_id,
        )
        db.session.add(employee)
        db.session.commit()
        flash("Employee created.", "success")
        return redirect(url_for("main.employees"))

    return render_template(
        "employees/form.html",
        roles=roles,
        departments=departments,
        managers=managers,
    )


@bp.route("/employees/<int:employee_id>/edit", methods=["GET", "POST"])
@login_required
def edit_employee(employee_id: int):
    employee = Employee.query.get_or_404(employee_id)
    roles = Role.query.order_by(Role.title.asc()).all()
    departments = Department.query.order_by(Department.name.asc()).all()
    managers = Employee.query.filter(Employee.id != employee.id).order_by(Employee.last_name.asc()).all()

    if request.method == "POST":
        employee.first_name = request.form.get("first_name", employee.first_name).strip()
        employee.last_name = request.form.get("last_name", employee.last_name).strip()
        employee.email = request.form.get("email", employee.email).strip().lower()
        employee.phone = request.form.get("phone", employee.phone).strip()
        start_date_raw = request.form.get("start_date", employee.start_date.isoformat())
        try:
            employee.start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid start date format.", "danger")
            return render_template(
                "employees/form.html",
                employee=employee,
                roles=roles,
                departments=departments,
                managers=managers,
            )

        employee.department_id = request.form.get("department_id") or None
        employee.role_id = request.form.get("role_id") or None
        employee.manager_id = request.form.get("manager_id") or None
        employee.status = request.form.get("status", employee.status)

        db.session.commit()
        flash("Employee updated.", "success")
        return redirect(url_for("main.employees"))

    return render_template(
        "employees/form.html",
        employee=employee,
        roles=roles,
        departments=departments,
        managers=managers,
    )


@bp.route("/employees/<int:employee_id>/delete", methods=["POST"])
@login_required
def delete_employee(employee_id: int):
    employee = Employee.query.get_or_404(employee_id)
    db.session.delete(employee)
    db.session.commit()
    flash("Employee deleted.", "info")
    return redirect(url_for("main.employees"))


@bp.route("/departments", methods=["POST"])
@login_required
def create_department():
    name = request.form.get("name", "").strip()
    location = request.form.get("location", "").strip()
    if not name:
        flash("Department name is required.", "danger")
        return redirect(url_for("main.employees"))

    if Department.query.filter_by(name=name).first():
        flash("Department already exists.", "warning")
        return redirect(url_for("main.employees"))

    db.session.add(Department(name=name, location=location))
    db.session.commit()
    flash("Department added.", "success")
    return redirect(url_for("main.employees"))


@bp.route("/roles", methods=["POST"])
@login_required
def create_role():
    title = request.form.get("title", "").strip()
    level = request.form.get("level", "").strip()
    if not title:
        flash("Role title is required.", "danger")
        return redirect(url_for("main.employees"))

    if Role.query.filter_by(title=title).first():
        flash("Role already exists.", "warning")
        return redirect(url_for("main.employees"))

    db.session.add(Role(title=title, level=level))
    db.session.commit()
    flash("Role added.", "success")
    return redirect(url_for("main.employees"))


@bp.route("/time-off")
@login_required
def time_off_list():
    requests_list = TimeOffRequest.query.order_by(TimeOffRequest.created_at.desc()).all()
    employees = Employee.query.order_by(Employee.last_name.asc()).all()
    return render_template("timeoff/list.html", requests=requests_list, employees=employees)


@bp.route("/time-off/new", methods=["GET", "POST"])
@login_required
def time_off_new():
    employees = Employee.query.order_by(Employee.last_name.asc()).all()

    if request.method == "POST":
        employee_id = request.form.get("employee_id")
        start_date_raw = request.form.get("start_date")
        end_date_raw = request.form.get("end_date")
        category = request.form.get("category", "pto")
        note = request.form.get("note", "")

        try:
            start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_raw, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            flash("Invalid dates.", "danger")
            return render_template("timeoff/form.html", employees=employees)

        if end_date < start_date:
            flash("End date must be after start date.", "danger")
            return render_template("timeoff/form.html", employees=employees)

        record = TimeOffRequest(
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
            category=category,
            note=note,
        )
        db.session.add(record)
        db.session.commit()
        flash("Request submitted.", "success")
        return redirect(url_for("main.time_off_list"))

    return render_template("timeoff/form.html", employees=employees)


@bp.route("/time-off/<int:request_id>/status", methods=["POST"])
@login_required
def time_off_status(request_id: int):
    record = TimeOffRequest.query.get_or_404(request_id)
    new_status = request.form.get("status", record.status)
    if new_status not in {"pending", "approved", "declined"}:
        flash("Invalid status.", "danger")
        return redirect(url_for("main.time_off_list"))

    record.status = new_status
    db.session.commit()
    flash("Status updated.", "info")
    return redirect(url_for("main.time_off_list"))


@bp.route("/attendance")
@login_required
def attendance_list():
    day = request.args.get("date")
    try:
        filter_date = datetime.strptime(day, "%Y-%m-%d").date() if day else None
    except ValueError:
        filter_date = None

    query = AttendanceLog.query.order_by(AttendanceLog.work_date.desc(), AttendanceLog.check_in.asc().nullslast())
    if filter_date:
        query = query.filter_by(work_date=filter_date)

    logs = query.all()
    employees = Employee.query.order_by(Employee.last_name.asc()).all()
    return render_template("attendance/list.html", logs=logs, employees=employees, filter_date=filter_date)


@bp.route("/attendance/new", methods=["GET", "POST"])
@login_required
def attendance_new():
    employees = Employee.query.order_by(Employee.last_name.asc()).all()
    if request.method == "POST":
        employee_id = request.form.get("employee_id")
        work_date_raw = request.form.get("work_date")
        check_in_raw = request.form.get("check_in") or None
        check_out_raw = request.form.get("check_out") or None
        status = request.form.get("status", "present")
        notes = request.form.get("notes", "")

        try:
            work_date = datetime.strptime(work_date_raw, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            flash("Invalid work date.", "danger")
            return render_template("attendance/form.html", employees=employees)

        check_in = datetime.strptime(check_in_raw, "%H:%M").time() if check_in_raw else None
        check_out = datetime.strptime(check_out_raw, "%H:%M").time() if check_out_raw else None

        if not employee_id:
            flash("Employee is required.", "danger")
            return render_template("attendance/form.html", employees=employees)

        entry = AttendanceLog(
            employee_id=employee_id,
            work_date=work_date,
            check_in=check_in,
            check_out=check_out,
            status=status,
            notes=notes,
        )
        db.session.add(entry)
        db.session.commit()
        flash("Attendance recorded.", "success")
        return redirect(url_for("main.attendance_list"))

    return render_template("attendance/form.html", employees=employees)


@bp.route("/attendance/<int:log_id>/edit", methods=["GET", "POST"])
@login_required
def attendance_edit(log_id: int):
    entry = AttendanceLog.query.get_or_404(log_id)
    employees = Employee.query.order_by(Employee.last_name.asc()).all()

    if request.method == "POST":
        work_date_raw = request.form.get("work_date")
        check_in_raw = request.form.get("check_in") or None
        check_out_raw = request.form.get("check_out") or None
        entry.status = request.form.get("status", entry.status)
        entry.notes = request.form.get("notes", entry.notes)
        entry.employee_id = request.form.get("employee_id", entry.employee_id)

        try:
            entry.work_date = datetime.strptime(work_date_raw, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            flash("Invalid work date.", "danger")
            return render_template("attendance/form.html", employees=employees, entry=entry)

        entry.check_in = datetime.strptime(check_in_raw, "%H:%M").time() if check_in_raw else None
        entry.check_out = datetime.strptime(check_out_raw, "%H:%M").time() if check_out_raw else None

        db.session.commit()
        flash("Attendance updated.", "success")
        return redirect(url_for("main.attendance_list"))

    return render_template("attendance/form.html", employees=employees, entry=entry)


@bp.route("/attendance/<int:log_id>/delete", methods=["POST"])
@login_required
def attendance_delete(log_id: int):
    entry = AttendanceLog.query.get_or_404(log_id)
    db.session.delete(entry)
    db.session.commit()
    flash("Attendance deleted.", "info")
    return redirect(url_for("main.attendance_list"))


@bp.route("/communications", methods=["GET", "POST"])
@login_required
def communications():
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(10).all()
    messages = ChannelMessage.query.order_by(ChannelMessage.created_at.desc()).limit(20).all()

    if request.method == "POST":
        kind = request.form.get("kind")
        author = request.form.get("author", g.user.full_name if getattr(g, "user", None) else "System")
        if kind == "announcement":
            title = request.form.get("title", "").strip()
            body = request.form.get("body", "").strip()
            if not title or not body:
                flash("Title and body are required.", "danger")
            else:
                db.session.add(Announcement(title=title, body=body, author=author))
                db.session.commit()
                flash("Announcement posted.", "success")
                return redirect(url_for("main.communications"))
        elif kind == "message":
            channel = request.form.get("channel", "general").strip() or "general"
            body = request.form.get("body", "").strip()
            if not body:
                flash("Message is required.", "danger")
            else:
                db.session.add(ChannelMessage(channel=channel, message=body, author=author))
                db.session.commit()
                flash("Message sent.", "success")
                return redirect(url_for("main.communications"))

    return render_template("communications/list.html", announcements=announcements, messages=messages)


@bp.route("/performance", methods=["GET", "POST"])
@login_required
def performance():
    employees = Employee.query.order_by(Employee.last_name.asc()).all()
    reviews = PerformanceReview.query.order_by(PerformanceReview.period_end.desc()).all()

    if request.method == "POST":
        employee_id = request.form.get("employee_id")
        reviewer = request.form.get("reviewer", "").strip()
        period_start_raw = request.form.get("period_start")
        period_end_raw = request.form.get("period_end")
        rating = request.form.get("rating", "")
        status = request.form.get("status", "draft")
        summary = request.form.get("summary", "")
        goals = request.form.get("goals", "")

        try:
            period_start = datetime.strptime(period_start_raw, "%Y-%m-%d").date()
            period_end = datetime.strptime(period_end_raw, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            flash("Invalid period dates.", "danger")
            return render_template("performance/list.html", employees=employees, reviews=reviews)

        if not employee_id:
            flash("Employee is required.", "danger")
            return render_template("performance/list.html", employees=employees, reviews=reviews)

        review = PerformanceReview(
            employee_id=employee_id,
            reviewer=reviewer,
            period_start=period_start,
            period_end=period_end,
            rating=rating,
            status=status,
            summary=summary,
            goals=goals,
        )
        db.session.add(review)
        db.session.commit()
        flash("Performance review saved.", "success")
        return redirect(url_for("main.performance"))

    return render_template("performance/list.html", employees=employees, reviews=reviews)


@bp.route("/performance/<int:review_id>/delete", methods=["POST"])
@login_required
def performance_delete(review_id: int):
    review = PerformanceReview.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash("Review deleted.", "info")
    return redirect(url_for("main.performance"))


@bp.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    employees = Employee.query.order_by(Employee.last_name.asc()).all()
    tasks = OnboardingTask.query.order_by(OnboardingTask.due_date.asc().nullslast()).all()

    if request.method == "POST":
        employee_id = request.form.get("employee_id")
        title = request.form.get("title", "").strip()
        status = request.form.get("status", "open")
        due_raw = request.form.get("due_date")
        notes = request.form.get("notes", "")

        due_date = None
        if due_raw:
            try:
                due_date = datetime.strptime(due_raw, "%Y-%m-%d").date()
            except ValueError:
                flash("Invalid due date.", "danger")
                return render_template("onboarding/list.html", employees=employees, tasks=tasks)

        if not employee_id or not title:
            flash("Employee and title are required.", "danger")
            return render_template("onboarding/list.html", employees=employees, tasks=tasks)

        task = OnboardingTask(employee_id=employee_id, title=title, status=status, due_date=due_date, notes=notes)
        db.session.add(task)
        db.session.commit()
        flash("Task saved.", "success")
        return redirect(url_for("main.onboarding"))

    return render_template("onboarding/list.html", employees=employees, tasks=tasks)


@bp.route("/onboarding/<int:task_id>/delete", methods=["POST"])
@login_required
def onboarding_delete(task_id: int):
    task = OnboardingTask.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted.", "info")
    return redirect(url_for("main.onboarding"))


@bp.route("/onboarding/<int:task_id>/status", methods=["POST"])
@login_required
def onboarding_status(task_id: int):
    task = OnboardingTask.query.get_or_404(task_id)
    new_status = request.form.get("status", task.status)
    task.status = new_status
    db.session.commit()
    flash("Task updated.", "success")
    return redirect(url_for("main.onboarding"))


@bp.route("/benefits", methods=["GET", "POST"])
@login_required
def benefits():
    employees = Employee.query.order_by(Employee.last_name.asc()).all()
    enrollments = BenefitEnrollment.query.order_by(BenefitEnrollment.start_date.desc().nullslast()).all()

    if request.method == "POST":
        employee_id = request.form.get("employee_id")
        benefit_type = request.form.get("benefit_type", "").strip()
        provider = request.form.get("provider", "").strip()
        coverage = request.form.get("coverage", "").strip()
        status = request.form.get("status", "active")
        start_raw = request.form.get("start_date")
        end_raw = request.form.get("end_date")

        try:
            start_date = datetime.strptime(start_raw, "%Y-%m-%d").date() if start_raw else None
            end_date = datetime.strptime(end_raw, "%Y-%m-%d").date() if end_raw else None
        except ValueError:
            flash("Invalid dates.", "danger")
            return render_template("benefits/list.html", employees=employees, enrollments=enrollments)

        if not employee_id or not benefit_type:
            flash("Employee and benefit type are required.", "danger")
            return render_template("benefits/list.html", employees=employees, enrollments=enrollments)

        enrollment = BenefitEnrollment(
            employee_id=employee_id,
            benefit_type=benefit_type,
            provider=provider,
            coverage=coverage,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )
        db.session.add(enrollment)
        db.session.commit()
        flash("Benefit enrollment saved.", "success")
        return redirect(url_for("main.benefits"))

    return render_template("benefits/list.html", employees=employees, enrollments=enrollments)


@bp.route("/benefits/<int:enroll_id>/delete", methods=["POST"])
@login_required
def benefits_delete(enroll_id: int):
    enrollment = BenefitEnrollment.query.get_or_404(enroll_id)
    db.session.delete(enrollment)
    db.session.commit()
    flash("Enrollment deleted.", "info")
    return redirect(url_for("main.benefits"))


@bp.route("/wellness", methods=["GET", "POST"])
@login_required
def wellness():
    employees = Employee.query.order_by(Employee.last_name.asc()).all()
    recognitions = Recognition.query.order_by(Recognition.created_at.desc()).all()

    if request.method == "POST":
        employee_id = request.form.get("employee_id")
        from_person = request.form.get("from_person", "").strip()
        badge = request.form.get("badge", "").strip()
        message = request.form.get("message", "").strip()
        if not employee_id or not message:
            flash("Employee and message are required.", "danger")
            return render_template("wellness/list.html", employees=employees, recognitions=recognitions)
        rec = Recognition(employee_id=employee_id, from_person=from_person, badge=badge, message=message)
        db.session.add(rec)
        db.session.commit()
        flash("Recognition sent.", "success")
        return redirect(url_for("main.wellness"))

    return render_template("wellness/list.html", employees=employees, recognitions=recognitions)


@bp.route("/wellness/<int:rec_id>/delete", methods=["POST"])
@login_required
def wellness_delete(rec_id: int):
    rec = Recognition.query.get_or_404(rec_id)
    db.session.delete(rec)
    db.session.commit()
    flash("Recognition removed.", "info")
    return redirect(url_for("main.wellness"))


@bp.route("/reports")
@login_required
def reports():
    employee_total = Employee.query.count()
    active_employees = Employee.query.filter_by(status="active").count()
    on_leave = Employee.query.filter_by(status="on-leave").count()
    pending_time_off = TimeOffRequest.query.filter_by(status="pending").count()
    payroll_scheduled = db.session.query(db.func.sum(PayrollEntry.gross_pay)).filter(PayrollEntry.status == "scheduled").scalar() or 0
    payroll_paid = db.session.query(db.func.sum(PayrollEntry.gross_pay)).filter(PayrollEntry.status == "paid").scalar() or 0
    attendance_today = AttendanceLog.query.filter_by(work_date=date.today()).count()
    open_onboarding = OnboardingTask.query.filter(OnboardingTask.status != "done").count()
    open_reviews = PerformanceReview.query.filter(PerformanceReview.status != "submitted").count()
    recognitions_7d = Recognition.query.filter(Recognition.created_at >= datetime.utcnow() - timedelta(days=7)).count()
    benefits_active = BenefitEnrollment.query.filter_by(status="active").count()

    metrics = {
        "employee_total": employee_total,
        "active_employees": active_employees,
        "on_leave": on_leave,
        "pending_time_off": pending_time_off,
        "payroll_scheduled": float(payroll_scheduled),
        "payroll_paid": float(payroll_paid),
        "attendance_today": attendance_today,
        "open_onboarding": open_onboarding,
        "open_reviews": open_reviews,
        "recognitions_7d": recognitions_7d,
        "benefits_active": benefits_active,
    }

    return render_template("reports/summary.html", metrics=metrics)


@bp.route("/ess")
@login_required
def ess():
    employees = Employee.query.order_by(Employee.last_name.asc()).all()
    recent_announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(3).all()
    my_tasks = OnboardingTask.query.order_by(OnboardingTask.due_date.asc().nullslast()).limit(5).all()
    recognitions = Recognition.query.order_by(Recognition.created_at.desc()).limit(5).all()
    return render_template(
        "ess/portal.html",
        employees=employees,
        announcements=recent_announcements,
        tasks=my_tasks,
        recognitions=recognitions,
    )


@bp.route("/system/health")
def system_health():
    try:
        db.session.execute(db.select(Employee).limit(1)).first()
        db_ok = True
    except Exception:
        db_ok = False

    payload = {
        "database": "ok" if db_ok else "error",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    return jsonify(payload)


@bp.route("/payroll")
@login_required
def payroll_list():
    entries = PayrollEntry.query.order_by(PayrollEntry.pay_date.desc()).all()
    employees = Employee.query.order_by(Employee.last_name.asc()).all()
    return render_template("payroll/list.html", entries=entries, employees=employees)


@bp.route("/payroll/new", methods=["GET", "POST"])
@login_required
def payroll_new():
    employees = Employee.query.order_by(Employee.last_name.asc()).all()
    if request.method == "POST":
        employee_id = request.form.get("employee_id")
        period_start = request.form.get("period_start")
        period_end = request.form.get("period_end")
        pay_date = request.form.get("pay_date")
        gross_pay = request.form.get("gross_pay", 0)
        taxes = request.form.get("taxes", 0)
        bonus = request.form.get("bonus", 0)
        status = request.form.get("status", "scheduled")
        notes = request.form.get("notes", "")

        try:
            period_start_dt = datetime.strptime(period_start, "%Y-%m-%d").date()
            period_end_dt = datetime.strptime(period_end, "%Y-%m-%d").date()
            pay_date_dt = datetime.strptime(pay_date, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            flash("Invalid dates.", "danger")
            return render_template("payroll/form.html", employees=employees)

        if period_end_dt < period_start_dt:
            flash("Period end must be after start.", "danger")
            return render_template("payroll/form.html", employees=employees)

        entry = PayrollEntry(
            employee_id=employee_id,
            period_start=period_start_dt,
            period_end=period_end_dt,
            pay_date=pay_date_dt,
            gross_pay=gross_pay or 0,
            taxes=taxes or 0,
            bonus=bonus or 0,
            status=status,
            notes=notes,
        )
        db.session.add(entry)
        db.session.commit()
        flash("Payroll entry created.", "success")
        return redirect(url_for("main.payroll_list"))

    return render_template("payroll/form.html", employees=employees)


@bp.route("/payroll/<int:entry_id>/edit", methods=["GET", "POST"])
@login_required
def payroll_edit(entry_id: int):
    entry = PayrollEntry.query.get_or_404(entry_id)
    employees = Employee.query.order_by(Employee.last_name.asc()).all()

    if request.method == "POST":
        entry.employee_id = request.form.get("employee_id")
        entry.status = request.form.get("status", entry.status)
        entry.notes = request.form.get("notes", entry.notes)
        entry.gross_pay = request.form.get("gross_pay", entry.gross_pay)
        entry.taxes = request.form.get("taxes", entry.taxes)
        entry.bonus = request.form.get("bonus", entry.bonus)

        try:
            entry.period_start = datetime.strptime(request.form.get("period_start"), "%Y-%m-%d").date()
            entry.period_end = datetime.strptime(request.form.get("period_end"), "%Y-%m-%d").date()
            entry.pay_date = datetime.strptime(request.form.get("pay_date"), "%Y-%m-%d").date()
        except (TypeError, ValueError):
            flash("Invalid dates.", "danger")
            return render_template("payroll/form.html", employees=employees, entry=entry)

        if entry.period_end < entry.period_start:
            flash("Period end must be after start.", "danger")
            return render_template("payroll/form.html", employees=employees, entry=entry)

        db.session.commit()
        flash("Payroll entry updated.", "success")
        return redirect(url_for("main.payroll_list"))

    return render_template("payroll/form.html", employees=employees, entry=entry)


@bp.route("/payroll/<int:entry_id>/delete", methods=["POST"])
@login_required
def payroll_delete(entry_id: int):
    entry = PayrollEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash("Payroll entry deleted.", "info")
    return redirect(url_for("main.payroll_list"))


@bp.route("/projects")
@login_required
def projects():
    projects_list = Project.query.order_by(Project.start_date.desc().nullslast(), Project.name).all()
    employees = Employee.query.order_by(Employee.last_name.asc()).all()
    return render_template("projects/list.html", projects=projects_list, employees=employees)


@bp.route("/projects/new", methods=["POST"])
@login_required
def project_new():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    status = request.form.get("status", "planned")
    start_date_raw = request.form.get("start_date")
    end_date_raw = request.form.get("end_date")

    if not name:
        flash("Project name is required.", "danger")
        return redirect(url_for("main.projects"))

    start_date = None
    end_date = None
    if start_date_raw:
        try:
            start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid start date.", "danger")
            return redirect(url_for("main.projects"))
    if end_date_raw:
        try:
            end_date = datetime.strptime(end_date_raw, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid end date.", "danger")
            return redirect(url_for("main.projects"))

    project = Project(name=name, description=description, status=status, start_date=start_date, end_date=end_date)
    db.session.add(project)
    db.session.commit()
    flash("Project created.", "success")
    return redirect(url_for("main.projects"))


@bp.route("/projects/<int:project_id>/edit", methods=["POST"])
@login_required
def project_edit(project_id: int):
    project = Project.query.get_or_404(project_id)
    project.name = request.form.get("name", project.name).strip()
    project.description = request.form.get("description", project.description).strip()
    project.status = request.form.get("status", project.status)

    start_date_raw = request.form.get("start_date")
    end_date_raw = request.form.get("end_date")
    try:
        project.start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date() if start_date_raw else None
        project.end_date = datetime.strptime(end_date_raw, "%Y-%m-%d").date() if end_date_raw else None
    except ValueError:
        flash("Invalid dates.", "danger")
        return redirect(url_for("main.projects"))

    db.session.commit()
    flash("Project updated.", "success")
    return redirect(url_for("main.projects"))


@bp.route("/projects/<int:project_id>/delete", methods=["POST"])
@login_required
def project_delete(project_id: int):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    flash("Project deleted.", "info")
    return redirect(url_for("main.projects"))


@bp.route("/projects/<int:project_id>/assign", methods=["POST"])
@login_required
def project_assign(project_id: int):
    project = Project.query.get_or_404(project_id)
    employee_id = request.form.get("employee_id")
    role = request.form.get("role", "")
    allocation = request.form.get("allocation") or None

    if not employee_id:
        flash("Employee is required.", "danger")
        return redirect(url_for("main.projects"))

    assignment = ProjectAssignment(project_id=project.id, employee_id=employee_id, role=role, allocation=allocation)
    db.session.add(assignment)
    db.session.commit()
    flash("Assignment added.", "success")
    return redirect(url_for("main.projects"))


@bp.route("/api/chat", methods=["POST"])
@login_required
def chat_api():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message is required."}), 400

    fallback = "Assistant is offline right now, but your request was received."

    client_tuple, err = _get_gemini_client()
    if err:
        return jsonify({"reply": fallback, "error": err}), 200
    client, model_id = client_tuple

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=message,
        )
        reply = getattr(response, "text", None) or "I could not generate a reply just now."
    except Exception as err:
        return jsonify({"reply": fallback, "error": f"Gemini request failed: {err}"}), 200

    return jsonify({"reply": reply})


@bp.app_errorhandler(404)
def not_found(_):
    return render_template("errors/404.html"), 404
