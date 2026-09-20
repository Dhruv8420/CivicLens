# CivicLens AWS deployment

This directory contains deployment configuration for CivicLens.

## AWS architecture

- Amazon EC2 (Amazon Linux 2023) hosts the React build and FastAPI backend.
- Nginx serves `frontend/dist` and reverse-proxies `/api/` to FastAPI on `127.0.0.1:8000`.
- AWS Systems Manager Session Manager provides administrative access without requiring inbound SSH.
- IAM instance profile uses `AmazonSSMManagedInstanceCore`.
- An EC2 security group exposes HTTP/80 and HTTPS/443 publicly.
- The CloudFormation template can create the EC2, security group, IAM role, and instance profile in an existing VPC/subnet.

## CloudFormation

`civiclens-ec2-existing-vpc.yaml` expects an existing VPC, public subnet, and EC2 key pair.

The template deliberately does not contain AWS access keys, GitHub tokens, private keys, or other secrets.

## Server layout

The deployment files assume:

- Application: `/opt/CivicLens`
- Backend: `/opt/CivicLens/backend`
- Python virtual environment: `/opt/CivicLens/.venv`
- Frontend build: `/opt/CivicLens/frontend/dist`

## Install Nginx

On Amazon Linux 2023:

```bash
sudo dnf install -y nginx
sudo cp deployment/nginx/civiclens.conf /etc/nginx/conf.d/civiclens.conf
sudo nginx -t
sudo systemctl enable --now nginx
```

## Install the FastAPI service

```bash
sudo cp deployment/systemd/civiclens.service /etc/systemd/system/civiclens.service
sudo systemctl daemon-reload
sudo systemctl enable --now civiclens
sudo systemctl status civiclens
```

## Security

Do not commit:

- `.env` files containing secrets
- AWS access keys
- GitHub personal access tokens
- EC2 `.pem` private keys
- passwords or API keys

Use environment variables or AWS-managed identity/permissions for secrets.
