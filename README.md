# Rantoo

Random Tools - A Flask web application for various utility tools.

## Features

- Epoch to Human Date Converter
- Human Date to Epoch Converter
- Health check endpoint for monitoring
- Responsive web interface

## Local Development

### Prerequisites

- Python 3.10+
- pip

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/pbertain/timepuff.git
   cd timepuff
   ```

2. Create and activate virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python app.py
   ```

5. Open your browser to `http://localhost:33080`

## Production Deployment

This application includes Ansible playbooks for automated deployment to your `pb_home` host group.

### Prerequisites

- Ansible installed on your local machine
- SSH access to target hosts
- Hosts configured in `ansible/inventory/hosts.yml`
- Reverse proxy (nginx, Apache, etc.) configured separately

### Quick Deployment

```bash
./deploy.sh
```

### Management

Use the management script for common operations:

```bash
# Check status
./manage.sh status

# View logs
./manage.sh logs

# Restart application
./manage.sh restart

# Update application
./manage.sh update
```

For detailed deployment instructions, see [ansible/README.md](ansible/README.md).

## Project Structure

```
rantoo/
├── app.py                 # Flask application
├── requirements.txt       # Python dependencies
├── static/               # Static files (CSS, JS)
├── templates/            # HTML templates
├── ansible/              # Ansible deployment configuration
│   ├── inventory/        # Host inventory
│   ├── playbooks/        # Deployment playbooks
│   ├── templates/        # Configuration templates
│   └── group_vars/       # Group variables
├── deploy.sh             # Deployment script
└── manage.sh             # Management script
```

## License

MIT License - see [LICENSE](LICENSE) file for details.
