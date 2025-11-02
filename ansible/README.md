# Rantoo Ansible Deployment

This directory contains Ansible playbooks and configurations for deploying the Rantoo Flask application to your `pb_home` host group.

## Directory Structure

```
ansible/
├── ansible.cfg              # Ansible configuration
├── inventory/
│   └── hosts.yml           # Host inventory
├── group_vars/
│   └── pb_home.yml         # Group variables
├── templates/
│   └── rantoo.service.j2   # Systemd service template
└── playbooks/
    └── deploy.yml          # Main deployment playbook
```

## Prerequisites

1. **Ansible installed** on your local machine:
   ```bash
   pip install ansible
   # or on macOS
   brew install ansible
   ```

2. **SSH access** to your target hosts configured

3. **Hosts configured** in `inventory/hosts.yml`

## Configuration

### 1. Configure Hosts

Edit `inventory/hosts.yml` and add your actual host details:

```yaml
all:
  children:
    pb_home:
      hosts:
        192.168.1.100:  # Replace with your host IP
          ansible_user: your_username
          ansible_ssh_private_key_file: ~/.ssh/id_rsa
        # Add more hosts as needed
```

### 2. Configure Variables

Edit `group_vars/pb_home.yml` to customize deployment settings:

- `app_name`: Application name (default: rantoo)
- `app_directory`: Installation directory (default: /opt/rantoo)
- `app_port`: Flask application port (default: 33080)

## Deployment

### Quick Deployment

From the project root directory:

```bash
./deploy.sh
```

### Manual Deployment

```bash
cd ansible
ansible-playbook -i inventory/hosts.yml playbooks/deploy.yml --ask-become-pass
```

## Management

Use the management script for common operations:

```bash
# Check application status
./manage.sh status

# View logs
./manage.sh logs

# Restart application
./manage.sh restart

# Update application
./manage.sh update

# Health check
./manage.sh health
```

## What Gets Deployed

The playbook will:

1. **Install system packages**: Python 3, pip, git
2. **Create application user**: `rantoo` user with restricted shell
3. **Set up directories**: `/opt/rantoo` for the application
4. **Deploy code**: Clone and set up the Flask application
5. **Install dependencies**: Create virtual environment and install requirements
6. **Configure systemd**: Create and enable the `rantoo` service
7. **Start service**: Enable and start the application

## Service Management

The application runs as a systemd service:

```bash
# Check status
sudo systemctl status rantoo

# View logs
sudo journalctl -u rantoo -f

# Restart service
sudo systemctl restart rantoo

# Stop service
sudo systemctl stop rantoo

# Start service
sudo systemctl start rantoo
```

## Security Features

- Application runs as non-root user (`rantoo`)
- User has restricted shell (`/bin/false`)
- No direct access to application files

## Troubleshooting

### Check Application Status
```bash
./manage.sh status
```

### View Application Logs
```bash
./manage.sh logs
```

### Test Application Health
```bash
curl http://your-host-ip:33080/health
```

### Manual Service Restart
```bash
sudo systemctl restart rantoo
```
