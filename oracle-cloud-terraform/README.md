# 🌩️ Oracle Cloud Terraform Deployment

Deploy PsySupport AI Bot to Oracle Cloud Infrastructure using Terraform.

## Prerequisites

1. Oracle Cloud Free Tier account: https://www.oracle.com/cloud/free/
2. Terraform installed: https://developer.hashicorp.com/terraform/downloads
3. OCI CLI configured: https://docs.oracle.com/en-us/iaas/Content/API/Concepts/cliconcepts.htm

## Setup

### 1. Generate API Key

```bash
mkdir -p ~/.oci
openssl genrsa -out ~/.oci/oci_api_key.pem 2048
chmod 600 ~/.oci/oci_api_key.pem
openssl rsa -pubout -in ~/.oci/oci_api_key.pem -out ~/.oci/oci_api_key_public.pem
```

### 2. Add Public Key to Oracle Cloud

1. Log in to https://cloud.oracle.com
2. Profile (top right) → User Settings → API Keys
3. Add API Key → Paste public key
4. Copy the fingerprint shown

### 3. Get Required OCIDs

```bash
# Tenancy OCID
oci iam tenancy get --tenancy-id $(oci iam config get | jq -r '.data.tenancy-id')

# User OCID
oci iam user list --name <your-email>

# Compartment OCID
oci iam compartment list
```

### 4. Configure Terraform

```bash
cd oracle-cloud-terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
nano terraform.tfvars
```

### 5. Deploy

```bash
terraform init
terraform plan
terraform apply
```

### 6. Access Your Bot

```bash
# Get IP
terraform output instance_public_ip

# SSH into the server
ssh ubuntu@<IP>

# Check logs
docker compose -f docker-compose.oracle.yml logs -f bot
```

## Architecture

```
Oracle Cloud (Free Tier)
├── VM.Standard.A1.Flex (ARM, 1 OCPU, 6GB RAM)
│   ├── Docker
│   │   ├── Bot Container
│   │   ├── PostgreSQL Container
│   │   └── Redis Container
│   └── Auto-update (daily at 4 AM)
├── VCN (Virtual Cloud Network)
│   ├── Subnet (10.0.1.0/24)
│   ├── Internet Gateway
│   └── Security List (ports 22, 80, 443, 3000, 9090)
└── Public IP
```

## Costs

**Free Forever:**
- 1 VM.Standard.A1.Flex instance
- 100 GB block storage
- 10 TB outbound data transfer

## Maintenance

```bash
# Update bot
/home/ubuntu/update-bot.sh

# View logs
docker compose -f docker-compose.oracle.yml logs -f

# Restart
docker compose -f docker-compose.oracle.yml restart

# Backup database
docker compose -f docker-compose.oracle.yml exec postgres pg_dump -U postgres psybot > backup.sql
```

## Destroy

```bash
terraform destroy
```

**Warning:** This will delete all data!
