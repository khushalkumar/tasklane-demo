resource "aws_db_instance" "primary" {
  identifier              = "tasklane-primary"
  engine                  = "postgres"
  engine_version          = "16.4"
  instance_class          = "db.t4g.micro"
  allocated_storage       = 20
  backup_retention_period = 30
  storage_encrypted       = true
}
