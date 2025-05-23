# app.py
import os
from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required, get_user_id
import sqlite3
from datetime import datetime

# Configure application
app = Flask(__name__)

# Configure session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure database
DATABASE = "database.db"


def get_db():
    try:
        db = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        return db
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None


def init_db():
    try:
        with app.app_context():
            db = get_db()
            if db is None:
                return False
            with open('schema.sql', 'r') as f:
                db.executescript(f.read())
            db.commit()
            return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False


# Create the database if it doesn't exist
if not os.path.exists(DATABASE):
    if not init_db():
        print("Failed to initialize database. Please check your schema.sql file and permissions.")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show dashboard"""
    db = get_db()
    if db is None:
        flash("Database connection error", "error")
        return redirect("/login")
        
    user_id = session["user_id"]
    
    # Get user information
    user = db.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        session.clear()
        flash("User not found", "error")
        return redirect("/login")

    # Get task counts
    try:
        total_tasks = db.execute("SELECT COUNT(*) as count FROM tasks WHERE user_id = ?",
                               (user_id,)).fetchone()["count"]

        completed_tasks = db.execute("SELECT COUNT(*) as count FROM tasks WHERE user_id = ? AND completed = 1",
                                   (user_id,)).fetchone()["count"]

        pending_tasks = db.execute("SELECT COUNT(*) as count FROM tasks WHERE user_id = ? AND completed = 0",
                                 (user_id,)).fetchone()["count"]

        high_priority_tasks = db.execute("SELECT COUNT(*) as count FROM tasks WHERE user_id = ? AND priority = 'high' AND completed = 0",
                                       (user_id,)).fetchone()["count"]

        # Get recent tasks
        recent_tasks = db.execute("""
            SELECT id, title, priority, due_date, completed
            FROM tasks
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 5
        """, (user_id,)).fetchall()

        # Get categories
        categories = db.execute("SELECT id, name, color FROM categories WHERE user_id = ?",
                              (user_id,)).fetchall()

        return render_template("dashboard.html",
                             username=user["username"],
                             total_tasks=total_tasks,
                             completed_tasks=completed_tasks,
                             pending_tasks=pending_tasks,
                             high_priority_tasks=high_priority_tasks,
                             recent_tasks=recent_tasks,
                             categories=categories)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", "error")
        return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Please provide both username and password", "error")
            return render_template("login.html")

        db = get_db()
        if db is None:
            flash("Database connection error", "error")
            return render_template("login.html")

        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if not user or not check_password_hash(user["hash"], password):
            flash("Invalid username and/or password", "error")
            return render_template("login.html")

        session["user_id"] = user["id"]
        flash("Logged in successfully!", "success")
        return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password or not confirmation:
            flash("Please fill in all fields", "error")
            return render_template("register.html")

        if password != confirmation:
            flash("Passwords do not match", "error")
            return render_template("register.html")

        db = get_db()
        if db is None:
            flash("Database connection error", "error")
            return render_template("register.html")

        # Check if username already exists
        existing_user = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing_user:
            flash("Username already exists", "error")
            return render_template("register.html")

        # Create new user
        try:
            db.execute(
                "INSERT INTO users (username, hash, created_at) VALUES (?, ?, ?)",
                (username, generate_password_hash(password), datetime.now())
            )
            db.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect("/login")
        except sqlite3.Error as e:
            flash(f"Database error: {e}", "error")
            return render_template("register.html")

    return render_template("register.html")


@app.route("/tasks", methods=["GET"])
@login_required
def tasks():
    """Show all tasks"""
    user_id = session["user_id"]
    db = get_db()
    
    if db is None:
        flash("Database connection error", "error")
        return redirect("/")

    # Get filter and sort parameters
    status_filter = request.args.get("status", "all")
    priority_filter = request.args.get("priority", "all")
    sort_by = request.args.get("sort", "created_at")
    sort_order = request.args.get("order", "desc")

    # Base query
    query = """
        SELECT t.id, t.title, t.description, t.priority, t.due_date, t.completed, t.created_at, t.updated_at
        FROM tasks t
        WHERE t.user_id = ?
    """
    params = [user_id]

    # Apply filters
    if status_filter == "completed":
        query += " AND t.completed = 1"
    elif status_filter == "pending":
        query += " AND t.completed = 0"

    if priority_filter != "all":
        query += " AND t.priority = ?"
        params.append(priority_filter)

    # Apply sorting
    valid_sort_columns = ["title", "priority", "due_date", "created_at", "updated_at"]
    if sort_by not in valid_sort_columns:
        sort_by = "created_at"

    valid_sort_orders = ["asc", "desc"]
    if sort_order not in valid_sort_orders:
        sort_order = "desc"

    query += f" ORDER BY t.{sort_by} {sort_order}"

    try:
        tasks = db.execute(query, params).fetchall()

        # Get categories for each task
        for task in tasks:
            task_categories = db.execute("""
                SELECT c.id, c.name, c.color
                FROM categories c
                JOIN task_categories tc ON c.id = tc.category_id
                WHERE tc.task_id = ?
            """, (task["id"],)).fetchall()
            task["categories"] = task_categories

        # Get all categories for the filter dropdown
        categories = db.execute("SELECT id, name, color FROM categories WHERE user_id = ?",
                                (user_id,)).fetchall()

        return render_template("tasks.html", tasks=tasks, categories=categories,
                               status_filter=status_filter, priority_filter=priority_filter,
                               sort_by=sort_by, sort_order=sort_order)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", "error")
        return redirect("/")


@app.route("/tasks/new", methods=["GET", "POST"])
@login_required
def new_task():
    """Create a new task"""
    user_id = session["user_id"]
    db = get_db()
    
    if db is None:
        flash("Database connection error", "error")
        return redirect("/tasks")

    if request.method == "POST":
        # Get form data
        title = request.form.get("title")
        description = request.form.get("description", "")
        priority = request.form.get("priority", "medium")
        due_date = request.form.get("due_date", None)
        category_ids = request.form.getlist("categories")

        # Validate data
        if not title:
            flash("Title is required", "error")
            return redirect("/tasks/new")

        # Create task
        try:
            now = datetime.now()
            db.execute("""
                INSERT INTO tasks (user_id, title, description, priority, due_date, completed, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, title, description, priority, due_date, 0, now, now))
            db.commit()

            # Get the newly created task's ID
            task_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

            # Associate task with categories
            if category_ids:
                for category_id in category_ids:
                    db.execute("INSERT INTO task_categories (task_id, category_id) VALUES (?, ?)",
                            (task_id, category_id))
                db.commit()

            flash("Task created successfully!", "success")
            return redirect("/tasks")
        except sqlite3.Error as e:
            flash(f"Database error: {e}", "error")
            return redirect("/tasks/new")

    # GET request - show the form
    try:
        categories = db.execute("SELECT id, name, color FROM categories WHERE user_id = ?",
                                (user_id,)).fetchall()
        return render_template("new_task.html", categories=categories)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", "error")
        return redirect("/tasks")


@app.route("/tasks/<int:task_id>", methods=["GET"])
@login_required
def view_task(task_id):
    """View a single task"""
    user_id = session["user_id"]
    db = get_db()
    
    if db is None:
        flash("Database connection error", "error")
        return redirect("/tasks")

    try:
        # Get task details
        task = db.execute("""
            SELECT id, title, description, priority, due_date, completed, created_at, updated_at
            FROM tasks
            WHERE id = ? AND user_id = ?
        """, (task_id, user_id)).fetchone()

        if not task:
            flash("Task not found", "error")
            return redirect("/tasks")

        # Get task categories
        task_categories = db.execute("""
            SELECT c.id, c.name, c.color
            FROM categories c
            JOIN task_categories tc ON c.id = tc.category_id
            WHERE tc.task_id = ?
        """, (task_id,)).fetchall()

        # Get all categories for editing
        all_categories = db.execute("SELECT id, name, color FROM categories WHERE user_id = ?",
                                    (user_id,)).fetchall()

        return render_template("view_task.html", task=task, task_categories=task_categories, all_categories=all_categories)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", "error")
        return redirect("/tasks")


@app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    """Edit a task"""
    user_id = session["user_id"]
    db = get_db()
    
    if db is None:
        flash("Database connection error", "error")
        return redirect("/tasks")

    try:
        # Check if task exists and belongs to user
        task = db.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?",
                        (task_id, user_id)).fetchone()

        if not task:
            flash("Task not found", "error")
            return redirect("/tasks")

        if request.method == "POST":
            # Get form data
            title = request.form.get("title")
            description = request.form.get("description", "")
            priority = request.form.get("priority", "medium")
            due_date = request.form.get("due_date", None)
            completed = 1 if request.form.get("completed") else 0
            category_ids = request.form.getlist("categories")

            # Validate data
            if not title:
                flash("Title is required", "error")
                return redirect(f"/tasks/{task_id}/edit")

            # Update task
            now = datetime.now()
            db.execute("""
                UPDATE tasks
                SET title = ?, description = ?, priority = ?, due_date = ?, completed = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
            """, (title, description, priority, due_date, completed, now, task_id, user_id))

            # Update categories: First delete existing associations
            db.execute("DELETE FROM task_categories WHERE task_id = ?", (task_id,))

            # Then add new associations
            if category_ids:
                for category_id in category_ids:
                    db.execute("INSERT INTO task_categories (task_id, category_id) VALUES (?, ?)",
                            (task_id, category_id))

            db.commit()
            flash("Task updated successfully!", "success")
            return redirect(f"/tasks/{task_id}")

        # GET request - show the form with current values
        # Get task categories
        task_categories = db.execute("""
            SELECT category_id
            FROM task_categories
            WHERE task_id = ?
        """, (task_id,)).fetchall()
        selected_categories = [tc["category_id"] for tc in task_categories]

        # Get all categories
        categories = db.execute("SELECT id, name, color FROM categories WHERE user_id = ?",
                                (user_id,)).fetchall()

        return render_template("edit_task.html", task=task, categories=categories, selected_categories=selected_categories)
    except sqlite3.Error as e:
        flash(f"Database error: {e}", "error")
        return redirect("/tasks")


@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    """Delete a task"""
    user_id = session["user_id"]
    db = get_db()
    
    if db is None:
        flash("Database connection error", "error")
        return redirect("/tasks")

    try:
        # Check if task exists and belongs to user
        task = db.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?",
                        (task_id, user_id)).fetchone()

        if not task:
            flash("Task not found", "error")
            return redirect("/tasks")

        # Delete associations first
        db.execute("DELETE FROM task_categories WHERE task_id = ?", (task_id,))
        
        # Delete task
        db.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
        db.commit()

        flash("Task deleted successfully!", "success")
        return redirect("/tasks")
    except sqlite3.Error as e:
        flash(f"Database error: {e}", "error")
        return redirect("/tasks")


@app.route("/tasks/<int:task_id>/toggle", methods=["POST"])
@login_required
def toggle_task(task_id):
    """Toggle task completion status"""
    user_id = session["user_id"]
    db = get_db()
    
    if db is None:
        return jsonify({"success": False, "message": "Database connection error"}), 500

    try:
        # Check if task exists and belongs to user
        task = db.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?",
                        (task_id, user_id)).fetchone()

        if not task:
            return jsonify({"success": False, "message": "Task not found"}), 404

        # Toggle completion status
        new_status = 0 if task["completed"] else 1

        db.execute("""
            UPDATE tasks
            SET completed = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
        """, (new_status, datetime.now(), task_id, user_id))
        db.commit()

        return jsonify({"success": True, "completed": bool(new_status)})
    except sqlite3.Error as e:
        return jsonify({"success": False, "message": f"Database error: {str(e)}"}), 500


@app.route("/tasks/quick", methods=["POST"])
@login_required
def quick_add_task():
    """Quickly add a task with minimal information"""
    user_id = session["user_id"]
    db = get_db()
    
    if db is None:
        flash("Database connection error", "error")
        return redirect("/")

    try:
        # Get form data
        title = request.form.get("title")
        priority = request.form.get("priority", "medium")

        if not title:
            flash("Title is required", "error")
            return redirect("/")

        # Create task
        now = datetime.now()
        db.execute("""
            INSERT INTO tasks (user_id, title, priority, completed, created_at, updated_at)
            VALUES (?, ?, ?, 0, ?, ?)
        """, (user_id, title, priority, now, now))
        db.commit()

        flash("Task added successfully!", "success")
        return redirect("/")
    except sqlite3.Error as e:
        flash(f"Database error: {e}", "error")
        return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
