variable "region" {
  type    = string
  default = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type used for vertical scaling"
  type        = string
  default     = "t2.small"
}

variable "key_name" {
  type = string
}