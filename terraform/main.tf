resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.project_name}"
  location = var.location
}

# VNet and Subnets
resource "azurerm_virtual_network" "vnet" {
  name                = "vnet-${var.project_name}"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_subnet" "aks_subnet" {
  name                 = "snet-aks"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_subnet" "psql_subnet" {
  name                 = "snet-psql"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.2.0/24"]
  delegation {
    name = "fs"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

# Private DNS Zone for PostgreSQL
resource "azurerm_private_dns_zone" "psql_dns" {
  name                = "${var.project_name}.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "psql_vnet_link" {
  name                  = "psql-vnet-link"
  private_dns_zone_name = azurerm_private_dns_zone.psql_dns.name
  virtual_network_id    = azurerm_virtual_network.vnet.id
  resource_group_name   = azurerm_resource_group.rg.name
}

# PostgreSQL Flexible Server
resource "azurerm_postgresql_flexible_server" "psql" {
  name                   = "psql-${var.project_name}-db"
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location
  version                = "15"
  delegated_subnet_id    = azurerm_subnet.psql_subnet.id
  private_dns_zone_id    = azurerm_private_dns_zone.psql_dns.id
  administrator_login    = var.db_admin_user
  administrator_password = var.db_admin_password
  zone                   = "1"
  storage_mb             = 32768
  sku_name               = "B_Standard_B1ms"
  
  depends_on = [azurerm_private_dns_zone_virtual_network_link.psql_vnet_link]
}

# ACR
resource "azurerm_container_registry" "acr" {
  name                = "acr${var.project_name}registry"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Standard"
  admin_enabled       = false
}

# AKS
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "aks-${var.project_name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "aks-${var.project_name}"

  default_node_pool {
    name           = "default"
    node_count     = 2
    vm_size        = "Standard_DS2_v2"
    vnet_subnet_id = azurerm_subnet.aks_subnet.id
  }

  identity {
    type = "SystemAssigned"
  }
}

# Role Assignment to allow AKS to pull from ACR
resource "azurerm_role_assignment" "aks_acr_pull" {
  principal_id                     = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.acr.id
  skip_service_principal_aad_check = true
}
