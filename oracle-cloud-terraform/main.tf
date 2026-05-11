# Oracle Cloud Infrastructure - Terraform Configuration
# Deploys PsySupport AI Bot on Oracle Cloud Free Tier

terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 5.0"
    }
  }
}

provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region
}

# Virtual Cloud Network
resource "oci_core_vcn" "psy_support_vcn" {
  cidr_block     = "10.0.0.0/16"
  compartment_id = var.compartment_ocid
  display_name   = "psy-support-vcn"
  dns_label      = "psysupport"
}

# Internet Gateway
resource "oci_core_internet_gateway" "psy_support_igw" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.psy_support_vcn.id
  display_name   = "psy-support-igw"
}

# Route Table
resource "oci_core_route_table" "psy_support_rt" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.psy_support_vcn.id
  display_name   = "psy-support-rt"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.psy_support_igw.id
  }
}

# Security List
resource "oci_core_security_list" "psy_support_sl" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.psy_support_vcn.id
  display_name   = "psy-support-sl"

  # SSH
  ingress_security_rules {
    protocol  = "6" # TCP
    source    = "0.0.0.0/0"
    stateless = false

    tcp_options {
      min = 22
      max = 22
    }
  }

  # HTTP
  ingress_security_rules {
    protocol  = "6"
    source    = "0.0.0.0/0"
    stateless = false

    tcp_options {
      min = 80
      max = 80
    }
  }

  # HTTPS
  ingress_security_rules {
    protocol  = "6"
    source    = "0.0.0.0/0"
    stateless = false

    tcp_options {
      min = 443
      max = 443
    }
  }

  # Grafana
  ingress_security_rules {
    protocol  = "6"
    source    = "0.0.0.0/0"
    stateless = false

    tcp_options {
      min = 3000
      max = 3000
    }
  }

  # Prometheus
  ingress_security_rules {
    protocol  = "6"
    source    = "0.0.0.0/0"
    stateless = false

    tcp_options {
      min = 9090
      max = 9090
    }
  }

  # All outbound
  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
    stateless   = false
  }
}

# Subnet
resource "oci_core_subnet" "psy_support_subnet" {
  cidr_block        = "10.0.1.0/24"
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_vcn.psy_support_vcn.id
  display_name      = "psy-support-subnet"
  dns_label         = "subnet"
  route_table_id    = oci_core_route_table.psy_support_rt.id
  security_list_ids = [oci_core_security_list.psy_support_sl.id]
}

# Compute Instance (ARM - Free Tier)
resource "oci_core_instance" "psy_support_bot" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = var.compartment_ocid
  display_name        = "psy-support-bot"
  shape               = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = 1
    memory_in_gbs = 6
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ubuntu.images[0].id
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.psy_support_subnet.id
    assign_public_ip = true
  }

  metadata = {
    ssh_authorized_keys = file(var.ssh_public_key_path)
    user_data           = base64encode(templatefile("${path.module}/cloud-init.yaml", {
      bot_token           = var.bot_token
      openrouter_api_key  = var.openrouter_api_key
    }))
  }

  timeouts {
    create = "60m"
  }
}

# Data sources
data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_ocid
}

data "oci_core_images" "ubuntu" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# Outputs
output "instance_public_ip" {
  value = oci_core_instance.psy_support_bot.public_ip
}

output "instance_id" {
  value = oci_core_instance.psy_support_bot.id
}
