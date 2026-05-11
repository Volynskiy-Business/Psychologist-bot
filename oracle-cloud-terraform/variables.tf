variable "tenancy_ocid" {
  description = "OCID of your Oracle Cloud tenancy"
  type        = string
}

variable "user_ocid" {
  description = "OCID of your Oracle Cloud user"
  type        = string
}

variable "fingerprint" {
  description = "Fingerprint of your API key"
  type        = string
}

variable "private_key_path" {
  description = "Path to your private API key"
  type        = string
  default     = "~/.oci/oci_api_key.pem"
}

variable "region" {
  description = "Oracle Cloud region"
  type        = string
  default     = "eu-frankfurt-1"
}

variable "compartment_ocid" {
  description = "OCID of the compartment"
  type        = string
}

variable "ssh_public_key_path" {
  description = "Path to your SSH public key"
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

variable "bot_token" {
  description = "Telegram Bot Token"
  type        = string
  sensitive   = true
}

variable "openrouter_api_key" {
  description = "OpenRouter API Key"
  type        = string
  sensitive   = true
}
