from flask import Flask, render_template_string, request, jsonify
import json

app = Flask(__name__)

# Simulated DB
TICKETS = {
    "T-101": {"id": "T-101", "user": "alice@acme.com", "issue": "Need access to AWS Production", "priority": "High", "status": "Open", "notes": ""},
    "T-102": {"id": "T-102", "user": "bob@acme.com", "issue": "Monitor won't turn on", "priority": "Low", "status": "Open", "notes": ""},
    "T-103": {"id": "T-103", "user": "charlie@acme.com", "issue": "Onboarding new hire: Software Engineer", "priority": "Medium", "status": "Open", "notes": ""},
    "T-104": {"id": "T-104", "user": "diana@acme.com", "issue": "Update my title to Senior Manager", "priority": "Medium", "status": "Resolved", "notes": "Updated in Workday"},
}

EMPLOYEES = {
    "alice@acme.com": {"name": "Alice Smith", "department": "Engineering", "manager": "Eve"},
    "bob@acme.com": {"name": "Bob Jones", "department": "Sales", "manager": "Frank"},
    "charlie@acme.com": {"name": "Charlie Davis", "department": "HR", "manager": "Grace"},
    "diana@acme.com": {"name": "Diana Prince", "department": "Management", "manager": "CEO"}
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html data-bs-theme="dark">
<head>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <title>Acme Corp IT Helpdesk</title>
</head>
<body class="bg-dark text-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-secondary mb-4">
        <div class="container">
            <a class="navbar-brand" href="/">Acme IT Helpdesk</a>
            <div class="navbar-nav">
                <a class="nav-link" href="/tickets">Tickets</a>
                <a class="nav-link" href="/provision">Provision Software</a>
            </div>
        </div>
    </nav>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

INDEX_TEMPLATE = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', """
<h1>Welcome to Acme IT Helpdesk</h1>
<p>Manage employee requests, provision software, and resolve tickets.</p>
<div class="mt-4">
    <a href="/tickets" class="btn btn-primary">View Open Tickets</a>
    <a href="/provision" class="btn btn-outline-light">Provision Software</a>
</div>
""")

TICKETS_TEMPLATE = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', """
<h2>Active Tickets</h2>
<table class="table table-dark table-striped mt-3">
    <thead>
        <tr>
            <th>ID</th>
            <th>User</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Action</th>
        </tr>
    </thead>
    <tbody>
        {% for t in tickets.values() %}
        <tr>
            <td>{{ t.id }}</td>
            <td>{{ t.user }}</td>
            <td>
                <span class="badge {% if t.priority == 'High' %}bg-danger{% elif t.priority == 'Medium' %}bg-warning{% else %}bg-info{% endif %}">
                    {{ t.priority }}
                </span>
            </td>
            <td>
                <span class="badge {% if t.status == 'Resolved' %}bg-success{% else %}bg-secondary{% endif %}" id="status-{{ t.id }}">
                    {{ t.status }}
                </span>
            </td>
            <td><a href="/ticket/{{ t.id }}" class="btn btn-sm btn-outline-light" id="view-{{ t.id }}">View</a></td>
        </tr>
        {% endfor %}
    </tbody>
</table>
""")

TICKET_DETAIL_TEMPLATE = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', """
<div class="card bg-secondary text-light">
    <div class="card-header d-flex justify-content-between align-items-center">
        <h3 class="mb-0">Ticket {{ ticket.id }}</h3>
        <span class="badge {% if ticket.status == 'Resolved' %}bg-success{% else %}bg-dark{% endif %}" id="ticket-status">{{ ticket.status }}</span>
    </div>
    <div class="card-body">
        <p><strong>User:</strong> <span id="ticket-user">{{ ticket.user }}</span></p>
        <p><strong>Priority:</strong> <span id="ticket-priority">{{ ticket.priority }}</span></p>
        <p><strong>Issue:</strong> <span id="ticket-issue">{{ ticket.issue }}</span></p>
        <p><strong>Notes:</strong> <span id="ticket-notes">{{ ticket.notes }}</span></p>
        
        <div class="mt-4">
            {% if ticket.status != 'Resolved' %}
            <form action="/ticket/{{ ticket.id }}/resolve" method="POST" class="d-inline">
                <button type="submit" class="btn btn-success" id="btn-resolve">Mark Resolved</button>
            </form>
            {% endif %}
            <a href="/tickets" class="btn btn-outline-light">Back to Tickets</a>
        </div>
    </div>
</div>
""")

PROVISION_TEMPLATE = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', """
<h2>Provision Software License</h2>
{% if message %}
<div class="alert alert-success" id="success-msg">{{ message }}</div>
{% endif %}
<div class="card bg-secondary text-light mt-4">
    <div class="card-body">
        <form action="/provision" method="POST">
            <div class="mb-3">
                <label class="form-label">Employee Email</label>
                <input type="email" name="email" class="form-control" id="email" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Software / Access Type</label>
                <select name="software" class="form-select" id="select-software">
                    <option value="AWS">AWS Console</option>
                    <option value="GitHub">GitHub Enterprise</option>
                    <option value="Jira">Jira / Confluence</option>
                </select>
            </div>
            <button type="submit" class="btn btn-primary" id="btn-provision">Grant Access</button>
        </form>
    </div>
</div>
""")

@app.route('/')
def index():
    return render_template_string(INDEX_TEMPLATE)

@app.route('/tickets')
def list_tickets():
    return render_template_string(TICKETS_TEMPLATE, tickets=TICKETS)

@app.route('/ticket/<tid>')
def view_ticket(tid):
    if tid not in TICKETS:
        return "Not found", 404
    return render_template_string(TICKET_DETAIL_TEMPLATE, ticket=TICKETS[tid])

@app.route('/ticket/<tid>/resolve', methods=['POST'])
def resolve_ticket(tid):
    if tid in TICKETS:
        TICKETS[tid]['status'] = 'Resolved'
    return render_template_string(TICKET_DETAIL_TEMPLATE, ticket=TICKETS[tid])

@app.route('/provision', methods=['GET', 'POST'])
def provision():
    msg = None
    if request.method == 'POST':
        email = request.form.get('email')
        sw = request.form.get('software')
        msg = f"Successfully provisioned {sw} access for {email}!"
    return render_template_string(PROVISION_TEMPLATE, message=msg)

# JSON APIs
@app.route('/api/employees/<email>')
def get_employee(email):
    emp = EMPLOYEES.get(email)
    if not emp:
        return jsonify({"error": "Employee not found"}), 404
    return jsonify(emp)

@app.route('/api/tickets')
def api_tickets():
    return jsonify(list(TICKETS.values()))

if __name__ == '__main__':
    app.run(port=5001, debug=True)
