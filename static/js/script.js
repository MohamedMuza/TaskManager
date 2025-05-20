// TaskMaster main JavaScript file

document.addEventListener('DOMContentLoaded', function() {

    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Toggle task completion when checkbox is clicked
    const taskCheckboxes = document.querySelectorAll('.task-checkbox');
    taskCheckboxes.forEach(function(checkbox) {
        checkbox.addEventListener('change', function() {
            const taskId = this.getAttribute('data-task-id');
            const taskItem = document.querySelector(`.task-item[data-task-id="${taskId}"]`);

            // Optimistic UI update
            if (this.checked) {
                taskItem.classList.add('task-completed');
            } else {
                taskItem.classList.remove('task-completed');
            }

            // This would be replaced with actual AJAX in Week 2
            console.log(`Task ${taskId} completion toggled to ${this.checked}`);
        });
    });

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Dark mode toggle (to be implemented in Week 3)
    const darkModeToggle = document.querySelector('#darkModeToggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-mode');
            // Save preference to localStorage
            const isDarkMode = document.body.classList.contains('dark-mode');
            localStorage.setItem('darkMode', isDarkMode);
        });

        // Check for saved preference
        if (localStorage.getItem('darkMode') === 'true') {
            document.body.classList.add('dark-mode');
            darkModeToggle.checked = true;
        }
    }
});

// Helper functions (to be used in Week 2 and beyond)
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
}

function showLoading() {
    // Create and show loading spinner
    const spinner = document.createElement('div');
    spinner.classList.add('spinner-border', 'text-primary', 'loading-spinner');
    spinner.setAttribute('role', 'status');

    const span = document.createElement('span');
    span.classList.add('visually-hidden');
    span.textContent = 'Loading...';

    spinner.appendChild(span);
    document.body.appendChild(spinner);
}

function hideLoading() {
    // Remove loading spinner
    const spinner = document.querySelector('.loading-spinner');
    if (spinner) {
        spinner.remove();
    }
}