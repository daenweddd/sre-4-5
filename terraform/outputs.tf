output "public_ip" {
  value = aws_instance.tech_store_vm.public_ip
}

output "instance_id" {
  value = aws_instance.tech_store_vm.id
}