terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-agrostream-prod"
  location = "West Europe"
}

# Add AKS Cluster, PostgreSQL Flexible Server, and Networking below
# ...
