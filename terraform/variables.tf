variable "location" {
  default = "westeurope"
}
variable "project_name" {
  default = "agrostream"
}
variable "db_admin_user" {
  default = "psqladmin"
}
variable "db_admin_password" {
  type        = string
  description = "The administrator password of the PostgreSQL server"
  sensitive   = true
}
