# Task Manager

A simple Flask web application to help you manage and organize your tasks.

## Features

- User registration and login
- Create, view, edit, and delete tasks
- Filter and sort tasks by different criteria
- Assign categories to tasks
- Mark tasks as completed

## Installation

1. Clone the repository:
```
git clone <repository-url>
cd TaskManager
```

2. Install the required dependencies:
```
pip install -r requirements.txt
```

## Running the Application

### Set the Flask App Environment Variable

**On Windows (PowerShell):**
```
$env:FLASK_APP = "app.py"
$env:FLASK_ENV = "development"
```

**On Windows (Command Prompt):**
```
set FLASK_APP=app.py
set FLASK_ENV=development
```

**On macOS/Linux:**
```
export FLASK_APP=app.py
export FLASK_ENV=development
```

### Start the Flask Server

```
flask run
```

The application will be available at http://127.0.0.1:5000/

## First-time Setup

1. The database will be automatically created when you first run the application
2. Register a new user to start using the application
3. The first user will have default categories created automatically

## Technologies Used

- Flask - Python web framework
- SQLite - Database
- Bootstrap 5 - Frontend framework 