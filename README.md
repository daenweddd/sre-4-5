# Online Tech Store Microservices System

## Overview

This project implements a containerized microservices-based system for an online tech store. It demonstrates deployment, monitoring, infrastructure provisioning, and incident response.

## Architecture

The system includes:

* Frontend (Nginx)
* Microservices: Auth, Product, Order, User, Chat
* PostgreSQL database
* Prometheus and Grafana for monitoring
* AWS EC2 provisioned with Terraform

All services run in separate Docker containers and communicate via internal networking.

## Deployment

Run the system using Docker Compose:

```bash
docker compose up --build
```

## Monitoring

* Prometheus collects metrics from services
* Grafana visualizes system performance
* Service health is monitored using metrics and dashboards

## Terraform

Infrastructure is provisioned using:

```bash
terraform init
terraform plan
terraform apply
```

An EC2 instance is created with open ports for HTTP, SSH, Grafana, and Prometheus.

## Incident Simulation

A failure was introduced in the Order Service by misconfiguring the database. The issue was detected via monitoring tools, analyzed using logs, fixed, and the service was restored.

## Technologies used

Python (FastAPI), Docker, PostgreSQL, Prometheus, Grafana, Terraform, AWS

## Deployment Guide

The system can be deployed locally using Docker Compose or in the cloud using Terraform.

### Local Deployment
Run:
docker compose up --build

### Cloud Deployment (AWS)
1. Navigate to terraform folder:
cd terraform

2. Initialize Terraform:
terraform init

3. Review the plan:
terraform plan

4. Apply configuration:
terraform apply

After deployment, use the public IP to access the system.
