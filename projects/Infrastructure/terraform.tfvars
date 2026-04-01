region = "us-east-1"
vpc_name = "EKS-Demo-VPC"
vpc_cidr = "10.1.0.0/16"

 subnets = [
  {
    name = "subnet-1"
    cidr_block = "10.1.1.0/24"
    availability_zone = "us-east-1a"
  },

  {
    name = "subnet-2",
    cidr_block = "10.1.2.0/24",
    availability_zone = "us-east-1b"
  },
  {
    name = "subnet-3",
    cidr_block = "10.1.3.0/24",
    availability_zone = "us-east-1c"
  }
 ]

cluster_name = "eks-cluster"
node_group_name = "eks-node-group"

instance_types = ["m7i-flex.large"]
capacity_type  = "ON_DEMAND"

desired_size = 1
min_size     = 1
max_size     = 2

disk_size = 30

repositories = [
  "frontend",
  "gateway",
  "auth",
  "order-service",
  "orders",
  "product-service",
  "user-service"
]